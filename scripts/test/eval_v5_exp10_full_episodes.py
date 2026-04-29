#!/usr/bin/env python3
"""
V5 Exp10 - 9개 에피소드 타입 전 프레임 추론 + 인터랙티브 HTML 뷰어 생성

각 path type에서 대표 에피소드 1개씩(첫 번째 파일), 전 프레임 bbox grounding 추론.
초록 박스 = 탐지 성공, 빨간 테두리 = 실패.
결과를 docs/v5/exp10/full_episode_viewer/index.html 에 저장.
"""
import os
import sys
import re
import glob
import json
import base64
import torch
import numpy as np
import cv2
from tqdm import tqdm
from PIL import Image
import h5py

os.environ["PYTHONNOUSERSITE"] = "1"
os.environ["USE_FLASH_ATTENTION"] = "0"
sys.path.insert(1, "/home/billy/25-1kp/MoNaVLA")
sys.path.insert(0, "/home/billy/25-1kp/MoNaVLA/third_party/RoboVLMs")

from robovlms.model.backbone.base_backbone import load_config
from robovlms.train.mobile_vla_trainer import MobileVLATrainer
from transformers import AutoProcessor

# ── 경로 설정 ──────────────────────────────────────────────────────────────────
CONFIG_PATH  = "configs/mobile_vla_v5_exp10_bbox.json"
CKPT_PATH    = "runs/v5_nav/kosmos/mobile_vla_v5_bbox/2026-04-15/v5-exp10-track2-bbox/epoch_epoch=epoch=07-val_loss=val_loss=0.012.ckpt"
DATASET_DIR  = "ROS_action/mobile_vla_dataset_v5"
OUTPUT_DIR   = "docs/v5/exp10/full_episode_viewer"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── 9개 에피소드 타입 ───────────────────────────────────────────────────────────
EPISODE_TYPES = [
    "target_center_left_path",
    "target_center_right_path",
    "target_center_straight_path",
    "target_left_left_path",
    "target_left_right_path",
    "target_left_straight_path",
    "target_right_left_path",
    "target_right_right_path",
    "target_right_straight_path",
]

# 표시 이미지 크기 (원본 720×1280 → 480×270)
DISP_W, DISP_H = 480, 270


# ── BBox 파싱 / 그리기 ─────────────────────────────────────────────────────────
def parse_bbox(text):
    """patch_index 토큰 추출. 여러 포맷 지원:
    1) <box_2d><patch_index_XXXX><patch_index_YYYY></box_2d>
    2) <patch_index_XXXX><patch_index_YYYY>  (box_2d wrapper 없음)
    3) <patch_index_XXXX> 하나만 있을 때 (p1==p2로 처리)
    """
    # 방법 1: box_2d wrapper
    m = re.search(
        r"<box_2d>\s*<patch_index_(\d+)>\s*<patch_index_(\d+)>\s*</box_2d>",
        text
    )
    if m:
        return int(m.group(1)), int(m.group(2))

    # 방법 2/3: patch_index 토큰을 순서대로 모두 수집
    indices = [int(x) for x in re.findall(r"<patch_index_(\d+)>", text)]
    if len(indices) >= 2:
        return indices[-2], indices[-1]
    if len(indices) == 1:
        return indices[0], indices[0]   # 단일 → 점 표시
    return None, None


def patch_to_pixel(idx, w, h):
    """Kosmos-2 32×32 패치 인덱스 → 픽셀 좌표."""
    col = idx % 32
    row = idx // 32
    return int(col / 32 * w), int(row / 32 * h)


def draw_bbox(img_rgb, p1, p2):
    """BBox 오버레이.
    - p1!=p2: 초록 사각형 (정상 bbox)
    - p1==p2: 노란 점 (단일 패치 인덱스만 예측)
    - None: 빨간 테두리 (탐지 실패)
    """
    out = img_rgb.copy()
    h, w = out.shape[:2]
    if p1 is not None:
        x1, y1 = patch_to_pixel(p1, w, h)
        x2, y2 = patch_to_pixel(p2, w, h)
        if p1 == p2:
            # 단일 점: 노란 원
            cx, cy = x1 + w // 64, y1 + h // 64
            cv2.circle(out, (cx, cy), 10, (255, 220, 0), -1)
            cv2.circle(out, (cx, cy), 10, (200, 160, 0), 2)
        else:
            x1, x2 = min(x1, x2), max(x1, x2) + max(1, w // 32)
            y1, y2 = min(y1, y2), max(y1, y2) + max(1, h // 32)
            cv2.rectangle(out, (x1, y1), (x2, y2), (0, 230, 80), 2)
            cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
            cv2.drawMarker(out, (cx, cy), (0, 230, 80),
                           cv2.MARKER_CROSS, 18, 2)
    else:
        # 탐지 실패: 빨간 테두리
        cv2.rectangle(out, (2, 2), (w - 2, h - 2), (220, 50, 50), 2)
    return out


def to_b64(img_rgb, quality=75):
    bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
    _, buf = cv2.imencode('.jpg', bgr, [cv2.IMWRITE_JPEG_QUALITY, quality])
    return base64.b64encode(buf).decode()


def action_label(lx, ly, az):
    parts = []
    if abs(lx) > 0.05:
        parts.append(f"{'FWD' if lx > 0 else 'BACK'} {abs(lx):.2f}")
    if abs(ly) > 0.05:
        parts.append(f"{'L-STRAFE' if ly > 0 else 'R-STRAFE'} {abs(ly):.2f}")
    if abs(az) > 0.03:
        parts.append(f"{'ROT_L' if az > 0 else 'ROT_R'} {abs(az):.2f}")
    return ', '.join(parts) if parts else 'STOP'


# ── 모델 로드 ──────────────────────────────────────────────────────────────────
def load_model():
    print("=== 모델 로딩 중 ===")
    configs = load_config(CONFIG_PATH)
    trainer = MobileVLATrainer(configs)

    ckpt = torch.load(CKPT_PATH, map_location="cpu")
    state_dict = ckpt.get("state_dict", ckpt)
    if any(k.startswith("model.") for k in state_dict):
        state_dict = {
            (k[6:] if k.startswith("model.") else k): v
            for k, v in state_dict.items()
        }
    trainer.model.load_state_dict(state_dict, strict=False)
    model = trainer.model.to("cuda:0").eval()

    processor = AutoProcessor.from_pretrained("microsoft/kosmos-2-patch14-224")
    print(f"  ckpt: {os.path.basename(CKPT_PATH)}")
    return model, processor


# ── 에피소드 추론 ──────────────────────────────────────────────────────────────
def infer_episode(ep_path, model, processor):
    with h5py.File(ep_path) as f:
        images_raw = f['observations/images'][:]   # (N, H, W, 3)
        actions_raw = f['actions'][:]               # (N, 3)  [lx, ly, az]
        instr_raw = f['language_instruction'][0]
        instr = instr_raw.decode() if isinstance(instr_raw, bytes) else instr_raw

    n_frames = len(images_raw)
    frames_data = []

    for i in tqdm(range(n_frames), desc=f"  {os.path.basename(ep_path)[-50:]}", leave=False):
        img_orig = images_raw[i]                               # H×W×3 RGB
        img_disp = cv2.resize(img_orig, (DISP_W, DISP_H))    # 480×270

        image_pil = Image.fromarray(img_orig)
        inputs = processor(
            text=instr,
            images=image_pil,
            return_tensors="pt"
        ).to("cuda:0")

        with torch.no_grad():
            outputs = model.model.generate(
                pixel_values=inputs['pixel_values'],
                input_ids=inputs['input_ids'],
                attention_mask=inputs['attention_mask'],
                image_embeds_position_mask=inputs.get('image_embeds_position_mask'),
                max_new_tokens=48,
                use_cache=True,
            )

        pred_text = processor.tokenizer.decode(outputs[0], skip_special_tokens=False)
        p1, p2 = parse_bbox(pred_text)

        # BBox 중심 x (0=왼쪽, 1=오른쪽)
        bbox_cx = None
        if p1 is not None:
            cx_col = ((p1 % 32) + (p2 % 32)) / 2.0
            bbox_cx = round(cx_col / 32.0, 4)

        # 이미지 (오버레이 / 원본)
        img_overlay = draw_bbox(img_disp, p1, p2)
        b64_overlay = to_b64(img_overlay)
        b64_orig    = to_b64(img_disp)

        act = actions_raw[i]
        lx, ly, az = float(act[0]), float(act[1]), float(act[2])

        # 모델 출력 텍스트 — 마지막 150자만 (HTML 크기 절약)
        short_text = pred_text.strip()[-150:]

        frames_data.append({
            'frame':        i,
            'b64':          b64_overlay,
            'b64_orig':     b64_orig,
            'p1':           p1,
            'p2':           p2,
            'bbox_cx':      bbox_cx,
            'pred_text':    short_text,
            'lx':           lx,
            'ly':           ly,
            'az':           az,
            'action_label': action_label(lx, ly, az),
        })

    hit_rate = sum(1 for fd in frames_data if fd['p1'] is not None) / n_frames * 100
    return frames_data, instr, hit_rate


# ── HTML 생성 ──────────────────────────────────────────────────────────────────
def _hit_color(rate):
    if rate >= 70: return '#4ade80'
    if rate >= 40: return '#fbbf24'
    return '#f87171'


def generate_html(all_eps):
    # JS 데이터 직렬화 (p1/p2 None → null)
    ep_js = json.dumps([
        {
            'type':         ep['type'],
            'name':         ep['name'],
            'instruction':  ep['instruction'],
            'bbox_hit_rate': ep['bbox_hit_rate'],
            'frames':       ep['frames'],
        }
        for ep in all_eps
    ], ensure_ascii=False)

    tab_buttons = '\n'.join(
        f'<button class="tab-btn" id="tab-{i}" onclick="switchEp({i})">'
        f'<span class="type-lbl">{ep["type"].replace("_", " ")}</span>'
        f'<span class="hit-badge" style="color:{_hit_color(ep["bbox_hit_rate"])}">'
        f'BBox {ep["bbox_hit_rate"]:.0f}%</span>'
        f'</button>'
        for i, ep in enumerate(all_eps)
    )

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>V5 Exp10 — Full Episode Viewer</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:#0f172a;color:#e2e8f0;font-family:'Segoe UI',system-ui,sans-serif;font-size:14px}}
header{{background:#1e293b;border-bottom:1px solid #334155;padding:14px 22px}}
header h1{{font-size:1.25rem;color:#f8fafc;font-weight:700}}
header p{{font-size:0.75rem;color:#64748b;margin-top:3px}}
.tabs{{display:flex;flex-wrap:wrap;gap:6px;padding:14px 22px;background:#0a1120;border-bottom:1px solid #1e293b}}
.tab-btn{{background:#1e293b;border:1px solid #334155;color:#94a3b8;padding:7px 12px;border-radius:8px;
          cursor:pointer;font-size:0.7rem;display:flex;flex-direction:column;gap:2px;transition:all .15s;text-align:left}}
.tab-btn:hover{{border-color:#4f6ef7;color:#e2e8f0}}
.tab-btn.active{{background:#1d4ed8;border-color:#3b82f6;color:#fff}}
.type-lbl{{font-weight:600;font-size:0.72rem}}
.hit-badge{{font-size:0.65rem}}
.main{{padding:20px 22px;max-width:1380px;margin:0 auto}}
.ep-panel{{display:none}}.ep-panel.active{{display:block}}
.ep-header{{margin-bottom:14px}}
.ep-header h2{{font-size:0.95rem;color:#fbbf24;margin-bottom:4px}}
.ep-header .instr{{font-size:0.75rem;color:#64748b;font-style:italic}}
.ep-header .ep-name{{font-size:0.65rem;color:#334155;margin-top:2px}}
.stat-row{{display:flex;gap:10px;margin-bottom:16px;flex-wrap:wrap}}
.stat-card{{background:#1e293b;border:1px solid #334155;border-radius:8px;padding:10px 16px;flex:1;min-width:100px}}
.stat-num{{font-size:1.5rem;font-weight:700;color:#f8fafc}}
.stat-lbl{{font-size:0.65rem;color:#64748b;margin-top:1px}}
.viewer-layout{{display:grid;grid-template-columns:1fr 300px;gap:18px}}
@media(max-width:860px){{.viewer-layout{{grid-template-columns:1fr}}}}
.viewer-img{{width:100%;border-radius:10px;border:2px solid #334155;display:block;background:#0a1120}}
.slider-wrap{{margin-top:10px}}
input[type=range]{{width:100%;-webkit-appearance:none;height:4px;border-radius:2px;
                    background:#334155;outline:none;cursor:pointer}}
input[type=range]::-webkit-slider-thumb{{-webkit-appearance:none;width:16px;height:16px;
  border-radius:50%;background:#3b82f6;cursor:pointer;border:2px solid #1d4ed8}}
.fcounter{{text-align:center;font-size:0.72rem;color:#64748b;margin-top:5px}}
.ctrl-btns{{display:flex;gap:8px;margin-top:10px;justify-content:center;flex-wrap:wrap}}
.btn{{background:#1e293b;border:1px solid #334155;color:#e2e8f0;padding:6px 14px;
      border-radius:6px;cursor:pointer;font-size:0.75rem;transition:background .15s}}
.btn:hover{{background:#334155}}.btn.play-btn{{background:#1d4ed8;border-color:#3b82f6}}
.thumb-strip{{display:flex;flex-wrap:wrap;gap:4px;margin-top:12px}}
.td{{width:22px;height:22px;border-radius:4px;cursor:pointer;transition:transform .1s;flex-shrink:0}}
.td:hover{{transform:scale(1.3);z-index:10;position:relative}}
.td.active-dot{{outline:2px solid #fff;transform:scale(1.15)}}
.info-panel{{background:#1e293b;border:1px solid #334155;border-radius:10px;padding:14px;
             font-size:0.78rem;overflow-y:auto;max-height:600px}}
.ir{{margin-bottom:10px;padding-bottom:10px;border-bottom:1px solid #334155}}
.ir:last-child{{border-bottom:none;margin-bottom:0;padding-bottom:0}}
.ilbl{{color:#64748b;font-size:0.65rem;text-transform:uppercase;letter-spacing:.05em;margin-bottom:3px}}
.ival{{color:#f8fafc;word-break:break-all;line-height:1.4}}
.bbox-ok{{color:#4ade80}}.bbox-fail{{color:#f87171}}
.act-val{{color:#38bdf8;font-weight:700}}
.raw-text{{font-size:0.62rem;color:#94a3b8;word-break:break-all;font-family:monospace;line-height:1.3}}
</style>
</head>
<body>
<header>
  <h1>V5 Exp10 — BBox Grounding · Full Episode Viewer</h1>
  <p>9개 에피소드 타입 × 전 프레임 추론 &nbsp;|&nbsp; ckpt: epoch=07, val_loss=0.012 &nbsp;|&nbsp; 🟩 탐지 성공 &nbsp; 🟥 실패</p>
</header>
<div class="tabs">{tab_buttons}</div>
<div class="main" id="main-content"></div>

<script>
const DATA = {ep_js};
let curEp = 0;
let curFrame = {{}};
let playItvs = {{}};
let showOverlay = true;

function switchEp(idx) {{
  curEp = idx;
  document.querySelectorAll('.tab-btn').forEach((b,i) => b.classList.toggle('active', i===idx));
  document.querySelectorAll('.ep-panel').forEach((p,i) => p.classList.toggle('active', i===idx));
  if (curFrame[idx] == null) curFrame[idx] = 0;
  renderFrame(idx, curFrame[idx]);
}}

function renderFrame(epIdx, fi) {{
  const ep = DATA[epIdx];
  if (!ep || fi < 0 || fi >= ep.frames.length) return;
  curFrame[epIdx] = fi;
  const fr = ep.frames[fi];

  const img = document.getElementById('img-'+epIdx);
  img.src = 'data:image/jpeg;base64,' + (showOverlay ? fr.b64 : fr.b64_orig);

  document.getElementById('slider-'+epIdx).value = fi;
  document.getElementById('fcnt-'+epIdx).textContent =
    'Frame ' + (fi+1) + ' / ' + ep.frames.length;

  const bboxOk = fr.p1 !== null;
  const bboxStr = bboxOk
    ? 'p1=' + fr.p1 + ' → p2=' + fr.p2
    : '탐지 실패';
  let cxStr = '—';
  if (fr.bbox_cx !== null) {{
    const pct = (fr.bbox_cx * 100).toFixed(1);
    const dir = fr.bbox_cx < 0.43 ? '← LEFT' : fr.bbox_cx > 0.57 ? 'RIGHT →' : '✓ CENTER';
    cxStr = pct + '% (' + dir + ')';
  }}

  document.getElementById('info-'+epIdx).innerHTML =
    '<div class="ir"><div class="ilbl">Frame</div>' +
    '<div class="ival">' + fi + ' / ' + (ep.frames.length-1) + '</div></div>' +
    '<div class="ir"><div class="ilbl">BBox 예측</div>' +
    '<div class="ival ' + (bboxOk?'bbox-ok':'bbox-fail') + '">' + bboxStr + '</div></div>' +
    '<div class="ir"><div class="ilbl">BBox 중심 x</div>' +
    '<div class="ival">' + cxStr + '</div></div>' +
    '<div class="ir"><div class="ilbl">전문가 액션 [lx, ly, az]</div>' +
    '<div class="ival act-val">[' + fr.lx.toFixed(3) + ', ' + fr.ly.toFixed(3) + ', ' + fr.az.toFixed(3) + ']</div>' +
    '<div class="ival" style="font-size:0.7rem;color:#94a3b8;margin-top:2px">' + fr.action_label + '</div></div>' +
    '<div class="ir"><div class="ilbl">모델 출력 텍스트</div>' +
    '<div class="raw-text">' + fr.pred_text.replace(/</g,'&lt;').replace(/>/g,'&gt;') + '</div></div>';

  // dot strip
  document.querySelectorAll('#thumbs-'+epIdx+' .td').forEach((d,i) => {{
    d.classList.toggle('active-dot', i===fi);
  }});
}}

function prevFrame(epIdx) {{
  renderFrame(epIdx, Math.max(0, (curFrame[epIdx]||0) - 1));
}}
function nextFrame(epIdx) {{
  const n = DATA[epIdx].frames.length;
  renderFrame(epIdx, Math.min(n-1, (curFrame[epIdx]||0) + 1));
}}
function togglePlay(epIdx) {{
  if (playItvs[epIdx]) {{
    clearInterval(playItvs[epIdx]);
    delete playItvs[epIdx];
    document.getElementById('playbtn-'+epIdx).textContent = '▶ Play';
  }} else {{
    const n = DATA[epIdx].frames.length;
    playItvs[epIdx] = setInterval(() => {{
      renderFrame(epIdx, ((curFrame[epIdx]||0) + 1) % n);
    }}, 300);
    document.getElementById('playbtn-'+epIdx).textContent = '⏸ Pause';
  }}
}}
function toggleOverlay(epIdx) {{
  showOverlay = !showOverlay;
  document.getElementById('ovbtn-'+epIdx).textContent =
    showOverlay ? '🔲 Hide BBox' : '🔳 Show BBox';
  renderFrame(epIdx, curFrame[epIdx]||0);
}}

document.addEventListener('DOMContentLoaded', () => {{
  const container = document.getElementById('main-content');

  DATA.forEach((ep, epIdx) => {{
    const nFrames = ep.frames.length;
    const nHit = ep.frames.filter(f => f.p1 !== null).length;
    const hitPct = ep.bbox_hit_rate.toFixed(1);
    const hitColor = parseFloat(hitPct) >= 70 ? '#4ade80'
                   : parseFloat(hitPct) >= 40 ? '#fbbf24' : '#f87171';

    const dots = ep.frames.map((fr, fi) => {{
      const col = fr.p1 !== null ? '#22c55e' : '#ef4444';
      return '<div class="td" style="background:' + col + '" ' +
             'onclick="renderFrame(' + epIdx + ',' + fi + ')" ' +
             'title="Frame ' + fi + ': ' + (fr.p1!==null?'BBox OK':'No BBox') + '"></div>';
    }}).join('');

    const panel = document.createElement('div');
    panel.className = 'ep-panel';
    panel.id = 'ep-' + epIdx;
    panel.innerHTML =
      '<div class="ep-header">' +
        '<h2>' + ep.type.replace(/_/g,' ') + '</h2>' +
        '<div class="instr">' + ep.instruction + '</div>' +
        '<div class="ep-name">' + ep.name + '</div>' +
      '</div>' +
      '<div class="stat-row">' +
        '<div class="stat-card"><div class="stat-num">' + nFrames + '</div><div class="stat-lbl">전체 프레임</div></div>' +
        '<div class="stat-card"><div class="stat-num" style="color:' + hitColor + '">' + hitPct + '%</div><div class="stat-lbl">BBox 탐지율</div></div>' +
        '<div class="stat-card"><div class="stat-num">' + nHit + '</div><div class="stat-lbl">탐지 성공</div></div>' +
        '<div class="stat-card"><div class="stat-num">' + (nFrames - nHit) + '</div><div class="stat-lbl">탐지 실패</div></div>' +
      '</div>' +
      '<div class="viewer-layout">' +
        '<div>' +
          '<img class="viewer-img" id="img-' + epIdx + '" src="" alt="frame">' +
          '<div class="slider-wrap">' +
            '<input type="range" id="slider-' + epIdx + '" min="0" max="' + (nFrames-1) + '" value="0" ' +
            'oninput="renderFrame(' + epIdx + ',parseInt(this.value))">' +
            '<div class="fcounter" id="fcnt-' + epIdx + '">Frame 1 / ' + nFrames + '</div>' +
          '</div>' +
          '<div class="ctrl-btns">' +
            '<button class="btn" onclick="prevFrame(' + epIdx + ')">◀ Prev</button>' +
            '<button class="btn play-btn" id="playbtn-' + epIdx + '" onclick="togglePlay(' + epIdx + ')">▶ Play</button>' +
            '<button class="btn" onclick="nextFrame(' + epIdx + ')">Next ▶</button>' +
            '<button class="btn" id="ovbtn-' + epIdx + '" onclick="toggleOverlay(' + epIdx + ')">🔲 Hide BBox</button>' +
          '</div>' +
          '<div class="thumb-strip" id="thumbs-' + epIdx + '">' + dots + '</div>' +
        '</div>' +
        '<div class="info-panel" id="info-' + epIdx + '"></div>' +
      '</div>';

    container.appendChild(panel);
  }});

  switchEp(0);
}});

document.addEventListener('keydown', e => {{
  if (e.key === 'ArrowRight') {{ e.preventDefault(); nextFrame(curEp); }}
  if (e.key === 'ArrowLeft')  {{ e.preventDefault(); prevFrame(curEp); }}
  if (e.key === ' ')          {{ e.preventDefault(); togglePlay(curEp); }}
}});
</script>
</body>
</html>"""

    out_path = os.path.join(OUTPUT_DIR, "index.html")
    with open(out_path, 'w', encoding='utf-8') as fp:
        fp.write(html)
    size_mb = os.path.getsize(out_path) / 1024 / 1024
    print(f"\nHTML 저장 완료: {out_path}  ({size_mb:.1f} MB)")
    return out_path


# ── 메인 ───────────────────────────────────────────────────────────────────────
def main():
    model, processor = load_model()
    all_eps = []

    for ep_type in EPISODE_TYPES:
        files = sorted(glob.glob(os.path.join(DATASET_DIR, f"*{ep_type}*.h5")))
        if not files:
            print(f"[SKIP] {ep_type}: 파일 없음")
            continue

        ep_path = files[0]
        ep_name = os.path.basename(ep_path)
        print(f"\n[{ep_type}]  →  {ep_name}")

        frames_data, instr, hit_rate = infer_episode(ep_path, model, processor)
        print(f"  {len(frames_data)} 프레임 완료 | BBox 탐지율: {hit_rate:.1f}%")

        all_eps.append({
            'type':         ep_type,
            'name':         ep_name,
            'instruction':  instr,
            'bbox_hit_rate': hit_rate,
            'frames':       frames_data,
        })

    out_path = generate_html(all_eps)
    print(f"\n=== 완료 ===")
    print(f"HTML: {out_path}")
    print(f"\n로컬 서버 실행:")
    print(f"  python3 -m http.server 8765 --directory {OUTPUT_DIR}")
    print(f"  → Mac에서: http://<server-ip>:8765/")


if __name__ == "__main__":
    main()
