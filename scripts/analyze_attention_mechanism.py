#!/usr/bin/env python3
"""
Analyze attention collapse mechanism.

- Layer depth: at which Kosmos LM layer does text attention die?
- Per-head: how many of the 32 heads attend to text, before vs after training?
- Compares Pure Kosmos-2 (foundation) vs Exp11/Exp13 (trained).
"""
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "docs" / "v5" / "attention_analysis"
EXP_FILE = OUT_DIR / "summary.json"
PURE_FILE = OUT_DIR / "pure_kosmos.json"
OUT_JSON = OUT_DIR / "mechanism.json"
OUT_HTML = OUT_DIR / "mechanism.html"

# Threshold: a head is considered to "attend to text" if sum(text attention) > threshold
TEXT_HEAD_THRESHOLD = 0.05
IMG_HEAD_THRESHOLD = 0.05


def summarize_model(model_results, model_name):
    per_instr = {}
    for instr, data in model_results.items():
        per_layer = data.get("per_layer", [])
        if not per_layer:
            continue
        layers = []
        for l in per_layer:
            img_heads = np.array(l["image_per_head"], dtype=np.float32)
            text_heads = np.array(l["text_per_head"], dtype=np.float32)
            layers.append({
                "layer": l["layer"],
                "image_ratio": l["image_ratio_mean"],
                "text_ratio": l["text_ratio_mean"],
                "text_heads_alive": int((text_heads > TEXT_HEAD_THRESHOLD).sum()),
                "image_heads_alive": int((img_heads > IMG_HEAD_THRESHOLD).sum()),
                "num_heads": int(len(text_heads)),
                "text_head_max": float(text_heads.max() if len(text_heads) else 0.0),
                "image_head_max": float(img_heads.max() if len(img_heads) else 0.0),
            })
        per_instr[instr] = layers
    return {"model": model_name, "per_instruction": per_instr}


def aggregate_over_instructions(summary):
    out = {}
    for model_name, model_data in summary.items():
        pi = model_data.get("per_instruction", {})
        if not pi:
            continue
        num_layers = len(next(iter(pi.values())))
        agg = []
        for li in range(num_layers):
            img_ratios = [pi[k][li]["image_ratio"] for k in pi]
            text_ratios = [pi[k][li]["text_ratio"] for k in pi]
            text_alive = [pi[k][li]["text_heads_alive"] for k in pi]
            image_alive = [pi[k][li]["image_heads_alive"] for k in pi]
            agg.append({
                "layer": li,
                "image_ratio_avg": float(np.mean(img_ratios)),
                "text_ratio_avg": float(np.mean(text_ratios)),
                "text_heads_alive_avg": float(np.mean(text_alive)),
                "image_heads_alive_avg": float(np.mean(image_alive)),
                "num_heads": int(pi[list(pi.keys())[0]][li]["num_heads"]),
            })
        out[model_name] = agg
    return out


def pct(v):
    return f"{v * 100:.1f}%"


def build_html(agg):
    num_layers = len(next(iter(agg.values())))
    models = list(agg.keys())

    rows = []
    for li in range(num_layers):
        cells = [f"<td>{li}</td>"]
        for m in models:
            layer = agg[m][li]
            cells.append(
                f"<td>{pct(layer['image_ratio_avg'])}</td>"
                f"<td>{pct(layer['text_ratio_avg'])}</td>"
                f"<td>{layer['text_heads_alive_avg']:.1f}</td>"
            )
        rows.append(f"<tr>{''.join(cells)}</tr>")

    header_cells = ["<th>Layer</th>"]
    for m in models:
        header_cells.append(f"<th colspan=3>{m}</th>")
    sub_cells = ["<th></th>"]
    for m in models:
        sub_cells.extend(["<th>Img%</th>", "<th>Text%</th>", "<th>text-heads alive / 32</th>"])

    html = f"""<!DOCTYPE html>
<html lang=\"ko\">
<head>
<meta charset=\"UTF-8\">
<title>Attention Collapse Mechanism (Per Layer)</title>
<style>
 body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; background:#0f172a; color:#e2e8f0; margin:0; padding:24px; }}
 h1, h2 {{ color:#fff; }}
 .note {{ background:#172554; border-left:4px solid #60a5fa; padding:14px 18px; border-radius:6px; margin-bottom:18px; line-height:1.6; }}
 table {{ width:100%; border-collapse:collapse; background:#1e293b; border-radius:8px; overflow:hidden; margin-bottom:20px; }}
 th, td {{ padding:8px 12px; border-bottom:1px solid #334155; text-align:center; font-size:0.9rem; }}
 th {{ background:#0b1220; }}
 .back {{ color:#60a5fa; text-decoration:none; display:inline-block; margin-bottom:14px; }}
</style>
</head>
<body>
  <a class=\"back\" href=\"../../index.html\">← Back to MoNaVLA</a>
  <h1>Attention Collapse Mechanism</h1>
  <div class=\"note\">
    각 Kosmos LM layer에서 <b>마지막 real token의 attention</b>을 측정.
    Pure Kosmos-2(학습 전)와 Exp11/Exp13(학습 후)의 layer별 image/text ratio, 그리고 &lsquo;text-head alive&rsquo;(text region 합 &gt; {TEXT_HEAD_THRESHOLD}) 개수를 비교합니다.
    <br>→ <b>학습 후 text-heads alive가 layer 어디에서 0이 되는가</b>가 collapse mechanism의 layer-level signature.
  </div>

  <h2>Per Layer Summary</h2>
  <table>
    <thead>
      <tr>{''.join(header_cells)}</tr>
      <tr>{''.join(sub_cells)}</tr>
    </thead>
    <tbody>
      {''.join(rows)}
    </tbody>
  </table>
</body>
</html>"""
    OUT_HTML.write_text(html)


def main():
    if not EXP_FILE.exists():
        print(f"Missing {EXP_FILE}")
        return
    if not PURE_FILE.exists():
        print(f"Missing {PURE_FILE}")
        return
    exp_data = json.loads(EXP_FILE.read_text())
    pure_data = json.loads(PURE_FILE.read_text())

    exp11 = summarize_model(exp_data.get("exp11", {}), "exp11")
    exp13 = summarize_model(exp_data.get("exp13", {}), "exp13")
    pure = summarize_model(pure_data, "pure_kosmos")

    summary = {"pure_kosmos": pure, "exp11": exp11, "exp13": exp13}
    agg = aggregate_over_instructions(summary)

    OUT_JSON.write_text(json.dumps({"raw": summary, "aggregated": agg}, indent=2))
    print(f"Wrote: {OUT_JSON}")
    build_html(agg)
    print(f"Wrote: {OUT_HTML}")

    # Print layer curve summary to stdout
    print("\n  layer | pure(img/text, heads) | exp11(img/text, heads) | exp13(img/text, heads)")
    for li in range(len(agg[list(agg.keys())[0]])):
        parts = [f"  {li:5d}"]
        for m in agg:
            layer = agg[m][li]
            parts.append(
                f"{pct(layer['image_ratio_avg']):>6}/{pct(layer['text_ratio_avg']):>6}  {layer['text_heads_alive_avg']:.1f}"
            )
        print(" | ".join(parts))


if __name__ == "__main__":
    main()
