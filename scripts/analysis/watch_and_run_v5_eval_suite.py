#!/usr/bin/env python3
"""
Watch a training log until completion, then run the reserved V5 eval suite.

Reserved tests per model:
  1. short-term summary (closed-loop / non-straight prefix@5 / macro per-path frame acc)
  2. rollout degradation breakdown
  3. PM / DM offline evaluation

This is meant for "queue the tests now and let them start when training ends".
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_WAIT_PATTERNS = [
    "`Trainer.fit` stopped",
    "Trainer.fit stopped",
]

MODEL_CONFIGS = {
    "exp11": "configs/mobile_vla_v5_exp11_google_robot_8cls.json",
    "exp17": "configs/mobile_vla_v5_exp17_step3_balanced.json",
    "exp18": "configs/mobile_vla_v5_exp18_vla_finetuned.json",
    "exp21": "configs/mobile_vla_v5_exp21_pure_hf_head_only.json",
    "exp24": "configs/mobile_vla_v5_exp24_pure_hf_head_only_objective.json",
    "exp25": "configs/mobile_vla_v5_exp25_step3_balanced_objective.json",
    "exp26": "configs/mobile_vla_v5_exp26_step3_objective_direct224.json",
    "exp27": "configs/mobile_vla_v5_exp27_step3_objective_letterbox224.json",
    "exp28": "configs/mobile_vla_v5_exp28_step3_balanced_objective_grounding_turnboost.json",
}

MODEL_CKPT_GLOBS = {
    "exp11": [ROOT / "runs/v5_nav/kosmos/mobile_vla_v5_exp11"],
    "exp17": [ROOT / "runs/v5_nav/kosmos/mobile_vla_v5_exp17"],
    "exp18": [ROOT / "runs/v5_nav/kosmos/mobile_vla_v5_exp18"],
    "exp21": [Path("/tmp/monavla_resume_runs/kosmos/mobile_vla_v5_exp21")],
    "exp24": [Path("/tmp/monavla_resume_runs/kosmos/mobile_vla_v5_exp24")],
    "exp25": [ROOT / "runs/v5_nav/kosmos/mobile_vla_v5_exp25"],
    "exp26": [ROOT / "runs/v5_nav/kosmos/mobile_vla_v5_exp26"],
    "exp27": [ROOT / "runs/v5_nav/kosmos/mobile_vla_v5_exp27"],
    "exp28": [ROOT / "runs/v5_nav/kosmos/mobile_vla_v5_exp28"],
}


def parse_val_loss_from_ckpt_name(path: Path) -> float | None:
    match = re.search(r"val_loss=val_loss=([0-9]+(?:\.[0-9]+)?)", path.name)
    if match:
        return float(match.group(1))
    return None


def wait_for_training_completion(log_path: Path, patterns: list[str], poll_sec: float) -> None:
    print(f"[watch] waiting for training completion in {log_path}")
    last_size = -1
    while True:
        if log_path.exists():
            text = log_path.read_text(errors="ignore")
            if any(pattern in text for pattern in patterns):
                print("[watch] completion pattern found")
                return
            size = log_path.stat().st_size
            if size != last_size:
                last_size = size
        time.sleep(poll_sec)


def resolve_ckpt(model_key: str) -> Path:
    roots = MODEL_CKPT_GLOBS[model_key]
    candidates = []
    for root in roots:
        if not root.exists():
            continue
        candidates.extend(root.glob("**/epoch*.ckpt"))
        candidates.extend(root.glob("**/last*.ckpt"))
    if not candidates:
        raise FileNotFoundError(f"No checkpoint found for {model_key}")

    def score(path: Path):
        val_loss = parse_val_loss_from_ckpt_name(path)
        is_epoch = path.name.startswith("epoch")
        if val_loss is not None:
            return (2, -val_loss, path.stat().st_mtime)
        if is_epoch:
            return (1, 0.0, path.stat().st_mtime)
        return (0, 0.0, path.stat().st_mtime)

    return max(candidates, key=score)


def run_cmd(cmd: list[str], label: str) -> None:
    print(f"\n[run] {label}")
    print("[cmd] " + " ".join(cmd))
    proc = subprocess.run(cmd, cwd=ROOT)
    if proc.returncode != 0:
        raise RuntimeError(f"{label} failed with exit code {proc.returncode}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--wait_log",
        default="logs/exp24_pure_hf_head_only_objective_tmp.log",
        help="Training log to watch before starting queued evals",
    )
    parser.add_argument(
        "--models",
        default="exp28,exp27,exp26,exp25,exp24,exp21,exp18,exp17,exp11",
        help="Comma-separated reserved model keys",
    )
    parser.add_argument("--poll_sec", type=float, default=20.0)
    parser.add_argument("--skip_wait", action="store_true")
    args = parser.parse_args()

    wait_log = ROOT / args.wait_log
    model_keys = [m.strip() for m in args.models.split(",") if m.strip()]

    if not args.skip_wait:
        wait_for_training_completion(wait_log, DEFAULT_WAIT_PATTERNS, args.poll_sec)

    run_cmd(
        [
            sys.executable,
            "scripts/analysis/summarize_v5_shortterm_eval.py",
            "--models",
            ",".join(model_keys),
        ],
        "short-term summary",
    )

    run_cmd(
        [
            sys.executable,
            "scripts/analysis/evaluate_rollout_degradation_v5.py",
            "--models",
            ",".join(model_keys),
        ],
        "rollout degradation",
    )

    pm_dir = ROOT / "docs" / "v5" / "pm_eval"
    pm_dir.mkdir(parents=True, exist_ok=True)
    pm_results = []
    for model_key in model_keys:
        if model_key not in MODEL_CONFIGS:
            print(f"[skip] PM eval unsupported model key: {model_key}")
            continue
        ckpt = resolve_ckpt(model_key)
        config = MODEL_CONFIGS[model_key]
        run_cmd(
            [
                sys.executable,
                "scripts/test_v5_pm_dm.py",
                "--ckpt",
                str(ckpt),
                "--config",
                config,
                "--num_classes",
                "8",
                "--window_size",
                "8",
                "--train_split",
                "0.8",
            ],
            f"PM/DM eval {model_key}",
        )
        pm_results.append(
            {
                "model": model_key,
                "ckpt": str(ckpt),
                "config": config,
            }
        )

    suite_manifest = {
        "wait_log": str(wait_log),
        "models": model_keys,
        "pm_eval_runs": pm_results,
    }
    manifest_path = pm_dir / "suite_manifest.json"
    manifest_path.write_text(json.dumps(suite_manifest, indent=2))
    print(f"\n[done] wrote {manifest_path}")


if __name__ == "__main__":
    main()
