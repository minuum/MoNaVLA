#!/usr/bin/env python3
"""
Evaluate policy degradation on a shared V5 episode split.

Goal:
  Separate failures into three levels on the same episodes:
  1. frame-level action accuracy (teacher-forced per-frame)
  2. short-horizon rollout drift (prefix K)
  3. full-episode closed-loop rollout

Initial target:
  Compare Exp11 vs Exp21 on the shared bbox_dataset.json episode split.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List

import h5py
import numpy as np
from transformers import AutoProcessor

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from scripts.sim.rollout_core import CLASS_NAMES, build_trajectory, compute_metrics, continuous_to_class
from scripts.sim.evaluate_closed_loop_v5 import (
    DATA_DIR,
    PATH_TYPES,
    STEP1_DIR,
    eval_exp11_episode,
    load_exp11_model,
    load_text_embedding_map,
)

OUT_DIR = ROOT / "docs" / "v5" / "rollout_degradation"
OUT_DIR.mkdir(parents=True, exist_ok=True)


MODEL_SPECS = {
    "exp11": {
        "label": "Exp11",
        "config": ROOT / "configs/mobile_vla_v5_exp11_google_robot_8cls.json",
        "ckpt": ROOT / "runs/v5_nav/kosmos/mobile_vla_v5_exp11/2026-04-16/v5-exp11-google-robot-8cls/epoch_epoch=epoch=14-val_loss=val_loss=1.010.ckpt",
        "uses_text_embedding": False,
    },
    "exp17": {
        "label": "Exp17",
        "config": ROOT / "configs/mobile_vla_v5_exp17_step3_balanced.json",
        "exp_dir": ROOT / "runs/v5_nav/kosmos/mobile_vla_v5_exp17",
        "uses_text_embedding": False,
    },
    "exp18": {
        "label": "Exp18",
        "config": ROOT / "configs/mobile_vla_v5_exp18_vla_finetuned.json",
        "ckpt": ROOT / "runs/v5_nav/kosmos/mobile_vla_v5_exp18/2026-04-21/v5-exp18-vla-text-fusion/epoch_epoch=epoch=14-val_loss=val_loss=1.325.ckpt",
        "uses_text_embedding": True,
    },
    "exp21": {
        "label": "Exp21",
        "config": ROOT / "configs/mobile_vla_v5_exp21_pure_hf_head_only.json",
        "ckpt": Path("/tmp/monavla_resume_runs/kosmos/mobile_vla_v5_exp21/2026-04-21/v5-exp21-pure-hf-head-only/epoch_epoch=epoch=14-val_loss=val_loss=2.009.ckpt"),
        "uses_text_embedding": False,
    },
    "exp24": {
        "label": "Exp24",
        "config": ROOT / "configs/mobile_vla_v5_exp24_pure_hf_head_only_objective.json",
        "exp_dir": Path("/tmp/monavla_resume_runs/kosmos/mobile_vla_v5_exp24"),
        "uses_text_embedding": False,
    },
    "exp25": {
        "label": "Exp25",
        "config": ROOT / "configs/mobile_vla_v5_exp25_step3_balanced_objective.json",
        "exp_dir": ROOT / "runs/v5_nav/kosmos/mobile_vla_v5_exp25",
        "uses_text_embedding": False,
    },
    "exp26": {
        "label": "Exp26",
        "config": ROOT / "configs/mobile_vla_v5_exp26_step3_objective_direct224.json",
        "exp_dir": ROOT / "runs/v5_nav/kosmos/mobile_vla_v5_exp26",
        "uses_text_embedding": False,
    },
    "exp27": {
        "label": "Exp27",
        "config": ROOT / "configs/mobile_vla_v5_exp27_step3_objective_letterbox224.json",
        "exp_dir": ROOT / "runs/v5_nav/kosmos/mobile_vla_v5_exp27",
        "uses_text_embedding": False,
    },
}


def resolve_ckpt_path(spec: Dict) -> Path:
    ckpt = spec.get("ckpt")
    if ckpt is not None:
        ckpt_path = Path(ckpt)
        return ckpt_path

    exp_dir = spec.get("exp_dir")
    if exp_dir is None:
        raise FileNotFoundError(f"No ckpt or exp_dir configured for {spec.get('label', 'unknown')}")

    exp_root = Path(exp_dir)
    if not exp_root.exists():
        raise FileNotFoundError(f"Experiment directory missing: {exp_root}")

    candidates = sorted(exp_root.glob("**/epoch*.ckpt"))
    if not candidates:
        candidates = sorted(exp_root.glob("**/last*.ckpt"))
    if not candidates:
        raise FileNotFoundError(f"No checkpoint found under {exp_root}")

    def score(path: Path):
        name = path.name
        is_epoch = 1 if name.startswith("epoch") else 0
        return (is_epoch, path.stat().st_mtime)

    return max(candidates, key=score)


def get_test_episode_paths(seed: int = 42) -> List[Path]:
    bbox_ds = json.loads((STEP1_DIR / "bbox_dataset.json").read_text())
    rng = np.random.default_rng(seed)
    by_path = defaultdict(list)
    for i, ep in enumerate(bbox_ds):
        by_path[ep["path_type"]].append(i)

    test_idx = []
    for _, idxs in by_path.items():
        idxs = idxs[:]
        rng.shuffle(idxs)
        k = max(1, int(len(idxs) * 0.2))
        test_idx.extend(idxs[:k])

    test_ep_stems = {bbox_ds[i]["episode"] for i in test_idx}
    paths = []
    for pt in PATH_TYPES:
        all_eps = sorted(DATA_DIR.glob(f"episode_*target_{pt}_path*.h5"))
        matched = [ep for ep in all_eps if ep.stem in test_ep_stems]
        if not matched and all_eps:
            matched = all_eps[-1:]
        paths.extend(matched)
    return paths


def load_expert_classes(ep_path: Path) -> List[int]:
    with h5py.File(ep_path, "r") as f:
        expert_actions = f["actions"][:]
    return [continuous_to_class(*a[:3]) for a in expert_actions]


def summarize_prefix(pred_cls: List[int], expert_cls: List[int], dt: float, success_fpe: float, horizon: int) -> Dict[str, float]:
    n = min(horizon, len(pred_cls), len(expert_cls))
    pred_prefix = pred_cls[:n]
    expert_prefix = expert_cls[:n]
    frame_acc = float(np.mean([int(p == g) for p, g in zip(pred_prefix, expert_prefix)])) if n else 0.0
    pred_traj = build_trajectory(pred_prefix, dt)
    expert_traj = build_trajectory(expert_prefix, dt)
    m = compute_metrics(expert_traj, pred_traj, success_fpe)
    return {
        "n_frames": n,
        "frame_acc": frame_acc,
        "fpe": m["fpe"],
        "tld": m["tld"],
        "mean_lateral_dev": m["mean_lateral_dev"],
        "success": m["success"],
    }


def evaluate_model(model_key: str, episode_paths: List[Path], horizons: List[int], dt: float, success_fpe: float) -> Dict:
    spec = MODEL_SPECS[model_key]
    ckpt_path = resolve_ckpt_path(spec)
    if not ckpt_path.exists():
        raise FileNotFoundError(f"{model_key} ckpt missing: {ckpt_path}")

    processor = AutoProcessor.from_pretrained(str(ROOT / ".vlms" / "kosmos-2-patch14-224"))
    text_embedding_map = load_text_embedding_map() if spec["uses_text_embedding"] else None

    model_wrapper = load_exp11_model(str(spec["config"]), str(ckpt_path))
    model_backbone = model_wrapper.model
    model_backbone.eval()

    per_episode = []
    prefix_buckets = {f"k={k}": [] for k in horizons}
    full_metrics = []
    frame_accs = []
    transition_counts = np.zeros((len(CLASS_NAMES), len(CLASS_NAMES)), dtype=int)
    gt_transition_counts = np.zeros((len(CLASS_NAMES), len(CLASS_NAMES)), dtype=int)
    by_path_full = defaultdict(list)

    for ep_path in episode_paths:
        pred_classes, _expert_actions = eval_exp11_episode(
            ep_path,
            model_backbone,
            processor,
            window_size=8,
            text_embedding_map=text_embedding_map,
        )
        expert_classes = load_expert_classes(ep_path)
        n = min(len(pred_classes), len(expert_classes))
        pred_classes = pred_classes[:n]
        expert_classes = expert_classes[:n]
        path_type = ep_path.stem.split("_target_")[1].split("_path")[0] if "_target_" in ep_path.stem else "unknown"

        ep_frame_acc = float(np.mean([int(p == g) for p, g in zip(pred_classes, expert_classes)])) if n else 0.0
        frame_accs.append(ep_frame_acc)

        for a, b in zip(pred_classes[:-1], pred_classes[1:]):
            if 0 <= a < len(CLASS_NAMES) and 0 <= b < len(CLASS_NAMES):
                transition_counts[a, b] += 1
        for a, b in zip(expert_classes[:-1], expert_classes[1:]):
            if 0 <= a < len(CLASS_NAMES) and 0 <= b < len(CLASS_NAMES):
                gt_transition_counts[a, b] += 1

        prefix_metrics = {}
        for horizon in horizons:
            p = summarize_prefix(pred_classes, expert_classes, dt, success_fpe, horizon)
            prefix_metrics[f"k={horizon}"] = p
            prefix_buckets[f"k={horizon}"].append(p)

        full_pred = build_trajectory(pred_classes, dt)
        full_expert = build_trajectory(expert_classes, dt)
        full = compute_metrics(full_expert, full_pred, success_fpe)
        full["frame_acc"] = ep_frame_acc
        full_metrics.append(full)
        by_path_full[path_type].append(full)

        per_episode.append({
            "episode": ep_path.stem,
            "path_type": path_type,
            "n_frames": n,
            "frame_acc": ep_frame_acc,
            "pred_classes": pred_classes,
            "expert_classes": expert_classes,
            "pred_class_names": [CLASS_NAMES[c] for c in pred_classes],
            "expert_class_names": [CLASS_NAMES[c] for c in expert_classes],
            "prefix": prefix_metrics,
            "full": full,
        })

    summary = {
        "n_episodes": len(per_episode),
        "frame_acc": float(np.mean(frame_accs)) if frame_accs else 0.0,
        "prefix": {},
        "full": {
            "success_rate": float(np.mean([m["success"] for m in full_metrics])) if full_metrics else 0.0,
            "mean_fpe": float(np.mean([m["fpe"] for m in full_metrics])) if full_metrics else 0.0,
            "mean_tld": float(np.mean([m["tld"] for m in full_metrics])) if full_metrics else 0.0,
            "mean_lateral_dev": float(np.mean([m["mean_lateral_dev"] for m in full_metrics])) if full_metrics else 0.0,
        },
    }
    for key, bucket in prefix_buckets.items():
        summary["prefix"][key] = {
            "frame_acc": float(np.mean([m["frame_acc"] for m in bucket])) if bucket else 0.0,
            "success_rate": float(np.mean([m["success"] for m in bucket])) if bucket else 0.0,
            "mean_fpe": float(np.mean([m["fpe"] for m in bucket])) if bucket else 0.0,
            "mean_tld": float(np.mean([m["tld"] for m in bucket])) if bucket else 0.0,
            "mean_lateral_dev": float(np.mean([m["mean_lateral_dev"] for m in bucket])) if bucket else 0.0,
        }

    summary["by_path_full"] = {
        path_type: {
            "n_episodes": len(bucket),
            "frame_acc": float(np.mean([m["frame_acc"] for m in bucket])) if bucket else 0.0,
            "success_rate": float(np.mean([m["success"] for m in bucket])) if bucket else 0.0,
            "mean_fpe": float(np.mean([m["fpe"] for m in bucket])) if bucket else 0.0,
            "mean_tld": float(np.mean([m["tld"] for m in bucket])) if bucket else 0.0,
            "mean_lateral_dev": float(np.mean([m["mean_lateral_dev"] for m in bucket])) if bucket else 0.0,
        }
        for path_type, bucket in by_path_full.items()
    }
    summary["pred_transition_top"] = summarize_transitions(transition_counts)
    summary["gt_transition_top"] = summarize_transitions(gt_transition_counts)

    return {
        "model": model_key,
        "label": spec["label"],
        "ckpt": str(ckpt_path),
        "config": str(spec["config"]),
        "summary": summary,
        "episodes": per_episode,
    }


def summarize_transitions(counts: np.ndarray, top_k: int = 8) -> List[Dict[str, object]]:
    entries = []
    for i in range(counts.shape[0]):
        for j in range(counts.shape[1]):
            c = int(counts[i, j])
            if c > 0:
                entries.append({
                    "src": i,
                    "dst": j,
                    "src_name": CLASS_NAMES[i],
                    "dst_name": CLASS_NAMES[j],
                    "count": c,
                })
    entries.sort(key=lambda x: x["count"], reverse=True)
    return entries[:top_k]


def build_html(payload: Dict, horizons: List[int]) -> str:
    model_cards = []
    for key in payload["models"]:
        m = payload["models"][key]
        s = m["summary"]
        rows = []
        rows.append(
            f"<tr><th>Frame Acc</th><td>{s['frame_acc']*100:.1f}%</td><td>-</td><td>-</td><td>-</td></tr>"
        )
        for h in horizons:
            p = s["prefix"][f"k={h}"]
            rows.append(
                f"<tr><th>Prefix @{h}</th><td>{p['frame_acc']*100:.1f}%</td><td>{p['success_rate']*100:.1f}%</td><td>{p['mean_fpe']:.3f}</td><td>{p['mean_tld']:.3f}</td></tr>"
            )
        f = s["full"]
        rows.append(
            f"<tr><th>Full</th><td>{s['frame_acc']*100:.1f}%</td><td>{f['success_rate']*100:.1f}%</td><td>{f['mean_fpe']:.3f}</td><td>{f['mean_tld']:.3f}</td></tr>"
        )
        path_rows = []
        for path_type, ps in sorted(s.get("by_path_full", {}).items()):
            path_rows.append(
                f"<tr><td>{path_type}</td><td>{ps['frame_acc']*100:.1f}%</td><td>{ps['success_rate']*100:.1f}%</td><td>{ps['mean_fpe']:.3f}</td><td>{ps['mean_tld']:.3f}</td></tr>"
            )
        pred_top = "".join(
            f"<li><code>{x['src_name']} -&gt; {x['dst_name']}</code>: {x['count']}</li>"
            for x in s.get("pred_transition_top", [])
        )
        card = f"""
        <section class="card">
          <h2>{m['label']}</h2>
          <div class="meta"><code>{m['model']}</code></div>
          <table>
            <tr><th>Metric</th><th>Frame Acc</th><th>Success</th><th>FPE</th><th>TLD</th></tr>
            {''.join(rows)}
          </table>
          <h3>Path-wise Full</h3>
          <table>
            <tr><th>Path</th><th>Frame Acc</th><th>Success</th><th>FPE</th><th>TLD</th></tr>
            {''.join(path_rows)}
          </table>
          <h3>Top Predicted Transitions</h3>
          <ul>{pred_top}</ul>
        </section>
        """
        model_cards.append(card)

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>V5 Rollout Degradation</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 32px; color: #111827; background: #f8fafc; }}
    h1 {{ margin-bottom: 8px; }}
    .sub {{ color: #4b5563; margin-bottom: 20px; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr)); gap: 16px; }}
    .card {{ background: white; border: 1px solid #e5e7eb; border-radius: 12px; padding: 16px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
    th, td {{ border-bottom: 1px solid #e5e7eb; padding: 8px; text-align: right; }}
    th:first-child, td:first-child {{ text-align: left; }}
    code {{ background: #f3f4f6; padding: 2px 6px; border-radius: 6px; }}
  </style>
</head>
<body>
  <h1>V5 Policy Degradation</h1>
  <div class="sub">Shared episode split. Compare frame-level accuracy, short prefix rollout, and full closed-loop drift.</div>
  <div class="grid">
    {''.join(model_cards)}
  </div>
</body>
</html>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default="exp11,exp17,exp18,exp21,exp24,exp25,exp26,exp27", help="Comma-separated model keys")
    ap.add_argument("--horizons", default="5,10,15", help="Comma-separated prefix lengths")
    ap.add_argument("--dt", type=float, default=0.1)
    ap.add_argument("--success_fpe", type=float, default=0.5)
    args = ap.parse_args()

    model_keys = [m.strip() for m in args.models.split(",") if m.strip()]
    horizons = [int(x.strip()) for x in args.horizons.split(",") if x.strip()]
    episode_paths = get_test_episode_paths(seed=42)

    payload = {
        "episode_split": [p.stem for p in episode_paths],
        "horizons": horizons,
        "models": {},
    }

    for key in model_keys:
        if key not in MODEL_SPECS:
            raise KeyError(f"Unknown model key: {key}")
        print(f"\n=== {key} ===")
        payload["models"][key] = evaluate_model(key, episode_paths, horizons, args.dt, args.success_fpe)
        s = payload["models"][key]["summary"]
        print(f"  frame_acc={s['frame_acc']*100:.1f}%")
        for h in horizons:
            p = s["prefix"][f"k={h}"]
            print(f"  prefix@{h}: success={p['success_rate']*100:.1f}% fpe={p['mean_fpe']:.3f} tld={p['mean_tld']:.3f}")
        f = s["full"]
        print(f"  full: success={f['success_rate']*100:.1f}% fpe={f['mean_fpe']:.3f} tld={f['mean_tld']:.3f}")

    out_json = OUT_DIR / "degradation_summary.json"
    out_html = OUT_DIR / "index.html"
    out_json.write_text(json.dumps(payload, indent=2))
    out_html.write_text(build_html(payload, horizons))
    print(f"\nWrote: {out_json}")
    print(f"Wrote: {out_html}")


if __name__ == "__main__":
    main()
