#!/usr/bin/env python3
"""
Real Robot Trial Logger — Exp49 실로봇 평가 기록기
포트 7862 독립 Gradio 서버

Exp49 핵심: 물체 위치(cx0)가 goal → 9개 path type이 아닌
바스켓이 LEFT / CENTER / RIGHT 어디 있는지만 알면 된다.

오프라인 CL 집계 (baseline):
  left  : 9/9  = 100.0%   (left_left + center_left + right_left)
  center: 12/12 = 100.0%  (center_straight + left_straight + right_straight)
  right : 8/9  =  88.9%   (center_right + left_right + right_right)

사용법:
  python3 scripts/real_robot_trial_logger.py
  python3 scripts/real_robot_trial_logger.py --port 7862
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

import gradio as gr

ROOT = Path(__file__).resolve().parents[1]
EVAL_OUT_DIR = ROOT / "docs" / "v5" / "eval"
EVAL_OUT_DIR.mkdir(parents=True, exist_ok=True)

# 오프라인 CL 베이스라인 (hard-coded, 변경 시 rollout_metrics.json에서 재집계)
OFFLINE_BASELINE = {
    "left":   {"n_ok": 9,  "n": 9,  "success_rate": 1.000, "mean_fpe": 0.06},
    "center": {"n_ok": 12, "n": 12, "success_rate": 1.000, "mean_fpe": 0.03},
    "right":  {"n_ok": 8,  "n": 9,  "success_rate": 0.889, "mean_fpe": 0.16},
}

POSITIONS = ["left", "center", "right"]

FAILURE_REASONS = [
    "(해당 없음)",
    "FORWARD_BIAS — 항상 직진",
    "WRONG_DIR — 반대 방향으로 이동",
    "EARLY_STOP — 중간에 멈춤",
    "DRIFT — 누적 편차로 이탈",
    "GROUNDING_FAIL — bbox 미검출 의심",
    "COLLISION — 충돌/걸림",
    "OTHER",
]

# ── 상태 ──────────────────────────────────────────────────────────────

def empty_state() -> dict:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return {
        "trials": [],
        "save_path": str(EVAL_OUT_DIR / f"real_robot_exp49_{ts}.json"),
    }

# ── 로직 ──────────────────────────────────────────────────────────────

def log_trial(state: dict, position: str, success_radio: str,
              failure_reason: str, notes: str):
    is_ok = success_radio == "✅ 성공"
    trial = {
        "trial_id": len(state["trials"]) + 1,
        "timestamp": datetime.now().isoformat(),
        "basket_position": position,
        "success": is_ok,
        "failure_reason": None if is_ok else failure_reason,
        "notes": notes.strip(),
    }
    state["trials"].append(trial)
    _autosave(state)

    status = f"✅ #{trial['trial_id']} [{position}] {'성공' if is_ok else '실패'} — 저장됨"
    return state, _summary_md(state["trials"]), _table(state["trials"]), status, ""


def undo_last(state: dict):
    if not state["trials"]:
        return state, _summary_md([]), _table([]), "⚠️ 취소할 기록 없음"
    t = state["trials"].pop()
    _autosave(state)
    return state, _summary_md(state["trials"]), _table(state["trials"]), \
           f"↩️ #{t['trial_id']} [{t['basket_position']}] 취소됨"


def show_save_path(state: dict) -> str:
    if not state["trials"]:
        return "⚠️ 기록된 시도 없음"
    return f"📁 {state['save_path']}"


def _autosave(state: dict):
    payload = {
        "model": "exp49",
        "date": datetime.now().strftime("%Y-%m-%d"),
        "server": "soda@100.85.118.58:8001",
        "total_trials": len(state["trials"]),
        "trials": state["trials"],
    }
    Path(state["save_path"]).write_text(
        json.dumps(payload, indent=2, ensure_ascii=False)
    )


# ── 렌더링 ────────────────────────────────────────────────────────────

def _summary_md(trials: list[dict]) -> str:
    if not trials:
        return "아직 기록된 시도 없음."
    n = len(trials)
    n_ok = sum(1 for t in trials if t["success"])
    rate = n_ok / n
    icon = "🟢" if rate >= 0.8 else ("🟡" if rate >= 0.6 else "🔴")

    # 오프라인 가중 평균 (n 기준)
    tot_off_ok = sum(v["n_ok"] for v in OFFLINE_BASELINE.values())
    tot_off_n  = sum(v["n"]   for v in OFFLINE_BASELINE.values())
    off_rate = tot_off_ok / tot_off_n  # 29/30 = 96.7%
    diff = rate - off_rate

    lines = [
        f"## {icon} 전체 {n_ok}/{n} = **{rate:.1%}**",
        f"오프라인 CL {off_rate:.1%} 대비 **{diff:+.1%}**",
        "",
    ]

    # 실패 원인 집계
    fails = [t for t in trials if not t["success"]]
    if fails:
        lines.append("### 실패 원인")
        counts: dict[str, int] = {}
        for t in fails:
            r = t.get("failure_reason") or "OTHER"
            counts[r] = counts.get(r, 0) + 1
        for r, c in sorted(counts.items(), key=lambda x: -x[1]):
            lines.append(f"- {r}: {c}회")
    else:
        lines.append("### 실패 없음 🎉")

    return "\n".join(lines)


def _table(trials: list[dict]) -> list[list]:
    """position × {실로봇, 오프라인, 차이} 비교표."""
    counts: dict[str, list[bool]] = {p: [] for p in POSITIONS}
    for t in trials:
        pos = t["basket_position"]
        if pos in counts:
            counts[pos].append(t["success"])

    rows = []
    for pos in POSITIONS:
        successes = counts[pos]
        n = len(successes)
        n_ok = sum(successes)
        real_str = f"{n_ok}/{n} ({n_ok/n:.0%})" if n else "—"

        off = OFFLINE_BASELINE[pos]
        off_str = f"{off['n_ok']}/{off['n']} ({off['success_rate']:.0%})"

        gap = ""
        if n:
            diff = (n_ok / n) - off["success_rate"]
            gap = f"{diff:+.0%}"

        rows.append([pos, real_str, off_str, gap])
    return rows


# ── UI ────────────────────────────────────────────────────────────────

def build_ui() -> gr.Blocks:
    with gr.Blocks(title="Exp49 Real Robot Logger", theme=gr.themes.Soft()) as demo:
        state = gr.State(empty_state())

        gr.Markdown(
            "# 🤖 Exp49 실로봇 평가\n"
            "바스켓 위치(LEFT / CENTER / RIGHT)별로 기록 → 오프라인 CL과 비교"
        )

        with gr.Row():
            # ── 입력 패널 ──────────────────────────────────────────────
            with gr.Column(scale=1):
                gr.Markdown("## 시도 기록")

                position = gr.Radio(
                    choices=POSITIONS,
                    value="center",
                    label="바스켓 위치 (첫 프레임 기준)",
                )
                success_radio = gr.Radio(
                    choices=["✅ 성공", "❌ 실패"],
                    value="✅ 성공",
                    label="결과",
                )
                failure_reason = gr.Dropdown(
                    choices=FAILURE_REASONS,
                    value=FAILURE_REASONS[0],
                    label="실패 원인",
                    visible=False,
                )
                notes = gr.Textbox(
                    label="메모 (선택)",
                    placeholder="예: 조명 어두움, 첫 회전 느림...",
                    lines=2,
                )

                with gr.Row():
                    btn_log  = gr.Button("📝 기록", variant="primary", scale=3)
                    btn_undo = gr.Button("↩ 취소", variant="secondary", scale=1)

                status_box = gr.Textbox(label="상태", interactive=False, lines=1)

                gr.Markdown("---")
                gr.Markdown(
                    "**서버 확인**\n"
                    "```bash\ncurl localhost:8001/health\n```\n"
                    "model_name=exp49 확인 후 시작"
                )

            # ── 요약 패널 ──────────────────────────────────────────────
            with gr.Column(scale=2):
                gr.Markdown("## 실시간 비교")

                summary_md = gr.Markdown("아직 기록된 시도 없음.")

                comparison = gr.Dataframe(
                    headers=["바스켓 위치", "실로봇", "오프라인 CL", "차이"],
                    value=_table([]),
                    interactive=False,
                    wrap=True,
                )

                gr.Markdown(
                    "오프라인 CL 기준 (Exp49, 30 에피소드)\n"
                    "| | left | center | right | **전체** |\n"
                    "|---|---|---|---|---|\n"
                    "| 성공률 | 100% | 100% | 88.9% | **96.7%** |\n"
                    "| FPE | 0.06m | 0.03m | 0.16m | 0.08m |"
                )

                btn_path = gr.Button("💾 저장 경로 확인", variant="secondary")
                path_out = gr.Textbox(label="저장 위치", interactive=False)

        # ── 이벤트 ────────────────────────────────────────────────────
        success_radio.change(
            fn=lambda s: gr.update(visible=(s == "❌ 실패")),
            inputs=[success_radio],
            outputs=[failure_reason],
        )

        btn_log.click(
            fn=log_trial,
            inputs=[state, position, success_radio, failure_reason, notes],
            outputs=[state, summary_md, comparison, status_box, notes],
        )

        btn_undo.click(
            fn=undo_last,
            inputs=[state],
            outputs=[state, summary_md, comparison, status_box],
        )

        btn_path.click(
            fn=show_save_path,
            inputs=[state],
            outputs=[path_out],
        )

    return demo


# ── 진입점 ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=7862)
    ap.add_argument("--share", action="store_true")
    args = ap.parse_args()

    print(f"📊 Trial Logger → http://{args.host}:{args.port}")
    print(f"📂 저장 → {EVAL_OUT_DIR}/real_robot_exp49_*.json")
    build_ui().launch(server_name=args.host, server_port=args.port, share=args.share)
