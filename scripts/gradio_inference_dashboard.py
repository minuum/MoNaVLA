import gradio as gr
import requests
import base64
import json
import time
from PIL import Image
import io
import os
import sys
import threading
import numpy as np
import cv2
from datetime import datetime

# --- Forced ROS2 Environment Overrides ---
os.environ["ROS_DOMAIN_ID"] = "42"
os.environ["RMW_IMPLEMENTATION"] = "rmw_fastrtps_cpp"
print(f"🔧 Forced ROS_DOMAIN_ID={os.environ['ROS_DOMAIN_ID']}, RMW={os.environ['RMW_IMPLEMENTATION']}")

# --- Load .vla_env_settings manually ---
env_path = os.getenv("VLA_ENV_PATH", "/home/soda/vla/.vla_env_settings")
if not os.path.exists(env_path):
    env_path = "/home/billy/25-1kp/vla/.vla_env_settings" # fallback
if os.path.exists(env_path):
    with open(env_path, "r") as f:
        for line in f:
            line = line.strip()
            if line.startswith("export "):
                try:
                    key, val = line.replace("export ", "", 1).split("=", 1)
                    os.environ[key] = val.strip('"').strip("'")
                except ValueError:
                    continue
    print("✅ Loaded .vla_env_settings directly into python environment")

# Add internal logging
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
try:
    from inference_logger import get_logger
    logger_instance = get_logger()
except ImportError:
    logger_instance = None

# --- Color Correction Params (Modified: Gains Only) ---
# --- Color Correction Params (Reset to Neutral) ---
CC_PARAMS = {
    'hue_target': 0,
    'hue_width': 0,
    'hue_strength': 0.0,
    'r_gain': 1.0,
    'g_gain': 1.0,
    'b_gain': 1.0,
    'center_boost': 0.0,
    'saturation': 1.0,
    'gamma': 1.0,
    'contrast': 1.0,
    'brightness': 0.0
}

def correct_image(img_pil):
    """Apply Simplified Color Correction (Gains Only) to PIL Image"""
    img_rgb = np.array(img_pil).astype(np.float32)
    # 2. Global Gains Only (Skip Hue Recovery)
    r, g, b = cv2.split(img_rgb)
    r = r * CC_PARAMS['r_gain']
    g = g * CC_PARAMS['g_gain']
    b = b * CC_PARAMS['b_gain']
    img_corrected = cv2.merge([r, g, b])
    
    # Final conversion
    img_final = np.clip(img_corrected, 0, 255).astype(np.uint8)
    return Image.fromarray(img_final)

# --- Matplotlib Optimization ---
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io
import warnings
warnings.filterwarnings("ignore", message="Unable to import Axes3D")

# --- ROS2 Environment Path Discovery ---
def setup_ros_paths():
    """Ensure colcon install paths are in sys.path"""
    import sys
    ros_ws = "/home/billy/25-1kp/vla/ROS_action"
    install_base = os.path.join(ros_ws, "install")
    if os.path.exists(install_base):
        for pkg in os.listdir(install_base):
            pkg_path = os.path.join(install_base, pkg, "local/lib/python3.10/dist-packages")
            if os.path.exists(pkg_path) and pkg_path not in sys.path:
                sys.path.append(pkg_path)
            pkg_path_lib = os.path.join(install_base, pkg, "lib/python3.10/site-packages")
            if os.path.exists(pkg_path_lib) and pkg_path_lib not in sys.path:
                sys.path.append(pkg_path_lib)

setup_ros_paths()

# --- ROS2 & Robot Hardware Imports ---
ROS_AVAILABLE = False
try:
    import rclpy
    from rclpy.node import Node
    from rclpy.callback_groups import ReentrantCallbackGroup
    from cv_bridge import CvBridge
    from geometry_msgs.msg import Twist
    from camera_interfaces.srv import GetImage
    ROS_AVAILABLE = True
except ImportError as e:
    ROS_AVAILABLE = False
    print(f"⚠️ ROS2 environment partially missing: {e}")

# --- Custom Control Library ---
sys.path.insert(0, "/home/soda/vla")
from robovlm_nav.serve.vla_control_utils import VLAControlManager


# --- Configuration ---
API_URL = "http://localhost:8000"
API_KEY = os.getenv("VLA_API_KEY", "vla_devel_key_2026")
DEFAULT_INSTRUCTION = "Navigate toward the gray basket until it is centered in the frame"
LINEAR_SPEED_VLA = 1.15
ANGULAR_SPEED_VLA = 1.15

# --- Local Model Support ---
VLA_ROOT = os.getenv("VLA_ROOT", "/home/billy/25-1kp/vla")
if VLA_ROOT not in sys.path:
    sys.path.insert(0, VLA_ROOT)

# Ensure RoboVLMs is searchable as a package
for root_name in ['RoboVLMs', 'RoboVLMs_upstream', 'third_party/RoboVLMs']:
    p = os.path.join(VLA_ROOT, root_name)
    if os.path.exists(p) and p not in sys.path:
        sys.path.insert(0, p)

try:
    from robovlm_nav.serve.inference_server import MobileVLAInference
    LOCAL_MODEL_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Local model modules not found: {e}")
    LOCAL_MODEL_AVAILABLE = False

local_model_instance = None

def init_local_model(use_quant_str):
    global local_model_instance
    if not LOCAL_MODEL_AVAILABLE:
        return "❌ Module Missing"
    
    # Force reload if requested (even if loaded)
    # Map UI string to boolean: "INT8 (Fast)" -> True, "FP16 (Accurate)" -> False
    use_quant = (use_quant_str == "INT8 (Fast)")
    
    try:
        # Clean up existing model
        if local_model_instance is not None:
             del local_model_instance
             import torch
             torch.cuda.empty_cache()
             print("🔄 Unloaded existing model")

        # Dynamically reload env settings to catch VSCode changes
        env_path = os.getenv("VLA_ENV_PATH", "/home/soda/vla/.vla_env_settings")
        if not os.path.exists(env_path):
            env_path = "/home/billy/25-1kp/vla/.vla_env_settings" # fallback
        if os.path.exists(env_path):
            with open(env_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("export "):
                        try:
                            key, val = line.replace("export ", "", 1).split("=", 1)
                            os.environ[key] = val.strip('"').strip("'")
                        except ValueError:
                            continue
            print("🔄 Reloaded .vla_env_settings dynamically")

        ckpt = os.getenv("VLA_CHECKPOINT_PATH")
        if not ckpt:
            state["model_status"] = "Missing VLA_CHECKPOINT_PATH"
            state["model_path"] = "N/A"
            return "❌ VLA_CHECKPOINT_PATH not set"
            
        # --- Auto-Detect Configuration based on Checkpoint Path ---
        config = os.getenv("VLA_CONFIG_PATH", "")
        if not config or not os.path.exists(config):
            import re
            import glob
            configs_dir = "/home/billy/25-1kp/vla/Mobile_VLA/configs"
            # Extract identifiers like exp04, exp-04, etc.
            match = re.search(r'(exp[-_]?\d+)', ckpt.lower())
            if match:
                exp_id = match.group(1).replace('-', '').replace('_', '') # e.g. exp04
                all_configs = glob.glob(os.path.join(configs_dir, "*.json"))
                # Match normalized strings
                matched = [c for c in all_configs if exp_id in os.path.basename(c).lower().replace('-', '').replace('_', '')]
                if matched:
                    config = matched[0]
                    print(f"🔍 Auto-detected config based on checkpoint: {os.path.basename(config)}")
            
            # Fallback if detection fails
            if not config or not os.path.exists(config):
                config = "/home/billy/25-1kp/vla/Mobile_VLA/configs/mobile_vla_v3_exp01_aug.json"
                print(f"⚠️ Could not auto-detect. Using fallback config: {os.path.basename(config)}")
        else:
            print(f"✅ Using explicitly set config from VLA_CONFIG_PATH: {os.path.basename(config)}")

        print(f"Loading Local Model: {ckpt} (Quant: {use_quant})")
        
        # Pass use_quant explicitely
        local_model_instance = MobileVLAInference(ckpt, config, use_quant=use_quant)
        
        # DEBUG: Verify reset method
        print(f"DEBUG: Model Type: {type(local_model_instance)}")
        print(f"DEBUG: Has reset method: {hasattr(local_model_instance, 'reset')}")
        if not hasattr(local_model_instance, 'reset'):
            print(f"DEBUG: Available methods: {[m for m in dir(local_model_instance) if not m.startswith('_')]}")
            
        state["model_status"] = f"Loaded ({'INT8' if use_quant else 'FP16'})"
        state["model_path"] = ckpt
        # Get parent directory name for better context instead of just epoch_epoch...ckpt
        short_name = f"{os.path.basename(os.path.dirname(ckpt))}/{os.path.basename(ckpt)}"
        return f"✅ Loaded: {short_name} ({'INT8' if use_quant else 'FP16'})"
    except Exception as e:
        import traceback
        traceback.print_exc()
        state["model_status"] = "Load Failed"
        return f"❌ Load Failed: {e}"

# --- ROS2 Node ---
class ROSDashboardNode(Node):
    def __init__(self):
        super().__init__('gradio_dashboard_node')
        self.callback_group = ReentrantCallbackGroup()
        self.cv_bridge = CvBridge()
        self.get_image_client = self.create_client(
            GetImage, 'get_image_service', callback_group=self.callback_group)
        self.cmd_pub = self.create_publisher(Twist, '/cmd_vel', 10, callback_group=self.callback_group)
        
        # ✅ Unified Precision Control Manager
        self.control = VLAControlManager(self, default_throttle=50, move_duration=0.4)

    def get_inference_frame(self):
        if not self.get_image_client.wait_for_service(timeout_sec=1.0):
            return None
        request = GetImage.Request()
        future = self.get_image_client.call_async(request)
        start_time = time.time()
        while rclpy.ok() and not future.done():
            if time.time() - start_time > 2.0: return None
            time.sleep(0.01)
        if future.done():
            try:
                response = future.result()
                if response and response.image.data:
                    cv_image = self.cv_bridge.imgmsg_to_cv2(response.image, "bgr8")
                    return Image.fromarray(cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB))
            except: pass
        return None

    def generate_trajectory_plot(self, full_chunk, model_name="VLA"):
        """Generate 2D Matplotlib plot for the given chunk"""
        if full_chunk is None or len(full_chunk) == 0:
            return None
        
        # Trajectory Integration
        DT = 0.2
        traj_x = [0]
        traj_y = [0]
        curr_x, curr_y = 0, 0
        
        for step in full_chunk:
            vx, vy = float(step[0]), float(step[1])
            curr_x += vx * DT
            curr_y += vy * DT
            traj_x.append(curr_x)
            traj_y.append(curr_y)
            
        fig, ax = plt.subplots(figsize=(5, 5))
        # Start point
        ax.plot(0, 0, 'ko', markersize=8, label='Start')
        # Orientation arrow (x-axis)
        ax.arrow(0, 0, 0.2, 0, head_width=0.05, head_length=0.05, fc='k', ec='k')
        
        # Trajectory line
        ax.plot(traj_x, traj_y, 'b-', linewidth=3, alpha=0.8, label=f'{model_name}')
        ax.plot(traj_x[-1], traj_y[-1], 'b*', markersize=10) # End point
        
        ax.set_title("Predicted Trajectory (2D XY)")
        ax.set_xlabel("Forward (X) [m]")
        ax.set_ylabel("Left/Right (Y) [m]")
        ax.grid(True, linestyle='--', alpha=0.6)
        ax.set_aspect('equal')
        
        # Auto-scale with some margin
        all_points = np.column_stack((traj_x, traj_y))
        mins = np.min(all_points, axis=0) - 0.5
        maxs = np.max(all_points, axis=0) + 0.5
        ax.set_xlim(min(mins[0], -0.5), max(maxs[0], 2.0))
        ax.set_ylim(min(mins[1], -1.0), max(maxs[1], 1.0))
        
        return fig

ros_node = None
if ROS_AVAILABLE:
    if not rclpy.ok(): rclpy.init()
    ros_node = ROSDashboardNode()
    threading.Thread(target=lambda: rclpy.spin(ros_node), daemon=True).start()

# --- Shared State ---
# --- Shared State ---
state = {
    "auto_inference": False, # Flag to run inference loop
    "is_running": False, # Actual running state (controlled by Start/Stop buttons)
    "is_busy": False,    # Prevent overlapping calls from Gradio timer (Avoid OOM/Concurrency bugs)
    "step_count": 0,
    "max_steps": 18,
    "instruction": DEFAULT_INSTRUCTION,
    "last_img": None,
    "current_log": "Ready",
    "camera_status": "Unknown",
    "model_status": "Not Loaded",
    "model_path": "N/A"
}

def update_ui(mode, instr, apply_cc, is_running_ui):
    # Global Concurrency Guard: If previous tick is still processing VLM inference, skip this tick.
    if state["is_busy"]:
        return gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update()
    
    # Sync UI state to internal state if needed, but primarily controlled by buttons
    state["auto_inference"] = (mode == "Inference (18-step)")
    
    if not ROS_AVAILABLE or ros_node is None:
        state["camera_status"] = "ROS Not Available"
        return None, "ROS Not Available", "N/A", "N/A", "N/A", gr.update(value="Stopped"), state["camera_status"], state["model_path"]
    
    img = ros_node.get_inference_frame()
    if img is None:
        state["camera_status"] = "Waiting for get_image_service"
        return state["last_img"], "⚠️ Camera Service Waiting...", "N/A", "N/A", "N/A", gr.update(), state["camera_status"], state["model_path"]
    
    if apply_cc:
        try:
            img = correct_image(img)
        except Exception as e:
            print(f"CC Error: {e}")
    
    state["camera_status"] = "OK"
    state["last_img"] = img
    
    # Logic for Inference Execution
    if state["auto_inference"] and state["is_running"]:
        state["is_busy"] = True # LOCK
        try:
            state["step_count"] += 1
            current_step = state["step_count"]
            
            # Step 1: Force Stop/Wait (Initial Setup) - Matching Data Collector
            if current_step == 1:
                log = "1/18 (Start/Wait)"
                lat = "0 ms"
                act = "STOP"
                chunk_info = "Waiting..."
                
                # [LOGGING] Unified session start
                if logger_instance: 
                    model_id = os.path.basename(os.getenv("VLA_CHECKPOINT_PATH", "Mobile-VLA"))
                    logger_instance.start_session(model_id, instr)

                if ROS_AVAILABLE and ros_node:
                     ros_node.control.robust_stop(source="inference_start")
                
                # Reset model history ensuring clean state
                if local_model_instance: 
                    try:
                        local_model_instance.reset(instruction=instr)
                    except TypeError:
                        local_model_instance.reset()
                        
                # 📸 [Image Cap] Always log step1 image
                if logger_instance:
                    logger_instance.log_step(current_step, [0.0, 0.0], 0, image=img)
                
                return img, log, lat, act, chunk_info, gr.update(value="Running (1/18)..."), state["camera_status"], state["model_path"]

            # Step 2~18: Run Inference (17 steps of action)
            elif current_step <= state["max_steps"]:
                # Returns: log_str, lat_str, act_str, chunk_str, action, lat, chunk
                res = run_api_inference(img, instr, use_local=True)
                log_inf, lat_str, act_str, chunk_str, raw_act, raw_lat, raw_chunk = res
                
                # [VISUALIZATION] Generate Trajectory Plot
                fig = None
                if ROS_AVAILABLE and ros_node:
                    fig = ros_node.generate_trajectory_plot(raw_chunk)

                # [LOGGING] Unified step logging
                if logger_instance: 
                    logger_instance.log_step(current_step, raw_act, raw_lat, raw_chunk, image=img)
                
                log = f"{current_step}/18 | {log_inf}"
                return img, log, lat_str, act_str, chunk_str, gr.update(value=f"Running ({current_step}/18)"), state["camera_status"], state["model_path"], fig
                
            # Step > 18: Finish
            else:
                state["is_running"] = False
                state["step_count"] = 0
                if logger_instance: 
                    report_path = logger_instance.end_session()
                    completion_msg = f"✅ Completed (18 Steps) | Log: {os.path.basename(report_path)}"
                else:
                    completion_msg = "✅ Completed (18 Steps)"
                    
                if ROS_AVAILABLE and ros_node:
                     ros_node.control.robust_stop(source="inference_done")
                return img, completion_msg, "0 ms", "STOP", "N/A", gr.update(value="Stopped (Finished)"), state["camera_status"], state["model_path"], None

        finally:
            state["is_busy"] = False # UNLOCK
            
    # Not running or Manual Mode
    return img, f"📡 Live | {state['current_log']}", "N/A", "N/A", "N/A", gr.update(), state["camera_status"], state["model_path"], None


def run_api_inference(image, instruction, use_local):
    """
    Returns: log_str, lat_str, act_str, chunk_str, action, lat, chunk
    """
    # Default return if error
    error_res = ("❌ Error", "N/A", "N/A", "N/A", np.zeros(2), 0.0, np.zeros((1, 2)))

    # Local Inference Mode
    if use_local:
        global local_model_instance
        if local_model_instance is None:
            return ("⚠️ Model Not Loaded", "0 ms", "0.0, 0.0", "N/A", np.zeros(2), 0.0, np.zeros((1, 2)))
        
        try:
            buffered = io.BytesIO()
            image.save(buffered, format="JPEG")
            img_b64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
            
            # Predict returns action, lat, full_chunk
            action, lat, chunk = local_model_instance.predict(img_b64, instruction)
            
            # Format action chunk for display
            chunk_str = np.array2string(chunk, precision=2, separator=', ', suppress_small=True)
            chunk_display = f"Chunk (N={len(chunk)}):\n{chunk_str}"
            
            if ROS_AVAILABLE and ros_node:
                # 0.4s Duration matching Data Collector
                state["current_log"] = ros_node.control.move_and_stop_timed(action[0], action[1], 0.0, source="local_inference")
            
            # Format UI strings
            log_str = f"✅ Local: {state['current_log']}"
            lat_str = f"{lat:.1f} ms"
            act_str = f"{action[0]:.4f}, {action[1]:.4f}"
            
            return log_str, lat_str, act_str, chunk_display, action, lat, chunk
        except Exception as e:
            print(f"Inference Exception: {e}")
            import traceback
            traceback.print_exc()
            return (f"❌ Local Error: {e}", "N/A", "N/A", "N/A", np.zeros(2), 0.0, np.zeros((1, 2)))

    # Remote API Mode (Legacy)
    return ("❌ API Not Supported", "N/A", "N/A", "N/A", np.zeros(2), 0.0, np.zeros((1, 2)))

# --- Control Handlers ---
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
        "STOP": (0.0, 0.0, 0.0)
    }
    
    if direction in mapping:
        lx, ly, az = mapping[direction]
        if direction == "STOP":
            ros_node.control.robust_stop(source="manual_stop")
            state["current_log"] = "🛑 Force STOP"
        else:
            ros_node.control.move_and_stop_timed(lx, ly, az, source=f"manual_{direction}")
            state["current_log"] = f"🕹️ Moving {direction} (Bang-Bang)"
    return state["current_log"]

# --- Gradio UI ---
with gr.Blocks(title="VLA PRO Dashboard") as demo:
    gr.Markdown("# 🚀 Mobile VLA Real-time Dashboard & Teleop")
    
    with gr.Row():
        with gr.Column(scale=2):
            camera_output = gr.Image(label="Live Camera (via Service)", interactive=False)
            with gr.Row():
                gr.Markdown("🟢 Continuous polling via GetImage service")
                # Removed Auto-Inference Checkbox, replaced with Radio Mode
                
            
            with gr.Group():
                gr.Markdown("### 🕹️ Operation Mode")
                mode_radio = gr.Radio(choices=["Manual Drive", "Inference (18-step)"], value="Manual Drive", label="Controller Mode")
                
                with gr.Row(visible=False) as inference_panel:
                    with gr.Column():
                        quant_radio = gr.Radio(choices=["INT8 (Fast)", "FP16 (Accurate)"], value="FP16 (Accurate)", label="Model Precision")
                        btn_load_model = gr.Button("📂 Load Local Model (Checkpoints)")
                        load_status = gr.Textbox(label="Model Status", value="Not Loaded", interactive=False)
                        model_path = gr.Textbox(label="Loaded Checkpoint Path", value="N/A", interactive=False)
                        toggle_cc = gr.Checkbox(label="🎨 RGB Red Gain Boost", value=False)
                    with gr.Column():
                        gr.Markdown("#### 🏁 Inference Control")
                        with gr.Row():
                            btn_start_inf = gr.Button("▶️ START (18 Steps)", variant="primary")
                            btn_stop_inf = gr.Button("⏹️ STOP", variant="stop")
                        run_status_box = gr.Textbox(label="Run Status", value="Stopped", interactive=False)
            
            def on_mode_change(mode):
                state["auto_inference"] = (mode == "Inference (18-step)")
                # Reset running state when mode changes
                state["is_running"] = False
                state["step_count"] = 0
                return gr.Row.update(visible=state["auto_inference"])

            def set_running(running):
                state["is_running"] = running
                if running:
                    state["step_count"] = 0 # Reset counter on start
                    # Reset model history if needed
                    if local_model_instance: local_model_instance.reset()
                return "Running..." if running else "Stopped"

            mode_radio.change(fn=on_mode_change, inputs=[mode_radio], outputs=[inference_panel])
            mode_radio.change(fn=on_mode_change, inputs=[mode_radio], outputs=[inference_panel])
            btn_load_model.click(fn=init_local_model, inputs=[quant_radio], outputs=load_status)
            
            btn_start_inf.click(fn=lambda: set_running(True), outputs=run_status_box)
            btn_stop_inf.click(fn=lambda: set_running(False), outputs=run_status_box)

            with gr.Group():
                gr.Markdown("### 🎮 Manual Controls")
                with gr.Row():
                    btn_q = gr.Button("↖️ Q", scale=1); btn_w = gr.Button("⬆️ W", scale=1); btn_e = gr.Button("↗️ E", scale=1)
                with gr.Row():
                    btn_a = gr.Button("⬅️ A", scale=1); btn_stop = gr.Button("🛑 SPACE (STOP)", variant="danger", scale=1); btn_d = gr.Button("➡️ D", scale=1)
                with gr.Row():
                    btn_r = gr.Button("🔄 CCW (R)", scale=1); btn_s = gr.Button("⬇️ S", scale=1); btn_t = gr.Button("🔄 CW (T)", scale=1)
            
        with gr.Column(scale=1):
            instr_box = gr.Textbox(label="Robot Prompt", value=DEFAULT_INSTRUCTION)
            camera_status = gr.Textbox(label="Camera Status", value="Unknown", interactive=False)
            status_log = gr.Textbox(label="Status", value="Ready")
            latency_val = gr.Textbox(label="Latency", value="0 ms")
            action_val = gr.Textbox(label="Predicted Action [v, w]", value="0, 0")
            chunk_val = gr.Textbox(label="Action Chunk Preview", value="N/A", lines=2)
            
            # --- Trajectory Visualization ---
            traj_plot = gr.Plot(label="Predicted Trajectory (XY)")
            
            btn_reset = gr.Button("🔄 Reset Model History")
            
            gr.Markdown("---")
            gr.Markdown("""
            ### ⌨️ Keyboard Shortcuts
            - **W/A/S/D/Q/E**: Move (0.4s)
            - **R/T**: Spin
            - **Space**: Stop
            """)

    # Event Bindings
    directions = {
        btn_w: "W", btn_s: "S", btn_a: "A", btn_d: "D",
        btn_q: "Q", btn_e: "E", btn_r: "R", btn_t: "T",
        btn_stop: "STOP"
    }
    for btn, d in directions.items():
        btn.click(fn=handle_control, inputs=[gr.State(d)], outputs=status_log)

    # Timer: VLA Inference (0.4s move) takes time. We use 0.5s ticks and a busy-lock to prevent OOM.
    timer = gr.Timer(0.5, active=True)
    timer.tick(
        fn=update_ui,
        inputs=[mode_radio, instr_box, toggle_cc, run_status_box],
        outputs=[camera_output, status_log, latency_val, action_val, chunk_val, run_status_box, camera_status, model_path, traj_plot]
    )


    def reset_model_wrapper():
        if local_model_instance:
            local_model_instance.reset()
            return "✅ Local History Cleared"
        try:
            requests.post(f"{API_URL}/reset", headers={"X-API-Key": API_KEY}, timeout=2)
            return "✅ API Reset Success"
        except: return "❌ Reset failed"
    btn_reset.click(fn=reset_model_wrapper, outputs=status_log)

    demo.load(None, None, None, js="""
    () => {
        document.addEventListener('keydown', (e) => {
            const key = e.key.toLowerCase();
            const mapping = {
                'w': 'W', 's': 'S', 'a': 'A', 'd': 'D',
                'q': 'Q', 'e': 'E', 'r': 'R', 't': 'T',
                ' ': 'STOP'
            };
            if (mapping[key]) {
                const buttons = document.querySelectorAll('button');
                for (let b of buttons) {
                    if (b.innerText.includes(mapping[key]) || (mapping[key] === 'STOP' && b.innerText.includes('SPACE'))) {
                        if (!b.disabled) b.click();
                        break;
                    }
                }
            }
        });
    }
    """)

if __name__ == "__main__":
    # 🌍 [Fixed URL Setup]
    # 1. Local Network: Always available at http://<LOCAL_IP>:7865
    # 2. Public URL: Use ngrok for fixed domain (optional)
    
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except:
        local_ip = "127.0.0.1"
        
    print("="*60)
    print(f"✅ Dashboard starting...")
    print(f"🏠 Local Access: http://{local_ip}:7865")
    print("="*60)
    
    # Optional: Start ngrok if installed and token present
    # This gives a stable public URL if you have a paid ngrok plan, or a random one otherwise
    # but it separates the public link management from Gradio's built-in share.
    
    # [Gradio Launch]
    # 1. server_name="0.0.0.0": Allows access from other devices on the same Wi-Fi (Fixed IP)
    # 2. share=True: Generates a public link (Randomly changes every restart)
    #    * Note: To get a FIXED public link, you need a paid Ngrok account or persistent tunnel.
    #    * For local development, use the "Local Access" IP printed above (http://192.168.x.x:7865)
    
    print(f"🌍 Public Share: Enabled (Link will be random due to free tier limit)")
    
    demo.launch(
        server_name="0.0.0.0", 
        server_port=7865, 
        share=True,   # ✅ Use Share Link (Random URL) as requested
        theme=gr.themes.Soft(),
        ssl_verify=False
    )
