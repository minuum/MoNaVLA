#!/usr/bin/env python3
"""
Object Recognition Demo — Kosmos-2 그라운딩 인터랙티브 테스트
ROS 카메라 자동 피드 / 이미지 업로드 → bbox 오버레이 + VLA 추론 연동

Port: 7863

Usage:
  python3 scripts/gradio_grounding_demo.py
  python3 scripts/gradio_grounding_demo.py --preload
"""
import argparse
import base64
import io
import os
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import cv2
import gradio as gr
import numpy as np
import requests
import torch
from PIL import Image, ImageDraw

from scripts.run_grounding_realtime import (
    load_model,
    ground,
    draw_overlay,
    check_hit,
    DEFAULT_VLM,
    DEFAULT_ADAPTERS,
)

# ─── ROS 환경 설정 ────────────────────────────────────────────────────────────

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")
os.environ.setdefault("ROS_HOME", "/tmp/ros")
os.environ["ROS_DOMAIN_ID"] = "42"
os.environ["RMW_IMPLEMENTATION"] = "rmw_fastrtps_cpp"


def prepend_env_path(key: str, value: str) -> None:
    current = os.environ.get(key, "")
    parts = [p for p in current.split(os.pathsep) if p]
    if value not in parts:
        os.environ[key] = value if not parts else f"{value}{os.pathsep}{current}"


def setup_ros_paths() -> None:
    ros_ws = Path(os.getenv("VLA_ROS_WS", str(ROOT / "ROS_action")))
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
        for candidate in (
            pkg / "local/lib/python3.10/dist-packages",
            pkg / "lib/python3.10/site-packages",
        ):
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
    from camera_interfaces.srv import GetImage

    ROS_AVAILABLE = True
    print("[DEMO] ROS2 available ✅")
except ImportError as e:
    print(f"[DEMO] ROS2 unavailable: {e}")

    class Node:
        pass

    class ReentrantCallbackGroup:
        pass


# ─── ROS 카메라 노드 ───────────────────────────────────────────────────────────

class ROSCameraNode(Node):
    def __init__(self):
        super().__init__("grounding_demo_camera_node")
        self.callback_group = ReentrantCallbackGroup()
        self.cv_bridge = CvBridge()
        self.get_image_client = self.create_client(
            GetImage, "get_image_service", callback_group=self.callback_group
        )

    def get_frame(self) -> Image.Image | None:
        if not self.get_image_client.wait_for_service(timeout_sec=1.0):
            return None
        request = GetImage.Request()
        future = self.get_image_client.call_async(request)
        start = time.time()
        while rclpy.ok() and not future.done():
            if time.time() - start > 2.0:
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


ros_node: ROSCameraNode | None = None
if ROS_AVAILABLE:
    try:
        if not rclpy.ok():
            rclpy.init()
        ros_node = ROSCameraNode()
        threading.Thread(target=lambda: rclpy.spin(ros_node), daemon=True).start()
        print("[DEMO] ROSCameraNode started ✅")
    except Exception as e:
        ROS_AVAILABLE = False
        ros_node = None
        print(f"[DEMO] ROSCameraNode disabled: {e}")


# ─── 공유 카메라 상태 ──────────────────────────────────────────────────────────

_last_frame: np.ndarray | None = None
_cam_ok = False


def _fetch_ros_frame() -> np.ndarray | None:
    global _last_frame, _cam_ok
    if not ROS_AVAILABLE or ros_node is None:
        _cam_ok = False
        return None
    img = ros_node.get_frame()
    if img is None:
        _cam_ok = False
        return _last_frame  # 이전 프레임 유지
    arr = np.array(img)
    _last_frame = arr
    _cam_ok = True
    return arr


def timer_tick():
    """gr.Timer tick — 카메라 프레임을 가져와 모든 live feed 업데이트."""
    frame = _fetch_ros_frame()
    status = "📷 Live ✅" if _cam_ok else ("ROS 연결됨, 서비스 대기 중…" if ROS_AVAILABLE else "❌ ROS 없음")
    return frame, frame, frame, status  # (vla_cam, alias_cam, grnd_cam, status_txt)


# ─── 모델 싱글톤 ───────────────────────────────────────────────────────────────

_state: dict = {"model": None, "processor": None, "adapter": None}
_DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

ADAPTER_OPTIONS = {
    "Pure Kosmos-2": None,
    "Exp56 LoRA":    DEFAULT_ADAPTERS.get("exp56"),
}

PRESET_ALIASES = {
    "🧺 basket": "gray basket\ngray box\ncontainer\nbin\nlaundry basket",
    "🔴 ball":   "red ball\norange ball\nball\nsphere",
    "🚪 door":   "door\nexit\nentrance",
    "🏛 wall":   "white wall\ncorridor wall\nwall",
    "🛣 corridor": "corridor\nhallway\npassage",
}

GOAL_NAV_PRESETS = [
    "the gray basket on right",
    "the gray basket on left",
    "the gray basket",
    "the door",
    "the corridor on the left",
    "the corridor on the right",
]

ACTION_COLORS = {
    "FORWARD":   (46, 204, 113),
    "LEFT":      (52, 152, 219),
    "RIGHT":     (230, 126, 34),
    "FWD+LEFT":  (26, 188, 156),
    "FWD+RIGHT": (243, 156, 18),
    "ROT_L":     (155, 89, 182),
    "ROT_R":     (231, 76, 60),
    "STOP":      (149, 165, 166),
}

API_URL = "http://localhost:8001"


def _ensure_model(adapter_label: str):
    if _state["model"] is None or _state["adapter"] != adapter_label:
        adapter_path = ADAPTER_OPTIONS.get(adapter_label)
        print(f"[LOAD] {adapter_label} ...")
        model, processor = load_model(DEFAULT_VLM, adapter_path, _DEVICE)
        _state.update(model=model, processor=processor, adapter=adapter_label)
    return _state["model"], _state["processor"]


def _to_numpy(image) -> np.ndarray | None:
    if image is None:
        return None
    if isinstance(image, np.ndarray):
        return image
    return np.array(image.convert("RGB"))


def _img_to_b64(img_np: np.ndarray) -> str:
    pil = Image.fromarray(img_np)
    buf = io.BytesIO()
    pil.save(buf, format="JPEG", quality=90)
    return base64.b64encode(buf.getvalue()).decode()


def annotate_image(img_np: np.ndarray, bbox: dict | None = None,
                   label: str = "", draw_grid: bool = True) -> np.ndarray:
    """3×3 격자 + bbox 오버레이 (inference_dashboard 동일 스타일)."""
    arr = img_np.copy()
    h, w = arr.shape[:2]

    if draw_grid:
        color = (100, 255, 100)
        cv2.line(arr, (w // 3, 0), (w // 3, h), color, 1)
        cv2.line(arr, (2 * w // 3, 0), (2 * w // 3, h), color, 1)
        cv2.line(arr, (0, h // 3), (w, h // 3), color, 1)
        cv2.line(arr, (0, 2 * h // 3), (w, 2 * h // 3), color, 1)

    if bbox:
        cx_px = int(bbox.get("cx", 0.5) * w)
        cy_px = int(bbox.get("cy", 0.5) * h)
        ent = str(bbox.get("entity", label or "bbox"))
        color_rgb = ACTION_COLORS.get(label, (255, 80, 80))
        color_bgr = (color_rgb[2], color_rgb[1], color_rgb[0])

        if "x1" in bbox:
            x1, y1 = int(bbox["x1"] * w), int(bbox["y1"] * h)
            x2, y2 = int(bbox["x2"] * w), int(bbox["y2"] * h)
            cv2.rectangle(arr, (x1, y1), (x2, y2), color_bgr, 2)
        else:
            r = 10
            cv2.line(arr, (cx_px - r, cy_px), (cx_px + r, cy_px), color_bgr, 2)
            cv2.line(arr, (cx_px, cy_px - r), (cx_px, cy_px + r), color_bgr, 2)

        cv2.circle(arr, (cx_px, cy_px), 4, color_bgr, -1)
        txt = f"{label}  {ent[:15]}" if label else ent[:20]
        cv2.putText(arr, txt, (max(cx_px - 40, 0), max(cy_px - 10, 14)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, color_bgr, 1, cv2.LINE_AA)
    return arr


# ─── Grounding 탭 로직 ────────────────────────────────────────────────────────

def run_grounding(image, phrase: str, adapter_label: str):
    if image is None:
        return None, "⚠️ 이미지가 없습니다 (카메라 연결 또는 업로드)", ""
    phrase = phrase.strip()
    if not phrase:
        return None, "⚠️ Phrase를 입력해주세요", ""

    model, proc = _ensure_model(adapter_label)
    img_np = _to_numpy(image)
    result = ground(model, proc, img_np, phrase, _DEVICE)
    overlay = draw_overlay(img_np, phrase, result)
    hit = check_hit(result, phrase)

    entity_lines = []
    for ent_name, ent_boxes, _ in result.get("entities", []):
        for box in ent_boxes:
            x1, y1, x2, y2 = box
            entity_lines.append(
                f"  [{ent_name}]  cx={((x1+x2)/2):.2f}  cy={((y1+y2)/2):.2f}"
                f"  area={((x2-x1)*(y2-y1)):.3f}"
            )

    status = f"{'HIT' if hit else 'MISS'}   {result.get('caption', '')}"
    return overlay, status, "\n".join(entity_lines) or "  (감지 없음)"


def run_alias_test(image, alias_text: str, adapter_label: str):
    if image is None:
        return None, "⚠️ 이미지가 없습니다"
    phrases = [p.strip() for p in alias_text.splitlines() if p.strip()]
    if not phrases:
        return None, "⚠️ Phrase를 한 줄씩 입력해주세요"

    model, proc = _ensure_model(adapter_label)
    img_np = _to_numpy(image)

    rows, overlays = [], []
    for phrase in phrases:
        r = ground(model, proc, img_np, phrase, _DEVICE)
        hit = check_hit(r, phrase)
        entities = [e for e, _, _ in r.get("entities", [])]
        rows.append((phrase, hit, entities, r.get("caption", "")[:50]))
        overlays.append(draw_overlay(img_np, phrase, r))

    cols = min(len(overlays), 3)
    n_rows = (len(overlays) + cols - 1) // cols
    W, H = overlays[0].size
    LABEL_H = 22
    grid = Image.new("RGB", (W * cols, (H + LABEL_H) * n_rows), (30, 30, 30))

    for i, (ov, (phrase, hit, _, _)) in enumerate(zip(overlays, rows)):
        ri, ci = divmod(i, cols)
        cell = Image.new("RGB", (W, H + LABEL_H), (30, 30, 30))
        d = ImageDraw.Draw(cell)
        lc = (80, 200, 120) if hit else (220, 80, 80)
        d.rectangle([0, 0, W, LABEL_H], fill=(20, 20, 20))
        d.text((6, 4), f"{'HIT' if hit else 'MISS'}  {phrase}", fill=lc)
        cell.paste(ov, (0, LABEL_H))
        grid.paste(cell, (ci * W, ri * (H + LABEL_H)))

    hit_count = sum(1 for _, hit, _, _ in rows if hit)
    lines = [f"Hit: {hit_count} / {len(phrases)}\n"]
    for phrase, hit, entities, _ in rows:
        ent_str = ", ".join(entities) if entities else "—"
        lines.append(f"{'HIT' if hit else 'MISS'}  {phrase:<25}  [{ent_str}]")

    return grid, "\n".join(lines)


# ─── VLA 로직 ────────────────────────────────────────────────────────────────

def _vla_call(img_np: np.ndarray, instruction: str) -> dict:
    b64 = _img_to_b64(img_np)
    r = requests.post(f"{API_URL}/predict",
                      json={"image": b64, "instruction": instruction}, timeout=30)
    r.raise_for_status()
    return r.json()


def run_vla_predict(image, instruction: str):
    if image is None:
        return None, "⚠️ 카메라 프레임 없음 (카메라 연결 또는 업로드)", ""
    instruction = instruction.strip()
    if not instruction:
        return None, "⚠️ Instruction을 입력해주세요", ""

    img_np = _to_numpy(image)
    try:
        d = _vla_call(img_np, instruction)
    except Exception as e:
        return None, f"❌ API 오류: {e}", ""

    label = d.get("predicted_label", "?")
    out_arr = annotate_image(img_np, d.get("bbox"), label)

    status = (
        f"▶  {label}\n"
        f"latency: {d['latency_ms']:.1f}ms  |  grounding: {d.get('grounding_latency_ms',0):.1f}ms\n"
        f"goal_near: {d.get('goal_near_proxy','?')}  |  model: {d.get('model_name','?')}\n"
        f"caption: {d.get('grounding_caption','')}"
    )

    bbox = d.get("bbox") or {}
    if "cx" in bbox:
        bbox_info = f"entity: {bbox.get('entity','?')}\ncx={bbox['cx']:.3f}  cy={bbox['cy']:.3f}  area={bbox.get('area',0):.3f}"
    elif "x1" in bbox:
        bbox_info = f"entity: {bbox.get('entity','?')}\nx1={bbox['x1']:.3f}  y1={bbox['y1']:.3f}  x2={bbox['x2']:.3f}  y2={bbox['y2']:.3f}"
    else:
        bbox_info = "(bbox 없음)"

    return out_arr, status, bbox_info


def run_vla_alias(image, alias_text: str):
    if image is None:
        return None, "⚠️ 카메라 프레임 없음"
    phrases = [p.strip() for p in alias_text.splitlines() if p.strip()]
    if not phrases:
        return None, "⚠️ Phrase를 한 줄씩 입력해주세요"

    img_np = _to_numpy(image)
    results = []
    last_d = None

    for phrase in phrases:
        try:
            d = _vla_call(img_np, phrase)
            label = d.get("predicted_label", "?")
            cx = f"{d['bbox']['cx']:.3f}" if d.get("bbox") and "cx" in d["bbox"] else "—"
            results.append((phrase, label, d.get("latency_ms", 0), cx))
            last_d = d
        except Exception as e:
            results.append((phrase, f"ERR:{e}", 0, "—"))

    out_arr = annotate_image(img_np, (last_d or {}).get("bbox"),
                             (last_d or {}).get("predicted_label", ""))

    lines = ["Phrase → Action  (VLA Alias Test)\n"]
    action_counts: dict[str, int] = {}
    for phrase, label, latency, cx in results:
        action_counts[label] = action_counts.get(label, 0) + 1
        lines.append(f"{label:<12}  {phrase:<30}  cx={cx}  ({latency:.0f}ms)")

    lines.append("\n─── 액션 분포 ───")
    for action, cnt in sorted(action_counts.items(), key=lambda x: -x[1]):
        lines.append(f"{action:<12} {'█' * cnt} {cnt}")

    return out_arr, "\n".join(lines)


def reset_api_history():
    try:
        r = requests.post(f"{API_URL}/reset", timeout=5)
        return f"리셋 완료  ({r.json()})"
    except Exception as e:
        return f"오류: {e}"


# ─── UI 빌드 ──────────────────────────────────────────────────────────────────

def build_ui() -> gr.Blocks:
    cam_status_init = "📷 Live ✅" if ROS_AVAILABLE else "❌ ROS 없음 (업로드 사용)"

    with gr.Blocks(title="Object Recognition Demo") as demo:
        gr.Markdown("# Object Recognition Demo")

        # 상단 상태 바
        with gr.Row():
            cam_status_txt = gr.Textbox(
                value=cam_status_init, label="카메라 상태",
                interactive=False, scale=4,
            )
            adapter_dd = gr.Dropdown(
                choices=list(ADAPTER_OPTIONS.keys()),
                value="Pure Kosmos-2",
                label="Grounding 모델", scale=2,
            )

        with gr.Tabs():

            # ── 탭 1: Grounding ──────────────────────────────────────────────
            with gr.TabItem("Grounding"):
                with gr.Row():
                    with gr.Column():
                        img_g = gr.Image(
                            interactive=False,
                            label="📷 Live Camera (자동 갱신)",
                        )
                        phrase_g = gr.Textbox(
                            value="gray basket", label="Phrase",
                            placeholder="찾을 객체 이름",
                        )
                        with gr.Row():
                            btn_g = gr.Button("▶ Run Grounding", variant="primary", scale=3)
                            btn_up_g = gr.UploadButton("📁 이미지 업로드", file_types=["image"], scale=1)
                    with gr.Column():
                        out_img_g  = gr.Image(label="결과 (bbox 오버레이)")
                        out_status = gr.Textbox(label="Status / Caption", lines=2)
                        out_ents   = gr.Textbox(label="감지된 Entity", lines=6)

                btn_g.click(run_grounding,
                            inputs=[img_g, phrase_g, adapter_dd],
                            outputs=[out_img_g, out_status, out_ents])
                btn_up_g.upload(fn=lambda f: np.array(Image.open(f).convert("RGB")),
                                inputs=btn_up_g, outputs=img_g)

            # ── 탭 2: Alias Test ─────────────────────────────────────────────
            with gr.TabItem("Alias Test"):
                gr.Markdown("같은 물체를 다양한 이름으로 — Kosmos-2 인식률 비교")
                with gr.Row():
                    with gr.Column():
                        img_a = gr.Image(interactive=False, label="📷 Live Camera")
                        btn_up_a = gr.UploadButton("📁 이미지 업로드", file_types=["image"])
                        gr.Markdown("**프리셋**")
                        with gr.Row():
                            preset_btns = [gr.Button(label, size="sm") for label in PRESET_ALIASES]
                        alias_txt = gr.Textbox(
                            value=list(PRESET_ALIASES.values())[0],
                            label="Alias 목록 (한 줄 = 1 phrase)", lines=8,
                        )
                        btn_a = gr.Button("▶ Run All", variant="primary")
                    with gr.Column():
                        out_img_a   = gr.Image(label="결과 그리드")
                        out_summary = gr.Textbox(label="Hit / Miss 요약", lines=12)

                btn_up_a.upload(fn=lambda f: np.array(Image.open(f).convert("RGB")),
                                inputs=btn_up_a, outputs=img_a)
                for btn, text in zip(preset_btns, PRESET_ALIASES.values()):
                    btn.click(fn=lambda t=text: t, outputs=alias_txt)
                btn_a.click(run_alias_test,
                            inputs=[img_a, alias_txt, adapter_dd],
                            outputs=[out_img_a, out_summary])

            # ── 탭 3: VLA Inference ──────────────────────────────────────────
            with gr.TabItem("VLA Inference"):
                gr.Markdown(
                    "이미지 → GoalNav API (`:8001/predict`) → 액션 예측\n"
                    "카메라 프레임이 자동으로 표시되며, **▶ Run VLA** 클릭 시 현재 프레임으로 추론합니다."
                )
                with gr.Row():
                    with gr.Column():
                        img_v = gr.Image(interactive=False, label="📷 Live Camera")
                        btn_up_v = gr.UploadButton("📁 이미지 업로드 (대체)", file_types=["image"])
                        instr_dd = gr.Dropdown(
                            choices=GOAL_NAV_PRESETS, value=GOAL_NAV_PRESETS[0],
                            label="Instruction 프리셋", allow_custom_value=True,
                        )
                        instr_txt = gr.Textbox(value=GOAL_NAV_PRESETS[0],
                                               label="Instruction (직접 입력)")
                        instr_dd.change(fn=lambda x: x, inputs=instr_dd, outputs=instr_txt)
                        with gr.Row():
                            btn_v     = gr.Button("▶ Run VLA", variant="primary", scale=3)
                            reset_btn = gr.Button("↺ Reset", scale=1)
                    with gr.Column():
                        out_img_v    = gr.Image(label="결과 (3×3 격자 + bbox)")
                        out_status_v = gr.Textbox(label="Action / Status", lines=5)
                        out_bbox_v   = gr.Textbox(label="Bbox 정보", lines=3)

                btn_up_v.upload(fn=lambda f: np.array(Image.open(f).convert("RGB")),
                                inputs=btn_up_v, outputs=img_v)
                reset_btn.click(reset_api_history,
                                outputs=gr.Textbox(visible=False))
                btn_v.click(run_vla_predict,
                            inputs=[img_v, instr_txt],
                            outputs=[out_img_v, out_status_v, out_bbox_v])

            # ── 탭 4: VLA Alias Test ─────────────────────────────────────────
            with gr.TabItem("VLA Alias Test"):
                gr.Markdown(
                    "여러 instruction phrase → VLA API 각각 → **어떤 말 → 어떤 액션** 비교\n"
                    "카메라 프레임이 자동 표시됩니다."
                )
                with gr.Row():
                    with gr.Column():
                        img_va = gr.Image(interactive=False, label="📷 Live Camera")
                        btn_up_va = gr.UploadButton("📁 이미지 업로드 (대체)", file_types=["image"])
                        gr.Markdown("**프리셋**")
                        with gr.Row():
                            vpreset_btns = [gr.Button(label, size="sm") for label in PRESET_ALIASES]
                        alias_txt_v = gr.Textbox(
                            value=list(PRESET_ALIASES.values())[0],
                            label="Instruction 목록 (한 줄 = 1개)", lines=8,
                        )
                        btn_va = gr.Button("▶ Run All VLA", variant="primary")
                    with gr.Column():
                        out_img_va = gr.Image(label="마지막 Bbox (3×3 격자)")
                        out_sum_va = gr.Textbox(label="Phrase → Action 매핑 + 분포", lines=18)

                btn_up_va.upload(fn=lambda f: np.array(Image.open(f).convert("RGB")),
                                 inputs=btn_up_va, outputs=img_va)
                for btn, text in zip(vpreset_btns, PRESET_ALIASES.values()):
                    btn.click(fn=lambda t=text: t, outputs=alias_txt_v)
                btn_va.click(run_vla_alias,
                             inputs=[img_va, alias_txt_v],
                             outputs=[out_img_va, out_sum_va])

        # ── 공유 타이머: 모든 탭의 카메라 이미지 자동 갱신 ─────────────────────
        timer = gr.Timer(value=1.0, active=ROS_AVAILABLE)
        timer.tick(
            fn=timer_tick,
            outputs=[img_v, img_va, img_g, cam_status_txt],
        )
        # Alias Test 탭은 별도 tick 연결 (Grounding과 공유하면 충돌)
        timer.tick(
            fn=lambda: _last_frame,
            outputs=[img_a],
        )

    return demo


# ─── 진입점 ───────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=7863)
    parser.add_argument("--share", action="store_true")
    parser.add_argument("--preload", action="store_true")
    args = parser.parse_args()

    if args.preload:
        print("[PRE-LOAD] Pure Kosmos-2")
        _ensure_model("Pure Kosmos-2")

    demo = build_ui()
    print(f"[START] http://0.0.0.0:{args.port}  |  ROS={ROS_AVAILABLE}")
    demo.launch(
        server_name="0.0.0.0",
        server_port=args.port,
        share=args.share,
        theme=gr.themes.Soft(),
    )


if __name__ == "__main__":
    main()
