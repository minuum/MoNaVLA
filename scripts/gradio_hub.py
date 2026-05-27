#!/usr/bin/env python3
"""
MoNaVLA 서비스 허브 — 통합 포털
모든 Gradio / FastAPI 서비스의 상태 확인 + 원클릭 접속

Port: 7860

Usage:
  python3 scripts/gradio_hub.py
  python3 scripts/gradio_hub.py --port 7860
"""
import socket
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import gradio as gr


# ─── 서비스 정의 ──────────────────────────────────────────────────────────────

SERVICES = [
    {
        "name":   "Object Recognition Demo",
        "port":   7863,
        "script": "scripts/gradio_grounding_demo.py",
        "cmd":    "python3 scripts/gradio_grounding_demo.py",
        "desc":   "Kosmos-2 그라운딩 — 웹캠/이미지 bbox 테스트 + Alias 비교",
        "group":  "Demo",
    },
    {
        "name":   "Inference Dashboard",
        "port":   7865,
        "script": "scripts/gradio_inference_dashboard.py",
        "cmd":    "python3 scripts/gradio_inference_dashboard.py",
        "desc":   "메인 추론 대시보드 — GoalNav 로봇 제어",
        "group":  "Robot",
    },
    {
        "name":   "Trial Logger",
        "port":   7862,
        "script": "scripts/real_robot_trial_logger.py",
        "cmd":    "python3 scripts/real_robot_trial_logger.py",
        "desc":   "실로봇 trial 기록 — 3-position 평가",
        "group":  "Robot",
    },
    {
        "name":   "Data Collector",
        "port":   8081,
        "script": "scripts/gradio_data_collector.py",
        "cmd":    "python3 scripts/gradio_data_collector.py",
        "desc":   "조이스틱 데이터 수집 — H5 에피소드 기록",
        "group":  "Data",
    },
    {
        "name":   "Session Eval",
        "port":   7861,
        "script": "scripts/gradio_session_eval.py",
        "cmd":    "python3 scripts/gradio_session_eval.py",
        "desc":   "H5 에피소드 품질 평가 — basket 가시성 분석",
        "group":  "Eval",
    },
    {
        "name":   "H5 Analyzer",
        "port":   7866,
        "script": "scripts/gradio_offline_h5_analyzer.py",
        "cmd":    "python3 scripts/gradio_offline_h5_analyzer.py",
        "desc":   "오프라인 H5 분석기 — 프레임 탐색 / 액션 분포",
        "group":  "Eval",
    },
    {
        "name":   "CL Dashboard",
        "port":   7867,
        "script": "scripts/gradio_cl_dashboard.py",
        "cmd":    "python3 scripts/gradio_cl_dashboard.py",
        "desc":   "Closed-Loop 평가 결과 + 실로봇 주행 로그",
        "group":  "Eval",
    },
    {
        "name":   "Monitor",
        "port":   8080,
        "script": "scripts/monitor_dashboard.py",
        "cmd":    "python3 scripts/monitor_dashboard.py",
        "desc":   "시스템 모니터링 대시보드",
        "group":  "System",
    },
    {
        "name":   "GoalNav API",
        "port":   8001,
        "script": "robovlm_nav/serve/proxy_inference_server.py",
        "cmd":    "python3 robovlm_nav/serve/proxy_inference_server.py --port 8001",
        "desc":   "GoalNav FastAPI 백엔드 — bbox grounding + MLP 추론",
        "group":  "System",
        "path":   "/dashboard",
    },
]

GROUP_COLOR = {
    "Demo":   "#1a6b3c",
    "Robot":  "#1a3d6b",
    "Data":   "#5a3d1a",
    "Eval":   "#4a1a6b",
    "System": "#3d3d3d",
}


# ─── 유틸 ─────────────────────────────────────────────────────────────────────

def get_server_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "localhost"


def is_port_up(port: int, timeout: float = 0.5) -> bool:
    try:
        with socket.create_connection(("localhost", port), timeout=timeout):
            return True
    except Exception:
        return False


def get_pid_on_port(port: int) -> str:
    try:
        result = subprocess.run(
            ["ss", "-tlnp", f"sport = :{port}"],
            capture_output=True, text=True, timeout=2,
        )
        for line in result.stdout.splitlines():
            if str(port) in line and "pid=" in line:
                pid = line.split("pid=")[1].split(",")[0]
                return pid
    except Exception:
        pass
    return ""


# ─── HTML 렌더 ────────────────────────────────────────────────────────────────

def render_hub_html(server_ip: str) -> str:
    groups: dict[str, list] = {}
    for svc in SERVICES:
        g = svc["group"]
        groups.setdefault(g, []).append(svc)

    cards_html = ""
    for group, svcs in groups.items():
        color = GROUP_COLOR.get(group, "#333")
        cards_html += f"""
        <div style="margin-bottom:24px">
          <div style="font-size:12px;font-weight:600;color:#888;text-transform:uppercase;
                      letter-spacing:1px;margin-bottom:10px;padding-left:4px">{group}</div>
          <div style="display:flex;flex-wrap:wrap;gap:12px">
        """
        for svc in svcs:
            up = is_port_up(svc["port"])
            pid = get_pid_on_port(svc["port"]) if up else ""
            dot_color = "#2ecc71" if up else "#e74c3c"
            dot_label = f"UP  pid={pid}" if up else "DOWN"
            url = f"http://{server_ip}:{svc['port']}{svc.get('path', '')}"
            link_style = (
                "background:#2a5a3a;color:#2ecc71;cursor:pointer;border:1px solid #2ecc71;"
                if up else
                "background:#3d3d3d;color:#666;cursor:not-allowed;border:1px solid #555;"
            )
            link_attr = f'href="{url}" target="_blank"' if up else ""
            cards_html += f"""
            <div style="width:280px;background:#1e1e1e;border:1px solid #333;border-radius:10px;
                        padding:16px;border-top:3px solid {color}">
              <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px">
                <div style="width:10px;height:10px;border-radius:50%;background:{dot_color};
                            box-shadow:0 0 6px {dot_color}"></div>
                <span style="font-size:11px;color:{dot_color};font-family:monospace">{dot_label}</span>
                <span style="margin-left:auto;font-size:11px;color:#666;font-family:monospace">:{svc['port']}</span>
              </div>
              <div style="font-weight:600;color:#e0e0e0;margin-bottom:6px">{svc['name']}</div>
              <div style="font-size:12px;color:#888;margin-bottom:12px;line-height:1.5">{svc['desc']}</div>
              <a {link_attr} style="display:block;text-align:center;padding:7px 0;border-radius:6px;
                                    text-decoration:none;font-size:13px;font-weight:500;{link_style}">
                {'Open →' if up else 'Offline'}
              </a>
            </div>
            """
        cards_html += "</div></div>"

    up_count = sum(1 for svc in SERVICES if is_port_up(svc["port"]))
    total = len(SERVICES)
    ts = time.strftime("%H:%M:%S")

    return f"""
    <div style="background:#111;color:#e0e0e0;font-family:'Segoe UI',sans-serif;
                padding:24px;border-radius:12px;min-height:400px">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:24px">
        <div>
          <div style="font-size:22px;font-weight:700;color:#fff">MoNaVLA Hub</div>
          <div style="font-size:13px;color:#666;margin-top:4px">{server_ip} &nbsp;·&nbsp;
            <span style="color:#2ecc71">{up_count}</span>/<span style="color:#888">{total}</span> running
            &nbsp;·&nbsp; updated {ts}
          </div>
        </div>
      </div>
      {cards_html}
    </div>
    """


# ─── 서비스 시작/종료 ─────────────────────────────────────────────────────────

def start_service(svc: dict) -> str:
    if is_port_up(svc["port"]):
        return f"already running on :{svc['port']}"
    log_name = svc["script"].replace("/", "_").replace(".py", "")
    log_path = ROOT / "logs" / f"{log_name}.log"
    cmd = f"nohup {svc['cmd']} > {log_path} 2>&1 &"
    subprocess.Popen(
        cmd, shell=True, cwd=str(ROOT),
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    for _ in range(20):
        time.sleep(1)
        if is_port_up(svc["port"]):
            return f"started on :{svc['port']}"
    return f"timeout — check {log_path}"


def stop_service(port: int) -> str:
    pid = get_pid_on_port(port)
    if not pid:
        return "not running"
    try:
        subprocess.run(["kill", pid], check=True)
        return f"killed pid={pid}"
    except Exception as e:
        return f"error: {e}"


# ─── Gradio UI ────────────────────────────────────────────────────────────────

def build_hub(server_ip: str) -> gr.Blocks:
    svc_names = [f"{s['name']} (:{s['port']})" for s in SERVICES]

    with gr.Blocks(title="MoNaVLA Hub") as demo:
        gr.Markdown("## MoNaVLA Hub")

        hub_html = gr.HTML(value=render_hub_html(server_ip))
        refresh_btn = gr.Button("Refresh Status", variant="secondary", size="sm")

        with gr.Accordion("Service Control", open=False):
            with gr.Row():
                svc_dd  = gr.Dropdown(choices=svc_names, label="서비스 선택", scale=3)
                start_b = gr.Button("Start", variant="primary", scale=1)
                stop_b  = gr.Button("Stop",  variant="stop",    scale=1)
            ctrl_out = gr.Textbox(label="결과", lines=2)

        def do_refresh():
            return render_hub_html(server_ip)

        def do_start(name):
            idx = svc_names.index(name)
            return start_service(SERVICES[idx])

        def do_stop(name):
            idx = svc_names.index(name)
            return stop_service(SERVICES[idx]["port"])

        refresh_btn.click(do_refresh, outputs=hub_html)
        start_b.click(do_start, inputs=svc_dd, outputs=ctrl_out).then(
            do_refresh, outputs=hub_html
        )
        stop_b.click(do_stop, inputs=svc_dd, outputs=ctrl_out).then(
            do_refresh, outputs=hub_html
        )

    return demo


def main():
    import argparse
    parser = argparse.ArgumentParser(description="MoNaVLA 서비스 허브")
    parser.add_argument("--port", type=int, default=7860)
    parser.add_argument("--share", action="store_true")
    args = parser.parse_args()

    server_ip = get_server_ip()
    print(f"[HUB] Server IP: {server_ip}")
    print(f"[HUB] http://0.0.0.0:{args.port}")

    demo = build_hub(server_ip)
    demo.launch(
        server_name="0.0.0.0",
        server_port=args.port,
        share=args.share,
        theme=gr.themes.Soft(),
    )


if __name__ == "__main__":
    main()
