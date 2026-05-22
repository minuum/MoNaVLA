import base64
import gc
import io
import os
import sys
import threading
import time
import warnings
from pathlib import Path
import socket

import cv2
import gradio as gr
import matplotlib
import numpy as np
import requests
from PIL import Image

matplotlib.use("Agg")
import matplotlib.pyplot as plt

warnings.filterwarnings("ignore", message="Unable to import Axes3D")


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ENV_PATH = PROJECT_ROOT / ".vla_env_settings"
# Exp47: path_type 키를 직접 입력하거나 자연어 instruction 사용 가능.
# path_type 키 목록: center_straight, center_left, center_right,
#   left_straight, left_left, left_right,
#   right_straight, right_right, right_left
# 미매칭 시 bbox cx 위치에서 자동 추론 (right_right / left_left / center_straight).
DEFAULT_INSTRUCTION = "the gray basket on right"
PATH_TYPES = [
    "right_right", "right_left", "right_straight",
    "center_straight", "center_left", "center_right",
    "left_straight", "left_left", "left_right",
]
GOAL_NAV_PRESETS = [
    "the gray basket on right",
    "the gray basket on left",
    "the gray basket",
    "the door",
    "the corridor on the left",
    "the corridor on the right",
]

# 실험 모드: (표시 이름, instruction, backend_instruction_mode, speed_scaling, grounding_skip_n)
EXP_MODES = {
    "GoalNav-fixed (Exp49, 고정속도)": {
        "instruction": GOAL_NAV_PRESETS[0],
        "backend_mode": "GoalNav (exp49)",
        "model": "exp49",
        "speed_scaling": False,
        "grounding_skip_n": 3,
        "desc": "기본 GoalNav — 96.4% val acc",
    },
    "GoalNav-scaled (Exp49, 거리비례속도)": {
        "instruction": GOAL_NAV_PRESETS[0],
        "backend_mode": "GoalNav (exp49)",
        "model": "exp49",
        "speed_scaling": True,
        "grounding_skip_n": 3,
        "desc": "기본 GoalNav + 거리비례속도 — 96.4% val acc",
    },
    "GoalNav (Exp50, flip-aug)": {
        "instruction": GOAL_NAV_PRESETS[0],
        "backend_mode": "GoalNav (exp50)",
        "model": "exp50",
        "speed_scaling": False,
        "grounding_skip_n": 3,
        "desc": "flip augmentation 2x — 92.0% val acc",
    },
    "GoalNav (Exp51, crop-aug)": {
        "instruction": GOAL_NAV_PRESETS[0],
        "backend_mode": "GoalNav (exp51)",
        "model": "exp51",
        "speed_scaling": False,
        "grounding_skip_n": 3,
        "desc": "crop augmentation 4x — 93.4% val acc",
    },
    "GoalNav (Exp52, lang+vis) ⚠️": {
        "instruction": GOAL_NAV_PRESETS[0],
        "backend_mode": "GoalNav (exp52)",
        "model": "exp52",
        "speed_scaling": False,
        "grounding_skip_n": 3,
        "desc": "⚠️ lang+vis 2048-dim — 실시간 추출 미지원, 실험적",
    },
    "GoalNav (Exp53, CLIP-LoRA)": {
        "instruction": GOAL_NAV_PRESETS[0],
        "backend_mode": "GoalNav (exp53)",
        "model": "exp53",
        "speed_scaling": False,
        "grounding_skip_n": 3,
        "desc": "CLIP LoRA fine-tuned vision encoder — 94.7% val acc",
    },
    "PathType-fixed (Exp47, 고정속도)": {
        "instruction": "right_right",
        "backend_mode": "PathType (exp47)",
        "model": None,
        "speed_scaling": False,
        "grounding_skip_n": 1,
        "desc": "PathType 분류기 — 고정속도",
    },
}
EXP_MODE_NAMES = list(EXP_MODES.keys())
LINEAR_SPEED_VLA = 1.15
ANGULAR_SPEED_VLA = 1.15

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")
os.environ.setdefault("ROS_HOME", "/tmp/ros")
Path(os.environ["MPLCONFIGDIR"]).mkdir(parents=True, exist_ok=True)
Path(os.environ["ROS_HOME"]).mkdir(parents=True, exist_ok=True)

os.environ["ROS_DOMAIN_ID"] = "42"
os.environ["RMW_IMPLEMENTATION"] = "rmw_fastrtps_cpp"
print(f"🔧 Forced ROS_DOMAIN_ID={os.environ['ROS_DOMAIN_ID']}, RMW={os.environ['RMW_IMPLEMENTATION']}")


def load_env() -> None:
    env_path = Path(os.getenv("VLA_ENV_PATH", str(DEFAULT_ENV_PATH)))
    if not env_path.exists():
        fallback = Path("/home/billy/25-1kp/vla/.vla_env_settings")
        if fallback.exists():
            env_path = fallback
    if not env_path.exists():
        return

    with env_path.open("r") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line.startswith("export "):
                continue
            try:
                key, val = line.replace("export ", "", 1).split("=", 1)
            except ValueError:
                continue
            os.environ[key] = val.strip('"').strip("'")
    print(f"✅ Loaded environment from {env_path}")


load_env()

DEFAULT_API_URL = os.getenv("VLA_API_SERVER", "http://localhost:8000")
API_KEY = os.getenv("VLA_API_KEY", "vla_devel_key_2026")
DEFAULT_BACKEND_MODE = os.getenv(
    "VLA_DASHBOARD_BACKEND",
    "API Server" if os.getenv("VLA_SERVER_ROLE") == "jetson" else "Local Runtime",
)

sys.path.append(str(PROJECT_ROOT / "scripts"))
try:
    from inference_logger import get_logger

    logger_instance = get_logger()
except ImportError:
    logger_instance = None

sys.path.insert(0, str(PROJECT_ROOT))
from robovlm_nav.serve.inference_server import MobileVLAInference
from robovlm_nav.serve.vla_control_utils import VLAControlManager


def prepend_env_path(key: str, value: str) -> None:
    current = os.environ.get(key, "")
    parts = [p for p in current.split(os.pathsep) if p]
    if value not in parts:
        os.environ[key] = value if not parts else f"{value}{os.pathsep}{current}"


def setup_ros_paths() -> None:
    ros_ws = Path(os.getenv("VLA_ROS_WS", str(PROJECT_ROOT / "ROS_action")))
    install_base = ros_ws / "install"
    if not install_base.exists():
        return

    prepend_env_path("AMENT_PREFIX_PATH", str(install_base))
    prepend_env_path("COLCON_PREFIX_PATH", str(install_base))
    prepend_env_path("CMAKE_PREFIX_PATH", str(install_base))

    for pkg in install_base.iterdir():
        if not pkg.is_dir():
            continue
        lib_path = pkg / "lib"
        if lib_path.exists():
            prepend_env_path("LD_LIBRARY_PATH", str(lib_path))
        share_path = pkg / "share"
        if share_path.exists():
            prepend_env_path("AMENT_PREFIX_PATH", str(pkg))
        local_path = pkg / "local/lib/python3.10/dist-packages"
        site_path = pkg / "lib/python3.10/site-packages"
        for candidate in (local_path, site_path):
            if candidate.exists() and str(candidate) not in sys.path:
                sys.path.append(str(candidate))
                prepend_env_path("PYTHONPATH", str(candidate))


setup_ros_paths()

ROS_AVAILABLE = False
try:
    import rclpy
    from rclpy.callback_groups import ReentrantCallbackGroup
    from rclpy.node import Node
    from cv_bridge import CvBridge
    from geometry_msgs.msg import Twist
    from camera_interfaces.srv import GetImage

    ROS_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ ROS2 environment partially missing: {e}")

    class Node:  # stub so class definitions below don't NameError
        pass

    class ReentrantCallbackGroup:
        pass


CC_PARAMS = {
    "r_gain": 1.0,
    "g_gain": 1.0,
    "b_gain": 1.0,
}


def correct_image(img_pil: Image.Image) -> Image.Image:
    img_rgb = np.array(img_pil).astype(np.float32)
    r, g, b = cv2.split(img_rgb)
    r = r * CC_PARAMS["r_gain"]
    g = g * CC_PARAMS["g_gain"]
    b = b * CC_PARAMS["b_gain"]
    img_corrected = cv2.merge([r, g, b])
    return Image.fromarray(np.clip(img_corrected, 0, 255).astype(np.uint8))


def scan_local_files():
    ckpt_tuples = []
    for root_dir in (PROJECT_ROOT, PROJECT_ROOT / "runs"):
        if not root_dir.exists():
            continue
        pattern = "**/*" if root_dir.name == "runs" else "*"
        for path in root_dir.glob(pattern):
            if path.suffix not in {".ckpt", ".pth", ".pt"} or not path.is_file():
                continue
            try:
                rel = path.relative_to(PROJECT_ROOT)
                display_name = str(rel)
            except ValueError:
                display_name = path.name
            ckpt_tuples.append((display_name, str(path)))

    configs_dir = PROJECT_ROOT / "configs"
    conf_tuples = []
    if configs_dir.exists():
        for path in configs_dir.glob("*.json"):
            conf_tuples.append((path.name, str(path)))

    return sorted(set(ckpt_tuples)), sorted(conf_tuples)


def pick_default_choice(choices, env_key: str):
    preferred = os.getenv(env_key)
    if preferred:
        for _label, value in choices:
            if value == preferred:
                return value
    return choices[0][1] if choices else None


def to_precision(precision_label: str) -> str:
    return "int8" if precision_label == "INT8 (Fast)" else "fp16"


def short_model_name(path_str: str) -> str:
    if not path_str or path_str == "N/A":
        return "N/A"
    path = Path(path_str)
    if len(path.parts) >= 2:
        return f"{path.parent.name}/{path.name}"
    return path.name


def pick_server_port(default_port: int, span: int = 20) -> int:
    try:
        for port in range(default_port, default_port + span):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                try:
                    sock.bind(("127.0.0.1", port))
                except OSError:
                    continue
            return port
    except PermissionError:
        return default_port
    return default_port


class LocalSharedRuntime:
    def __init__(self):
        self.model = None
        self.info_cache = {
            "model_loaded": False,
            "model_name": "Unavailable",
            "checkpoint_path": "N/A",
            "config_path": "N/A",
            "precision": "N/A",
            "device": "N/A",
            "action_dim": 3,
        }

    def unload(self) -> None:
        if self.model is not None:
            del self.model
            self.model = None
            gc.collect()
        self.info_cache = {
            "model_loaded": False,
            "model_name": "Unavailable",
            "checkpoint_path": "N/A",
            "config_path": "N/A",
            "precision": "N/A",
            "device": "N/A",
            "action_dim": 3,
        }

    def load_model(self, checkpoint_path: str, config_path: str, precision: str, refresh: bool = False):
        if refresh:
            self.unload()

        use_quant = precision == "int8"
        device = "cuda" if os.environ.get("CUDA_VISIBLE_DEVICES", "") != "" else "cpu"
        try:
            import torch

            if torch.cuda.is_available():
                device = "cuda"
            else:
                device = "cpu"
        except Exception:
            device = "cpu"

        self.model = MobileVLAInference(
            checkpoint_path=checkpoint_path,
            config_path=config_path,
            device=device,
            use_quant=use_quant,
        )
        self.info_cache = {
            "model_loaded": True,
            "model_name": Path(config_path).stem,
            "checkpoint_path": checkpoint_path,
            "config_path": config_path,
            "precision": precision,
            "device": device,
            "action_dim": 3,
        }
        return self.model

    def reset(self, instruction: str = "N/A") -> None:
        if self.model is None:
            raise RuntimeError("Model not loaded")
        self.model.reset(instruction=instruction)

    def predict(self, image_base64: str, instruction: str) -> dict:
        if self.model is None:
            raise RuntimeError("Model not loaded")
        action, latency_ms, chunk = self.model.predict(
            image_base64=image_base64,
            instruction=instruction,
        )
        return {
            "action": action.tolist(),
            "latency_ms": float(latency_ms),
            "chunk": chunk.tolist(),
        }

    def get_model_info(self) -> dict:
        return dict(self.info_cache)


shared_runtime = LocalSharedRuntime()


class LocalInferenceBackend:
    name = "Local Runtime"

    def load_model(self, checkpoint_path: str, config_path: str, precision: str) -> dict:
        model = shared_runtime.load_model(
            checkpoint_path=checkpoint_path,
            config_path=config_path,
            precision=precision,
            refresh=True,
        )
        info = shared_runtime.get_model_info()
        return {
            "status": "success",
            "message": f"✅ Loaded: {short_model_name(model.checkpoint_path)} ({info['precision']})",
            "info": info,
        }

    def reset(self, instruction: str) -> str:
        shared_runtime.reset(instruction=instruction)
        return "✅ Local history cleared"

    def predict(self, image: Image.Image, instruction: str) -> dict:
        buffered = io.BytesIO()
        image.save(buffered, format="JPEG")
        img_b64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
        return shared_runtime.predict(image_base64=img_b64, instruction=instruction)

    def info(self) -> dict:
        return shared_runtime.get_model_info()


class ApiInferenceBackend:
    name = "API Server"

    def __init__(self, api_url: str):
        self.api_url = api_url.rstrip("/")

    def _headers(self) -> dict:
        return {"X-API-Key": API_KEY}

    def _post(self, path: str, payload: dict) -> dict:
        response = requests.post(
            f"{self.api_url}{path}",
            json=payload,
            headers=self._headers(),
            timeout=60,
        )
        response.raise_for_status()
        return response.json()

    def load_model(self, checkpoint_path: str, config_path: str, precision: str) -> dict:
        payload = {
            "checkpoint_path": checkpoint_path,
            "config_path": config_path,
            "precision": precision,
            "refresh": True,
        }
        result = self._post("/model/load", payload)
        info = self.info()
        return {
            "status": result.get("status", "success"),
            "message": f"✅ API loaded: {short_model_name(info['checkpoint_path'])} ({info['precision']})",
            "info": info,
        }

    def reset(self, instruction: str) -> str:
        self._post("/reset", {})
        return f"✅ API history cleared ({instruction})"

    def predict(self, image: Image.Image, instruction: str) -> dict:
        buffered = io.BytesIO()
        image.save(buffered, format="JPEG")
        img_b64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
        return self._post(
            "/predict",
            {
                "image": img_b64,
                "instruction": instruction,
                "strategy": "receding_horizon",
            },
        )

    def set_config(self, speed_scaling: bool, grounding_skip_n: int, model: str | None = None) -> dict:
        try:
            payload: dict = {"speed_scaling": speed_scaling, "grounding_skip_n": grounding_skip_n}
            if model is not None:
                payload["model"] = model
            return self._post("/config", payload)
        except Exception as e:
            return {"status": "error", "reason": str(e)}

    def info(self) -> dict:
        response = requests.get(
            f"{self.api_url}/model/info",
            headers=self._headers(),
            timeout=10,
        )
        response.raise_for_status()
        return response.json()


def make_backend(mode: str, api_url: str):
    if mode == "API Server":
        return ApiInferenceBackend(api_url)
    return LocalInferenceBackend()


class ROSDashboardNode(Node):
    def __init__(self):
        super().__init__("gradio_dashboard_node")
        self.callback_group = ReentrantCallbackGroup()
        self.cv_bridge = CvBridge()
        self.get_image_client = self.create_client(
            GetImage, "get_image_service", callback_group=self.callback_group
        )
        self.cmd_pub = self.create_publisher(Twist, "/cmd_vel", 10, callback_group=self.callback_group)
        self.control = VLAControlManager(self, default_throttle=50, move_duration=0.4)

    def get_inference_frame(self):
        if not self.get_image_client.wait_for_service(timeout_sec=1.0):
            return None
        request = GetImage.Request()
        future = self.get_image_client.call_async(request)
        start_time = time.time()
        while rclpy.ok() and not future.done():
            if time.time() - start_time > 2.0:
                return None
            time.sleep(0.01)
        if future.done():
            try:
                response = future.result()
                if response and response.image.data:
                    cv_image = self.cv_bridge.imgmsg_to_cv2(response.image, "bgr8")
                    return Image.fromarray(cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB))
            except Exception:
                return None
        return None

    def generate_trajectory_plot(self, full_chunk):
        if full_chunk is None or len(full_chunk) == 0:
            return None

        dt = 0.2
        traj_x, traj_y = [0.0], [0.0]
        curr_x, curr_y = 0.0, 0.0
        for step in full_chunk:
            curr_x += float(step[0]) * dt
            curr_y += float(step[1]) * dt
            traj_x.append(curr_x)
            traj_y.append(curr_y)

        fig, ax = plt.subplots(figsize=(5, 5))
        ax.plot(0, 0, "ko", markersize=8, label="Start")
        ax.arrow(0, 0, 0.2, 0, head_width=0.05, head_length=0.05, fc="k", ec="k")
        ax.plot(traj_x, traj_y, "b-", linewidth=3, alpha=0.8)
        ax.plot(traj_x[-1], traj_y[-1], "b*", markersize=10)
        ax.set_title("Predicted Trajectory (2D XY)")
        ax.set_xlabel("Forward (X) [m]")
        ax.set_ylabel("Left/Right (Y) [m]")
        ax.grid(True, linestyle="--", alpha=0.6)
        ax.set_aspect("equal")
        all_points = np.column_stack((traj_x, traj_y))
        mins = np.min(all_points, axis=0) - 0.5
        maxs = np.max(all_points, axis=0) + 0.5
        ax.set_xlim(min(mins[0], -0.5), max(maxs[0], 2.0))
        ax.set_ylim(min(mins[1], -1.0), max(maxs[1], 1.0))
        return fig


ros_node = None
if ROS_AVAILABLE:
    try:
        if not rclpy.ok():
            rclpy.init()
        ros_node = ROSDashboardNode()
        threading.Thread(target=lambda: rclpy.spin(ros_node), daemon=True).start()
    except Exception as e:
        ROS_AVAILABLE = False
        ros_node = None
        print(f"⚠️ ROS dashboard node disabled: {e}")


def annotate_image(img: Image.Image, bbox: dict | None = None, draw_grid: bool = True) -> Image.Image:
    """카메라 이미지에 3x3 격자 + bbox 오버레이를 그려 반환."""
    arr = np.array(img)
    h, w = arr.shape[:2]

    if draw_grid:
        color = (100, 255, 100)
        cv2.line(arr, (w // 3, 0), (w // 3, h), color, 1)
        cv2.line(arr, (2 * w // 3, 0), (2 * w // 3, h), color, 1)
        cv2.line(arr, (0, h // 3), (w, h // 3), color, 1)
        cv2.line(arr, (0, 2 * h // 3), (w, 2 * h // 3), color, 1)

    if bbox:
        cx_px = int(bbox["cx"] * w)
        cy_px = int(bbox["cy"] * h)
        label = str(bbox.get("entity", "bbox"))

        if "x1" in bbox:
            x1 = int(bbox["x1"] * w)
            y1 = int(bbox["y1"] * h)
            x2 = int(bbox["x2"] * w)
            y2 = int(bbox["y2"] * h)
            cv2.rectangle(arr, (x1, y1), (x2, y2), (255, 80, 80), 2)
        else:
            # cx/cy만 있으면 십자선
            r = 10
            cv2.line(arr, (cx_px - r, cy_px), (cx_px + r, cy_px), (255, 80, 80), 2)
            cv2.line(arr, (cx_px, cy_px - r), (cx_px, cy_px + r), (255, 80, 80), 2)

        cv2.circle(arr, (cx_px, cy_px), 4, (255, 80, 80), -1)
        cv2.putText(arr, label[:20], (max(cx_px - 40, 0), max(cy_px - 8, 12)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 80, 80), 1, cv2.LINE_AA)

    return Image.fromarray(arr)


state = {
    "auto_inference": False,
    "is_running": False,
    "is_busy": False,
    "step_count": 0,
    "last_img": None,
    "current_log": "Ready",
    "camera_status": "Unknown",
    "model_status": "Not Loaded",
    "model_path": "N/A",
}


def backend_model_info(mode: str, api_url: str) -> dict:
    try:
        return make_backend(mode, api_url).info()
    except Exception:
        return {
            "model_loaded": False,
            "model_name": "Unavailable",
            "checkpoint_path": "N/A",
            "config_path": "N/A",
            "precision": "N/A",
            "device": "N/A",
            "action_dim": 3,
        }


def load_model_wrapper(backend_mode: str, api_url: str, precision_label: str, ckpt_path: str, config_path: str):
    try:
        result = make_backend(backend_mode, api_url).load_model(
            checkpoint_path=ckpt_path,
            config_path=config_path,
            precision=to_precision(precision_label),
        )
        info = result["info"]
        state["model_status"] = result["message"]
        state["model_path"] = info["checkpoint_path"]
        return result["message"], info["checkpoint_path"]
    except Exception as e:
        state["model_status"] = "Load Failed"
        return f"❌ Load Failed: {e}", state["model_path"]


def set_running(running: bool, backend_mode: str, api_url: str, instruction: str):
    state["is_running"] = running
    state["step_count"] = 0 if running else state["step_count"]
    if running:
        try:
            make_backend(backend_mode, api_url).reset(instruction)
        except Exception:
            pass
    return "Running..." if running else "Stopped"


def run_backend_inference(image: Image.Image, instruction: str, backend_mode: str, api_url: str):
    backend = make_backend(backend_mode, api_url)
    result = backend.predict(image=image, instruction=instruction)
    # action_3d includes az for ROT_L/ROT_R; fall back to 2D action if not present
    action_raw = result.get("action_3d") or result["action"]
    action = np.asarray(action_raw, dtype=np.float32).reshape(-1)
    chunk = np.asarray(result.get("chunk", [action.tolist()]), dtype=np.float32)
    if chunk.ndim == 1:
        chunk = chunk.reshape(1, -1)

    if ROS_AVAILABLE and ros_node:
        state["current_log"] = ros_node.control.move_and_stop_ramped(
            float(action[0]),
            float(action[1]),
            float(action[2]) if action.size > 2 else 0.0,
            source="gradio_inference",
        )

    strategy = result.get("strategy", "")
    pred_label = result.get("predicted_label") or ""
    goal_near = result.get("goal_near_proxy")

    label_prefix = f"[{pred_label}] " if pred_label else ""
    act_str = f"{label_prefix}{action[0]:.4f}, {action[1]:.4f}, {action[2] if action.size > 2 else 0.0:.4f}"

    speed_scale = result.get("speed_scale")
    grounding_cached = result.get("grounding_cached")

    if strategy == "goal_nav":
        near_str = ("✅ NEAR" if goal_near else "⬜ far") if goal_near is not None else "?"
        goal = result.get("goal")
        goal_str = f"[{goal[0]:.2f},{goal[1]:.2f},{goal[2]:.2f}]" if goal else "init"
        caption = result.get("grounding_caption") or ""
        chunk_display = f"[GoalNav] goal={goal_str}  near={near_str}"
        if speed_scale is not None:
            chunk_display += f"  spd={speed_scale:.2f}"
        if grounding_cached is not None:
            chunk_display += f"  cache={'✓' if grounding_cached else '✗'}"
        if caption:
            chunk_display += f"\ngrounding: {caption}"
    else:
        chunk_display = f"Chunk (N={len(chunk)}):\n{np.array2string(chunk, precision=2, separator=', ', suppress_small=True)}"

    return {
        "log_str": f"✅ {backend.name}: {state['current_log']}",
        "lat_str": f"{float(result['latency_ms']):.1f} ms",
        "act_str": act_str,
        "chunk_display": chunk_display,
        "action": action,
        "chunk": chunk,
        "goal_near": goal_near,
        # logger용 raw 필드
        "latency_ms": result.get("latency_ms"),
        "predicted_label": result.get("predicted_label"),
        "grounding_caption": result.get("grounding_caption"),
        "strategy": result.get("strategy"),
        "bbox": result.get("bbox"),
        "instruction_used": result.get("instruction_used"),
        "matched_path_type": result.get("matched_path_type"),
        "speed_scale": speed_scale,
        "grounding_cached": grounding_cached,
    }


def update_ui(mode, backend_mode, api_url, instr, apply_cc, _run_status):
    if state["is_busy"]:
        return (
            gr.update(),
            gr.update(),
            gr.update(),
            gr.update(),
            gr.update(),
            gr.update(),
            gr.update(),
            gr.update(),
            gr.update(),
        )

    state["auto_inference"] = mode in ("Inference (Auto)", "Inference (18-step)")

    if not ROS_AVAILABLE or ros_node is None:
        state["camera_status"] = "ROS Not Available"
        return None, "ROS Not Available", "N/A", "N/A", "N/A", gr.update(value="Stopped"), state["camera_status"], state["model_path"], None

    img = ros_node.get_inference_frame()
    if img is None:
        state["camera_status"] = "Waiting for get_image_service"
        return state["last_img"], "⚠️ Camera Service Waiting...", "N/A", "N/A", "N/A", gr.update(), state["camera_status"], state["model_path"], None

    if apply_cc:
        img = correct_image(img)

    state["camera_status"] = "OK"
    state["last_img"] = img  # raw image for logging

    if state["auto_inference"] and state["is_running"]:
        state["is_busy"] = True
        try:
            state["step_count"] += 1
            current_step = state["step_count"]

            if current_step == 1:
                if logger_instance:
                    logger_instance.start_session(short_model_name(state["model_path"]), instr, instruction_mode=backend_mode)
                    logger_instance.log_step(current_step, [0.0, 0.0, 0.0], 0, image=img)
                ros_node.control.robust_stop(source="inference_start")
                try:
                    make_backend(backend_mode, api_url).reset(instr)
                except Exception as e:
                    return annotate_image(img), f"❌ Reset failed: {e}", "0 ms", "STOP", "Waiting...", gr.update(value="Stopped"), state["camera_status"], state["model_path"], None
                return annotate_image(img), "Step 1 (Start/Wait)", "0 ms", "0.0000, 0.0000, 0.0000", "Waiting...", gr.update(value="Running (step 1)..."), state["camera_status"], state["model_path"], None

            result = run_backend_inference(img, instr, backend_mode, api_url)
            display_img = annotate_image(img, bbox=result.get("bbox"))
            fig = ros_node.generate_trajectory_plot(result["chunk"])
            if logger_instance:
                logger_instance.log_step(
                    current_step,
                    result["action"],
                    result.get("latency_ms", 0),
                    result["chunk"],
                    image=img,
                    predicted_label=result.get("predicted_label"),
                    grounding_caption=result.get("grounding_caption"),
                    goal_near=result.get("goal_near"),
                    strategy=result.get("strategy"),
                    bbox=result.get("bbox"),
                    instruction_used=result.get("instruction_used"),
                    matched_path_type=result.get("matched_path_type"),
                    speed_scale=result.get("speed_scale"),
                    grounding_cached=result.get("grounding_cached"),
                )
            log = f"Step {current_step} | {result['log_str']}"
            if result.get("goal_near"):
                state["is_running"] = False
                state["step_count"] = 0
                ros_node.control.robust_stop(source="goal_reached")
                if logger_instance:
                    report_path = logger_instance.end_session()
                    log = f"🎯 Goal Reached! (step {current_step}) | Log: {Path(report_path).name}"
                else:
                    log = f"🎯 Goal Reached! (step {current_step})"
                return display_img, log, result["lat_str"], result["act_str"], result["chunk_display"], gr.update(value="Stopped (Goal Reached)"), state["camera_status"], state["model_path"], fig
            return display_img, log, result["lat_str"], result["act_str"], result["chunk_display"], gr.update(value=f"Running (step {current_step})"), state["camera_status"], state["model_path"], fig
        finally:
            state["is_busy"] = False

    info = backend_model_info(backend_mode, api_url)
    if info["model_loaded"]:
        state["model_path"] = info["checkpoint_path"]
        state["model_status"] = f"{backend_mode} ({info['precision']})"
    return annotate_image(img), f"📡 Live | {state['current_log']}", "N/A", "N/A", "N/A", gr.update(), state["camera_status"], state["model_path"], None


def handle_control(direction):
    if not ROS_AVAILABLE or not ros_node:
        return "ROS Error"

    mapping = {
        "W": (LINEAR_SPEED_VLA, 0.0, 0.0),
        "S": (-LINEAR_SPEED_VLA, 0.0, 0.0),
        "A": (0.0, LINEAR_SPEED_VLA, 0.0),
        "D": (0.0, -LINEAR_SPEED_VLA, 0.0),
        "Q": (LINEAR_SPEED_VLA, LINEAR_SPEED_VLA, 0.0),
        "E": (LINEAR_SPEED_VLA, -LINEAR_SPEED_VLA, 0.0),
        "R": (0.0, 0.0, ANGULAR_SPEED_VLA),
        "T": (0.0, 0.0, -ANGULAR_SPEED_VLA),
        "STOP": (0.0, 0.0, 0.0),
    }
    lx, ly, az = mapping[direction]
    if direction == "STOP":
        ros_node.control.robust_stop(source="manual_stop")
        state["current_log"] = "🛑 Force STOP"
    else:
        ros_node.control.move_and_stop_timed(lx, ly, az, source=f"manual_{direction}")
        state["current_log"] = f"🕹️ Moving {direction} (Bang-Bang)"
    return state["current_log"]


def reset_model_wrapper(backend_mode: str, api_url: str, instruction: str):
    try:
        return make_backend(backend_mode, api_url).reset(instruction)
    except Exception as e:
        return f"❌ Reset failed: {e}"


with gr.Blocks(title="VLA PRO Dashboard") as demo:
    gr.Markdown("# 🚀 Mobile VLA Real-time Dashboard & Teleop")

    with gr.Row():
        with gr.Column(scale=2):
            camera_output = gr.Image(label="Live Camera (via Service)", interactive=False)
            gr.Markdown("🟢 Continuous polling via GetImage service")

            with gr.Group():
                gr.Markdown("### 🕹️ Operation Mode")
                mode_radio = gr.Radio(
                    choices=["Manual Drive", "Inference (Auto)", "Inference (18-step)"],
                    value="Manual Drive",
                    label="Controller Mode",
                )

                with gr.Row(visible=False) as inference_panel:
                    with gr.Column():
                        backend_radio = gr.Radio(
                            choices=["Local Runtime", "API Server"],
                            value=DEFAULT_BACKEND_MODE,
                            label="Inference Backend",
                        )
                        api_url_box = gr.Textbox(label="API URL", value=DEFAULT_API_URL)
                        ckpts, confs = scan_local_files()
                        ckpt_dropdown = gr.Dropdown(
                            choices=ckpts,
                            label="🎯 Select Checkpoint (.ckpt/.pth)",
                            value=pick_default_choice(ckpts, "VLA_CHECKPOINT_PATH"),
                        )
                        conf_dropdown = gr.Dropdown(
                            choices=confs,
                            label="⚙️ Select Config (.json)",
                            value=pick_default_choice(confs, "VLA_CONFIG_PATH"),
                        )
                        quant_radio = gr.Radio(
                            choices=["INT8 (Fast)", "FP16 (Accurate)"],
                            value="FP16 (Accurate)",
                            label="Model Precision",
                        )
                        btn_load_model = gr.Button("📂 Load Selected Model", variant="primary")
                        load_status = gr.Textbox(label="Model Status", value="Not Loaded", interactive=False)
                        model_path = gr.Textbox(label="Loaded Checkpoint Path", value="N/A", interactive=False)
                        toggle_cc = gr.Checkbox(label="🎨 RGB Red Gain Boost", value=False)
                    with gr.Column():
                        gr.Markdown("#### 🏁 Inference Control")
                        with gr.Row():
                            btn_start_inf = gr.Button("▶️ START", variant="primary")
                            btn_stop_inf = gr.Button("⏹️ STOP", variant="stop")
                        run_status_box = gr.Textbox(label="Run Status", value="Stopped", interactive=False)

            def on_mode_change(selected_mode):
                state["auto_inference"] = selected_mode in ("Inference (Auto)", "Inference (18-step)")
                state["is_running"] = False
                state["step_count"] = 0
                return gr.Row.update(visible=state["auto_inference"])

            mode_radio.change(fn=on_mode_change, inputs=[mode_radio], outputs=[inference_panel])
            btn_load_model.click(
                fn=load_model_wrapper,
                inputs=[backend_radio, api_url_box, quant_radio, ckpt_dropdown, conf_dropdown],
                outputs=[load_status, model_path],
            )

            with gr.Group():
                gr.Markdown("### 🎮 Manual Controls")
                with gr.Row():
                    btn_q = gr.Button("↖️ Q", scale=1)
                    btn_w = gr.Button("⬆️ W", scale=1)
                    btn_e = gr.Button("↗️ E", scale=1)
                with gr.Row():
                    btn_a = gr.Button("⬅️ A", scale=1)
                    btn_stop = gr.Button("🛑 SPACE (STOP)", variant="danger", scale=1)
                    btn_d = gr.Button("➡️ D", scale=1)
                with gr.Row():
                    btn_r = gr.Button("🔄 CCW (R)", scale=1)
                    btn_s = gr.Button("⬇️ S", scale=1)
                    btn_t = gr.Button("🔄 CW (T)", scale=1)

        with gr.Column(scale=1):
            with gr.Group():
                exp_mode = gr.Dropdown(
                    choices=EXP_MODE_NAMES,
                    value=EXP_MODE_NAMES[0],
                    label="실험 모드",
                )
                exp_config_status = gr.Textbox(label="서버 Config 상태", value="미적용", interactive=False)
                goal_dropdown = gr.Dropdown(
                    choices=["(직접 입력)"] + GOAL_NAV_PRESETS,
                    value=GOAL_NAV_PRESETS[0],
                    label="Goal Object 선택",
                    visible=True,
                )
                path_dropdown = gr.Dropdown(
                    choices=PATH_TYPES,
                    value="right_right",
                    label="Path Type 선택",
                    visible=False,
                )
                instr_box_real = gr.Textbox(label="Robot Prompt (GoalNav: 자연어 물체 설명 / PathType: 경로 코드)", value=DEFAULT_INSTRUCTION)
            camera_status = gr.Textbox(label="Camera Status", value="Unknown", interactive=False)
            status_log = gr.Textbox(label="Status", value="Ready")
            latency_val = gr.Textbox(label="Latency", value="0 ms")
            action_val = gr.Textbox(label="Predicted Action [lx, ly, az]", value="0, 0, 0")
            chunk_val = gr.Textbox(label="Action Chunk Preview", value="N/A", lines=3)
            traj_plot = gr.Plot(label="Predicted Trajectory (XY)")
            btn_reset = gr.Button("🔄 Reset Model History")

    btn_start_inf.click(
        fn=lambda mode, url, instruction: set_running(True, mode, url, instruction),
        inputs=[backend_radio, api_url_box, instr_box_real],
        outputs=run_status_box,
    )
    btn_stop_inf.click(
        fn=lambda: state.update({"is_running": False, "step_count": 0}) or "Stopped",
        outputs=run_status_box,
    )

    directions = {
        btn_w: "W",
        btn_s: "S",
        btn_a: "A",
        btn_d: "D",
        btn_q: "Q",
        btn_e: "E",
        btn_r: "R",
        btn_t: "T",
        btn_stop: "STOP",
    }
    for button, direction in directions.items():
        button.click(fn=handle_control, inputs=[gr.State(direction)], outputs=status_log)

    timer = gr.Timer(0.5, active=True)
    timer.tick(
        fn=update_ui,
        inputs=[mode_radio, backend_radio, api_url_box, instr_box_real, toggle_cc, run_status_box],
        outputs=[camera_output, status_log, latency_val, action_val, chunk_val, run_status_box, camera_status, model_path, traj_plot],
    )

    btn_reset.click(
        fn=reset_model_wrapper,
        inputs=[backend_radio, api_url_box, instr_box_real],
        outputs=status_log,
    )

    def on_exp_mode_change(mode_name, api_url, backend_mode):
        cfg = EXP_MODES.get(mode_name, EXP_MODES[EXP_MODE_NAMES[0]])
        is_goal = "GoalNav" in mode_name
        instr = cfg["instruction"]
        model_key = cfg.get("model")
        desc = cfg.get("desc", "")
        # Apply /config to server if using API backend
        cfg_status = "미적용 (Local 모드)"
        if backend_mode == "API Server":
            try:
                ApiInferenceBackend(api_url).set_config(
                    speed_scaling=cfg["speed_scaling"],
                    grounding_skip_n=cfg["grounding_skip_n"],
                    model=model_key,
                )
                speed_on = cfg["speed_scaling"]
                skip_n = cfg["grounding_skip_n"]
                parts = [f"model={model_key}", f"speed_scaling={speed_on}", f"skip_n={skip_n}"]
                if desc:
                    parts.append(desc)
                cfg_status = "✅ 적용: " + ", ".join(parts)
            except Exception as e:
                cfg_status = f"⚠️ 적용 실패: {e}"
        return (
            gr.update(visible=is_goal),
            gr.update(visible=not is_goal),
            instr,
            cfg_status,
        )

    exp_mode.change(
        fn=on_exp_mode_change,
        inputs=[exp_mode, api_url_box, backend_radio],
        outputs=[goal_dropdown, path_dropdown, instr_box_real, exp_config_status],
    )

    def on_goal_select(choice):
        if choice == "(직접 입력)":
            return gr.update()
        return choice

    goal_dropdown.change(
        fn=on_goal_select,
        inputs=[goal_dropdown],
        outputs=[instr_box_real],
    )

    path_dropdown.change(
        fn=lambda v: v,
        inputs=[path_dropdown],
        outputs=[instr_box_real],
    )

    demo.load(
        None,
        None,
        None,
        js="""
        () => {
            document.addEventListener('keydown', (e) => {
                const key = e.key.toLowerCase();
                const mapping = {'w': 'W', 's': 'S', 'a': 'A', 'd': 'D', 'q': 'Q', 'e': 'E', 'r': 'R', 't': 'T', ' ': 'STOP'};
                if (!mapping[key]) return;
                const buttons = document.querySelectorAll('button');
                for (let b of buttons) {
                    if (b.innerText.includes(mapping[key]) || (mapping[key] === 'STOP' && b.innerText.includes('SPACE'))) {
                        if (!b.disabled) b.click();
                        break;
                    }
                }
            });
        }
        """,
    )


if __name__ == "__main__":
    import socket

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except Exception:
        local_ip = "127.0.0.1"

    requested_port = int(os.getenv("VLA_INFERENCE_PORT", os.getenv("GRADIO_SERVER_PORT", "7865")))
    server_port = pick_server_port(requested_port)
    share_enabled = os.getenv("GRADIO_SHARE", "1").lower() not in {"0", "false", "no"}

    print("=" * 60)
    print("✅ Dashboard starting...")
    print(f"🏠 Local Access: http://{local_ip}:{server_port}")
    print("=" * 60)

    demo.launch(
        server_name="0.0.0.0",
        server_port=server_port,
        share=share_enabled,
        theme=gr.themes.Soft(),
        ssl_verify=False,
    )
