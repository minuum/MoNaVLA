#!/usr/bin/env python3
"""
Real Robot Trial Logger — Exp49 실로봇 평가 기록기
포트 7862 독립 Gradio 서버

사용법:
  python3 scripts/real_robot_trial_logger.py
  python3 scripts/real_robot_trial_logger.py --port 7862

각 시도(trial)를 기록하고 오프라인 CL 결과와 실시간 비교한다.
결과: docs/v5/eval/real_robot_exp49_YYYYMMDD_HHMMSS.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import gradio as gr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

EVAL_OUT_DIR = ROOT / "docs" / "v5" / "eval"
EVAL_OUT_DIR.mkdir(parents=True, exist_ok=True)

ROLLOUT_METRICS = ROOT / "docs" / "v5" / "closed_loop_eval" / "rollout_metrics.json"

PATH_TYPES = [
    "center_straight",
    "center_left",
    "center_right",
    "left_straight",
    "left_left",
    "left_right",
    "right_straight",
    "right_left",
    "right_right",
]

FAILURE_REASONS = [
    "(해당 없음)",
    "FORWARD_BIAS — 항상 직진",
    "WRONG_DIR — 반대 방향",
    "EARLY_STOP — 중간에 멈춤",
    "DRIFT — 누적 편차 이탈",
    "GROUNDING_FAIL — bbox 미검출",
    "COLLISION — 충돌/걸림",
    "OTHER",
]

# ── 오프라인 CL 베이스라인 로드 ───────────────────────────────────────

def load_offline_baseline() -> dict[str, dict]:
    """per_path exp49 결과를 path_type → {n, success_rate, mean_fpe}로 변환."""
    if not ROLLOUT_METRICS.exists():
        return {}
    try:
        data = json.loads(ROLLOUT_METRICS.read_text())
        per_path = data.get("per_path", {}).get("exp49", {})
        result = {}
        for pt, episodes in per_path.items():
            n = len(episodes)
            n_ok = sum(1 for e in episodes if e.get("success"))
            fpes = [e["fpe"] for e in episodes if "fpe" in e]
            result[pt] = {
                "n": n,
                "success_rate": n_ok / n if n else 0.0,
                "mean_fpe": sum(fpes) / len(fpes) if fpes else 0.0,
            }
        return result
    except Exception:
        return {}


OFFLINE = load_offline_baseline()

# ── 상태 관리 ─────────────────────────────────────────────────────────

def empty_state() -> dict:
    return {
        "trials": [],
        "save_path": str(EVAL_OUT_DIR / f"real_robot_exp49_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"),
    }


# ── 핵심 로직 ─────────────────────────────────────────────────────────

def log_trial(state: dict, path_type: str, success: str, failure_reason: str, notes: str):
    """시도 1건 기록 후 요약 업데이트."""
    is_success = (success == "✅ 성공")
    trial = {
        "trial_id": len(state["trials"]) + 1,
        "timestamp": datetime.now().isoformat(),
        "path_type": path_type,
        "success": is_success,
        "failure_reason": None if is_success else failure_reason,
        "notes": notes.strip(),
    }
    state["trials"].append(trial)

    # 자동 저장
    save_path = Path(state["save_path"])
    payload = {
        "model": "exp49",
        "date": datetime.now().strftime("%Y-%m-%d"),
        "server": "soda@100.85.118.58:8001",
        "total_trials": len(state["trials"]),
        "trials": state["trials"],
    }
    save_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False))

    summary_md = _build_summary_md(state["trials"])
    table_data = _build_table(state["trials"])
    log_text = f"✅ #{trial['trial_id']} {path_type} {'성공' if is_success else '실패'} — 저장됨"
    return state, summary_md, table_data, log_text, ""  # notes 초기화


def undo_last(state: dict):
    """마지막 시도 취소."""
    if not state["trials"]:
        return state, _build_summary_md([]), _build_table([]), "⚠️ 취소할 기록 없음"
    removed = state["trials"].pop()
    summary_md = _build_summary_md(state["trials"])
    table_data = _build_table(state["trials"])
    return state, summary_md, table_data, f"↩️ #{removed['trial_id']} {removed['path_type']} 취소됨"


def export_json(state: dict):
    path = state.get("save_path", "")
    if not state["trials"]:
        return "⚠️ 기록된 시도 없음"
    return f"📁 저장됨: {path}"


# ── 요약 렌더링 ───────────────────────────────────────────────────────

def _build_summary_md(trials: list[dict]) -> str:
    if not trials:
        return "아직 기록된 시도 없음."
    n = len(trials)
    n_ok = sum(1 for t in trials if t["success"])
    rate = n_ok / n
    color = "🟢" if rate >= 0.8 else ("🟡" if rate >= 0.6 else "🔴")
    offline_rate = OFFLINE and sum(v["success_rate"] for v in OFFLINE.values()) / max(len(OFFLINE), 1)
    diff = rate - offline_rate if offline_rate else 0.0
    diff_str = f"{diff:+.1%}" if offline_rate else "N/A"

    lines = [
        f"## {color} 전체: {n_ok}/{n} = **{rate:.1%}**",
        f"오프라인 CL 기준 {offline_rate:.1%} → 차이 {diff_str}",
        "",
        "### 실패 원인",
    ]
    fail_counts: dict[str, int] = {}
    for t in trials:
        if not t["success"]:
            r = t.get("failure_reason") or "OTHER"
            fail_counts[r] = fail_counts.get(r, 0) + 1
    if fail_counts:
        for r, c in sorted(fail_counts.items(), key=lambda x: -x[1]):
            lines.append(f"- {r}: {c}회")
    else:
        lines.append("- 실패 없음 🎉")
    return "\n".join(lines)


def _build_table(trials: list[dict]) -> list[list]:
    """path_type × {real_n, real_ok, real_rate, offline_rate} 테이블."""
    counts: dict[str, list[bool]] = {pt: [] for pt in PATH_TYPES}
    for t in trials:
        pt = t["path_type"]
        if pt in counts:
            counts[pt].append(t["success"])

    rows = []
    for pt in PATH_TYPES:
        successes = counts[pt]
        n = len(successes)
        n_ok = sum(successes)
        real_str = f"{n_ok}/{n} ({n_ok/n:.0%})" if n else "—"
        off = OFFLINE.get(pt, {})
        off_n = off.get("n", 0)
        off_ok = round(off.get("success_rate", 0) * off_n)
        off_str = f"{off_ok}/{off_n} ({off.get('success_rate', 0):.0%})" if off_n else "—"
        gap = ""
        if n and off_n:
            diff = (n_ok / n) - off.get("success_rate", 0)
            gap = f"{diff:+.0%}"
        rows.append([pt, real_str, off_str, gap])
    return rows


# ── Gradio UI ─────────────────────────────────────────────────────────

def build_ui() -> gr.Blocks:
    with gr.Blocks(title="Exp49 Real Robot Trial Logger", theme=gr.themes.Soft()) as demo:
        state = gr.State(empty_state())

        gr.Markdown("# 🤖 Exp49 실로봇 평가 기록기\n포트 7862 | 시도마다 기록 → 오프라인 CL 비교")

        with gr.Row():
            # ── 왼쪽: 입력 패널 ──────────────────────────────────────
            with gr.Column(scale=1):
                gr.Markdown("## 시도 기록")
                path_type = gr.Dropdown(
                    choices=PATH_TYPES,
                    value="center_straight",
                    label="Path Type",
                )
                success = gr.Radio(
                    choices=["✅ 성공", "❌ 실패"],
                    value="✅ 성공",
                    label="결과",
                )
                failure_reason = gr.Dropdown(
                    choices=FAILURE_REASONS,
                    value=FAILURE_REASONS[0],
                    label="실패 원인 (실패 시)",
                    visible=False,
                )
                notes = gr.Textbox(label="메모 (선택)", placeholder="특이사항 입력...", lines=2)

                with gr.Row():
                    btn_log = gr.Button("📝 기록", variant="primary", scale=3)
                    btn_undo = gr.Button("↩ 취소", variant="secondary", scale=1)

                status_box = gr.Textbox(label="상태", interactive=False, lines=1)

                gr.Markdown("---")
                gr.Markdown("### 사전 체크")
                gr.Markdown(
                    "```bash\n"
                    "# 서버 상태 확인\n"
                    "curl http://localhost:8001/health\n"
                    "# model_name=exp49 확인\n"
                    "```"
                )

            # ── 오른쪽: 요약 패널 ─────────────────────────────────────
            with gr.Column(scale=2):
                gr.Markdown("## 실시간 비교")
                summary_md = gr.Markdown("아직 기록된 시도 없음.")

                comparison_table = gr.Dataframe(
                    headers=["Path Type", "실로봇", "오프라인 CL", "차이"],
                    value=_build_table([]),
                    interactive=False,
                    wrap=True,
                )

                btn_export = gr.Button("💾 JSON 경로 확인", variant="secondary")
                export_out = gr.Textbox(label="저장 위치", interactive=False)

        # ── 이벤트 ────────────────────────────────────────────────────

        # 실패 선택 시 failure_reason 표시
        success.change(
            fn=lambda s: gr.update(visible=(s == "❌ 실패")),
            inputs=[success],
            outputs=[failure_reason],
        )

        btn_log.click(
            fn=log_trial,
            inputs=[state, path_type, success, failure_reason, notes],
            outputs=[state, summary_md, comparison_table, status_box, notes],
        )

        btn_undo.click(
            fn=undo_last,
            inputs=[state],
            outputs=[state, summary_md, comparison_table, status_box],
        )

        btn_export.click(
            fn=export_json,
            inputs=[state],
            outputs=[export_out],
        )

    return demo


# ── 진입점 ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=7862)
    parser.add_argument("--share", action="store_true")
    args = parser.parse_args()

    print(f"📊 Trial Logger starting on http://{args.host}:{args.port}")
    print(f"📂 Results → {EVAL_OUT_DIR}/real_robot_exp49_*.json")
    if OFFLINE:
        print(f"📈 Offline CL loaded: {len(OFFLINE)} path types")
    else:
        print("⚠️  Offline CL not found — comparison unavailable")

    build_ui().launch(server_name=args.host, server_port=args.port, share=args.share)
