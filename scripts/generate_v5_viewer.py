#!/usr/bin/env python3
"""
V5 데이터셋 에피소드 브라우저 HTML 생성기
- grounding JSON 있으면 BBox 오버레이 자동 포함

Usage:
  python3 scripts/generate_v5_viewer.py
Output:
  ROS_action/v5_data_bak/v5_viewer.html
"""

import h5py
import json
import os
from pathlib import Path

# ── 경로 설정 ────────────────────────────────────────────────────
BASE_DIR       = Path("/home/billy/25-1kp/MoNaVLA/ROS_action/v5_data_bak")
H5_DIR         = BASE_DIR / "mobile_vla_dataset_v5"
IMG_DIR        = BASE_DIR / "mobile_vla_dataset_v5(Image)"
OUTPUT_HTML    = BASE_DIR / "v5_viewer.html"
GROUNDING_JSON = BASE_DIR / "v5_grounding.json"
IMG_REL_PREFIX = "mobile_vla_dataset_v5(Image)"

# ── 액션 레이블 매핑 ─────────────────────────────────────────────
def action_label(action):
    lx, az, _ = float(action[0]), float(action[1]), float(action[2])
    if lx == 0.0 and az == 0.0:
        return "STOP"
    if lx > 0 and az > 0:
        return "FWD+LEFT"
    if lx > 0 and az < 0:
        return "FWD+RIGHT"
    if lx > 0:
        return "FORWARD"
    if az > 0:
        return "LEFT"
    if az < 0:
        return "RIGHT"
    return "STOP"

ACTION_COLORS = {
    "STOP":      "#ef4444",
    "FORWARD":   "#22c55e",
    "LEFT":      "#3b82f6",
    "RIGHT":     "#f97316",
    "FWD+LEFT":  "#06b6d4",
    "FWD+RIGHT": "#eab308",
}

# ── grounding 데이터 로드 ────────────────────────────────────────
def load_grounding():
    if not GROUNDING_JSON.exists():
        return None
    with open(GROUNDING_JSON, encoding="utf-8") as f:
        return json.load(f)

# ── 에피소드 데이터 로드 ─────────────────────────────────────────
def load_episodes(grounding_data):
    h5_files = sorted([f for f in os.listdir(H5_DIR) if f.endswith(".h5")])
    episodes = []
    for fname in h5_files:
        ep_id = fname.replace(".h5", "")

        with h5py.File(H5_DIR / fname, "r") as f:
            actions = f["actions"][:].tolist()
            lang = f["language_instruction"][0].decode("utf-8")

        labels = [action_label(a) for a in actions]
        n_frames = len(actions)

        dist = {}
        for lbl in labels:
            dist[lbl] = dist.get(lbl, 0) + 1

        ep_grounding = grounding_data.get(ep_id, {}) if grounding_data else {}

        frames = []
        for i in range(n_frames):
            img_rel = f"{IMG_REL_PREFIX}/{ep_id}/frame_{i:04d}.png"
            img_abs = IMG_DIR / ep_id / f"frame_{i:04d}.png"

            # grounding 데이터
            gr = ep_grounding.get(str(i), ep_grounding.get(i, {}))
            # valid_bboxes: fullscreen 제거된 bbox만 표시
            bboxes  = gr.get("valid_bboxes", gr.get("bboxes", [])) if gr else []
            caption = gr.get("caption", "") if gr else ""

            frames.append({
                "idx":        i,
                "img":        img_rel,
                "exists":     img_abs.exists(),
                "action":     labels[i],
                "action_raw": [round(a, 3) for a in actions[i]],
                "color":      ACTION_COLORS.get(labels[i], "#94a3b8"),
                "bboxes":     bboxes,
                "caption":    caption,
            })

        parts = fname.split("_")
        if len(parts) >= 3:
            ds, ts = parts[1], parts[2]
            try:
                time_fmt = f"20{ds[:2]}-{ds[2:4]}-{ds[4:6]} {ts[:2]}:{ts[2:4]}:{ts[4:6]}"
            except Exception:
                time_fmt = ds + "_" + ts
        else:
            time_fmt = fname[:20]

        episodes.append({
            "id":      ep_id,
            "fname":   fname,
            "time":    time_fmt,
            "lang":    lang,
            "n_frames": n_frames,
            "dist":    dist,
            "frames":  frames,
            "has_grounding": bool(ep_grounding),
        })
    return episodes


# ── Docs 섹션 HTML (별도 문자열 — f-string 중괄호 충돌 방지) ────────
DOCS_HTML = """
<div id="docs-view" class="tab-content" style="display:none">
<div class="dv-wrap">

  <!-- Docs 내부 헤더 -->
  <div class="dv-header">
    <span class="dv-brand">VLA-Analyzer Docs</span>
    <div class="dv-nav">
      <button class="dv-btn" id="dv-prev" onclick="dvChangePage(-1)" disabled>&#8592; 이전</button>
      <span class="dv-indicator" id="dv-indicator">1 / 5</span>
      <button class="dv-btn" id="dv-next" onclick="dvChangePage(1)">다음 &#8594;</button>
    </div>
    <div class="dv-dots" id="dv-dots"></div>
  </div>

  <!-- 5페이지 콘텐츠 -->
  <div class="dv-main">

  <!-- PAGE 1 개요 -->
  <section class="dv-page active" id="dv-page-1">
    <h1 class="dv-h1">VLA-Analyzer &mdash; 개요</h1>
    <p class="dv-subtitle">로컬 HTTP 서버 (localhost:8888) 및 V5 데이터셋 구조 설명</p>

    <h2 class="dv-h2">VLA-Analyzer란?</h2>
    <p>VLA-Analyzer는 MoNaVLA V5 데이터셋의 grounding 결과를 시각적으로 탐색하기 위한 <strong>로컬 정적 웹 도구</strong>다. Python의 <code>http.server</code>를 사용해 <code>localhost:8888</code>에서 서빙되며, 별도 서버 설치 없이 즉시 실행된다.</p>

    <div class="dv-card dv-card-accent">
      <h3 class="dv-h3">서버 실행 방법</h3>
      <pre class="dv-pre"><code>cd ROS_action/v5_data_bak
python -m http.server 8888

# 브라우저에서 접속
http://localhost:8888/v5_viewer.html          # 에피소드 뷰어 (현재 페이지)
http://localhost:8888/vla_analyzer_docs.html  # 독립 문서 페이지</code></pre>
    </div>

    <h2 class="dv-h2">서빙되는 파일 목록</h2>
    <div class="dv-table-wrap">
      <table class="dv-table">
        <thead><tr><th>파일</th><th>역할</th><th>비고</th></tr></thead>
        <tbody>
          <tr><td><code>v5_viewer.html</code></td><td>V5 에피소드별 grounding 시각화</td><td>현재 페이지</td></tr>
          <tr><td><code>v5_grounding.json</code></td><td>820 프레임 전수 grounding 결과</td><td>뷰어가 자동 로딩</td></tr>
          <tr><td><code>vla_analyzer_docs.html</code></td><td>독립 docs 페이지 (이 탭과 동일 내용)</td><td>별도 URL</td></tr>
        </tbody>
      </table>
    </div>

    <h2 class="dv-h2">V5 데이터셋 요약</h2>
    <div class="dv-card">
      <div class="dv-table-wrap" style="margin-bottom:0">
        <table class="dv-table">
          <thead><tr><th>항목</th><th>내용</th></tr></thead>
          <tbody>
            <tr><td>총 에피소드 수</td><td>50개</td></tr>
            <tr><td>총 프레임 수</td><td>820 프레임</td></tr>
            <tr><td>수집 환경</td><td>실내 복도, 회색 바구니를 향해 접근하는 고정 경로 9개</td></tr>
            <tr><td>Grounding 모델</td><td>Pure HF Kosmos-2 (<code>microsoft/kosmos-2-patch14-224</code>)</td></tr>
            <tr><td>채택 프롬프트</td><td><code>&lt;grounding&gt;The gray basket is at</code></td></tr>
          </tbody>
        </table>
      </div>
    </div>
  </section>

  <!-- PAGE 2 모델 비교 -->
  <section class="dv-page" id="dv-page-2">
    <h1 class="dv-h1">Grounding 조사: 모델 비교</h1>
    <p class="dv-subtitle">세 가지 모델 옵션과 image_to_text_projection 오염 문제</p>

    <h2 class="dv-h2">세 가지 모델 옵션</h2>
    <div class="dv-table-wrap">
      <table class="dv-table">
        <thead><tr><th>모델</th><th>로딩 방식</th><th>Text Generation</th><th>Grounding</th></tr></thead>
        <tbody>
          <tr>
            <td><strong>Pure HF Kosmos-2</strong></td>
            <td><code>AutoModelForVision2Seq</code> from HuggingFace</td>
            <td><span class="dv-badge dv-badge-green">정상</span></td>
            <td><span class="dv-badge dv-badge-green">사용 가능</span></td>
          </tr>
          <tr>
            <td><strong>Google-robot pretrained</strong></td>
            <td><code>MobileVLAInference</code> + <code>google-robot-post-train.pt</code></td>
            <td><span class="dv-badge dv-badge-red">garbage 출력</span></td>
            <td><span class="dv-badge dv-badge-red">불가</span></td>
          </tr>
          <tr>
            <td><strong>V4 LoRA</strong></td>
            <td><code>MobileVLAInference</code> + V4 checkpoint</td>
            <td><span class="dv-badge dv-badge-red">garbage 출력</span></td>
            <td><span class="dv-badge dv-badge-red">불가</span></td>
          </tr>
        </tbody>
      </table>
    </div>

    <h3 class="dv-h3">실제 출력 비교</h3>
    <div class="dv-card dv-card-green">
      <strong style="color:#4ade80">Pure HF Kosmos-2 (정상 출력)</strong>
      <pre class="dv-pre" style="margin-top:10px"><code>"The gray basket is located in the middle of the room."
Entity: "the gray box"  |  BBox: (0.33, 0.45) → (0.55, 0.83)</code></pre>
    </div>
    <div class="dv-card dv-card-orange">
      <strong style="color:#fb923c">Google-robot / V4 LoRA (비정상 출력)</strong>
      <pre class="dv-pre" style="margin-top:10px"><code>"Ring Ring Ring Lighted Ring Light Ring Ring Ring Ring..."
# entity grounding 완전 실패</code></pre>
    </div>

    <h2 class="dv-h2">image_to_text_projection 오염 문제</h2>
    <div class="dv-arch">
      <div>Image Encoder (Vision)  <span style="color:#4ade80">← frozen 유지</span></div>
      <div style="padding-left:4px">↓</div>
      <div><span style="color:#fb923c;font-weight:700">image_to_text_projection</span>  <span style="color:#fb923c;font-weight:700">← action 학습으로 덮어씌워짐</span></div>
      <div style="padding-left:4px">↓</div>
      <div>Text Decoder (Language Model)</div>
      <div style="padding-left:4px">↓</div>
      <div>Grounding / Text Output</div>
    </div>

    <p>Google-robot pretrained과 V4 LoRA는 action prediction을 위해 fine-tune된 모델이다. 이 과정에서 <code>image_to_text_projection</code>이 <strong>action feature 공간에 맞게 재학습</strong>되면서 원래의 텍스트 생성 경로가 파괴된다.</p>

    <div class="dv-table-wrap">
      <table class="dv-table">
        <thead><tr><th>학습 전</th><th>학습 후</th></tr></thead>
        <tbody>
          <tr>
            <td>image features → text tokens (grounding / caption 생성)</td>
            <td>image features → action features (텍스트 생성 <strong>불가</strong>)</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="dv-callout"><strong>결론:</strong> fine-tuned 체크포인트에서 원본 grounding 능력을 복구하는 것은 현실적으로 불가능하다. Pure HF 모델을 별도로 로딩하는 것이 <strong>유일한 해결책</strong>이다.</div>
  </section>

  <!-- PAGE 3 프롬프트 비교 -->
  <section class="dv-page" id="dv-page-3">
    <h1 class="dv-h1">Grounding 조사: 프롬프트 비교</h1>
    <p class="dv-subtitle">V5 로봇 이미지 기준 동일 이미지 비교 테스트</p>

    <h2 class="dv-h2">전체 프롬프트 비교표</h2>
    <div class="dv-table-wrap">
      <table class="dv-table">
        <thead><tr><th>프롬프트</th><th>entity 이름</th><th>BBox</th><th>유효 비율</th><th>평가</th></tr></thead>
        <tbody>
          <tr>
            <td><code>&lt;grounding&gt;An image of a robot. Where is the gray basket? Answer:</code></td>
            <td>"The room"</td>
            <td>(0,0)→(1,1) 전체화면</td>
            <td><span class="dv-badge dv-badge-red">1.8%</span></td>
            <td>실패 — 전체화면 hallucination</td>
          </tr>
          <tr>
            <td><code>&lt;grounding&gt;&lt;phrase&gt;gray basket&lt;/phrase&gt;</code></td>
            <td><code>&lt;patch_index_493&gt;...</code> (이름 깨짐)</td>
            <td>(0.42,0.48)→(0.58,0.70)</td>
            <td><span class="dv-badge dv-badge-yellow">가변</span></td>
            <td>bbox는 정확하나 entity 이름 손실</td>
          </tr>
          <tr>
            <td><code>&lt;grounding&gt;A gray basket is located at</code></td>
            <td>"a white wall"</td>
            <td>배경 좌표</td>
            <td><span class="dv-badge dv-badge-red">낮음</span></td>
            <td>실패 — 배경 오검출</td>
          </tr>
          <tr style="background:rgba(56,189,248,0.06)">
            <td><code>&lt;grounding&gt;The gray basket is at</code></td>
            <td><strong>"the gray box"</strong> / <strong>"The basket"</strong></td>
            <td>(0.33,0.45)→(0.55,0.83)</td>
            <td><span class="dv-badge dv-badge-green">100%</span></td>
            <td><strong>최선 선택 ✓</strong></td>
          </tr>
        </tbody>
      </table>
    </div>

    <h2 class="dv-h2">최종 채택 프롬프트 채택 이유</h2>
    <div class="dv-card dv-card-accent" style="margin-bottom:12px">
      <h3 class="dv-h3" style="margin-top:0">1. Entity 이름 정확성</h3>
      <p style="margin-bottom:0">"the gray box" 또는 "The basket" — 바구니를 올바르게 지칭. 색상 분류 필터에서 키워드 매칭이 가능하다.</p>
    </div>
    <div class="dv-card dv-card-accent" style="margin-bottom:12px">
      <h3 class="dv-h3" style="margin-top:0">2. Completion-style prompting</h3>
      <p style="margin-bottom:0">모델이 문장을 완성하도록 유도 → specific location 생성 경향 활용 → 더 정확한 grounding.</p>
    </div>
    <div class="dv-card dv-card-accent" style="margin-bottom:12px">
      <h3 class="dv-h3" style="margin-top:0">3. 유효 검출률 100%</h3>
      <p style="margin-bottom:0">테스트된 모든 820 프레임에서 non-fullscreen bbox 반환. 다른 프롬프트는 전체화면 또는 배경 오검출 빈번.</p>
    </div>

    <h2 class="dv-h2">최종 파이프라인</h2>
    <pre class="dv-pre"><code># 모델 로딩
model = AutoModelForVision2Seq.from_pretrained("microsoft/kosmos-2-patch14-224")

# 프롬프트
prompt = "&lt;grounding&gt;The gray basket is at"

# 후처리 필터
if bbox_area > 0.90:
    skip()  # fullscreen hallucination 제거

# entity 이름으로 색상 분류
color = "green" if "basket"/"box" in name else "yellow" if "gray" in name else "orange"</code></pre>
  </section>

  <!-- PAGE 4 BBox 해석 -->
  <section class="dv-page" id="dv-page-4">
    <h1 class="dv-h1">BBox 해석 가이드</h1>
    <p class="dv-subtitle">색상 분류 기준, fullscreen 필터, convergence 패턴</p>

    <h2 class="dv-h2">색상 분류 기준</h2>
    <div class="dv-legend">
      <div class="dv-legend-item">
        <div class="dv-dot" style="background:#4ade80"></div>
        <div><h4 style="color:#4ade80;margin-bottom:4px">초록 — 바구니 확실</h4>
        <p style="color:#94a3b8;font-size:0.85em;margin:0">entity 이름에 "basket", "box", "container" 포함</p></div>
      </div>
      <div class="dv-legend-item">
        <div class="dv-dot" style="background:#facc15"></div>
        <div><h4 style="color:#facc15;margin-bottom:4px">노랑 — 가능성 있음</h4>
        <p style="color:#94a3b8;font-size:0.85em;margin:0">entity 이름에 "gray", "grey" 포함</p></div>
      </div>
      <div class="dv-legend-item">
        <div class="dv-dot" style="background:#fb923c"></div>
        <div><h4 style="color:#fb923c;margin-bottom:4px">주황 — 배경 오검출</h4>
        <p style="color:#94a3b8;font-size:0.85em;margin:0">"wall", "floor", "air conditioner" 등</p></div>
      </div>
    </div>

    <div class="dv-callout"><strong>Fullscreen 필터:</strong> bbox 면적 &gt; 0.90인 경우 hallucination으로 판단, 표시하지 않는다. "The room" 같은 전체화면 entity를 제거하는 필터다.</div>

    <h2 class="dv-h2">BBox Convergence 패턴 — ep3 실제 데이터</h2>
    <p>Fixed Center Path에서 로봇이 바구니를 향해 접근할수록 bbox 변화:</p>

    <div class="dv-timeline">
      <div class="dv-tl-row"><span class="dv-tl-f">f00-f04</span><span class="dv-tl-e"><span class="dv-badge dv-badge-orange">주황</span> "white wall" 계열</span><span class="dv-tl-a" style="color:#64748b">배경 — 바구니 미검출</span></div>
      <div class="dv-tl-row"><span class="dv-tl-f">f05</span><span class="dv-tl-e"><span class="dv-badge dv-badge-green">초록</span> "The box"</span><span class="dv-tl-a" style="color:#facc15">area 0.077</span></div>
      <div class="dv-tl-row"><span class="dv-tl-f">f06</span><span class="dv-tl-e"><span class="dv-badge dv-badge-green">초록</span> "The basket"</span><span class="dv-tl-a" style="color:#facc15">area 0.083</span></div>
      <div class="dv-tl-row"><span class="dv-tl-f">f09</span><span class="dv-tl-e"><span class="dv-badge dv-badge-green">초록</span> "The basket"</span><span class="dv-tl-a" style="color:#fb923c">area 0.170</span></div>
      <div class="dv-tl-row"><span class="dv-tl-f">f10</span><span class="dv-tl-e"><span class="dv-badge dv-badge-green">초록</span> "The basket"</span><span class="dv-tl-a" style="color:#fb923c">area 0.211</span></div>
      <div class="dv-tl-row"><span class="dv-tl-f">f11</span><span class="dv-tl-e"><span class="dv-badge dv-badge-green">초록</span> "The basket"</span><span class="dv-tl-a" style="color:#f87171">area 0.246 ↑</span></div>
    </div>

    <div class="dv-callout"><strong>핵심 관찰:</strong> bbox 면적이 에피소드 진행에 따라 단조 증가하고, bbox 중심이 이미지 중앙 하단으로 수렴하는 것이 "올바른 접근 행동"의 visual signature다.</div>
  </section>

  <!-- PAGE 5 검증 방법론 -->
  <section class="dv-page" id="dv-page-5">
    <h1 class="dv-h1">V5 BBox-Centric 검증 방법론</h1>
    <p class="dv-subtitle">무엇을 검증하는가, 성공 기준, 뷰어 사용법</p>

    <h2 class="dv-h2">검증의 목적</h2>
    <p>BBox-Centric 방법론은 <strong>"로봇 카메라에서 바구니 bbox가 어떻게 변화하는가"</strong>를 ground truth로 사용해 모델이 올바른 접근 행동을 학습했는지 시각적으로 확인한다.</p>

    <h2 class="dv-h2">검증 항목 및 성공 기준</h2>
    <div class="dv-table-wrap">
      <table class="dv-table">
        <thead><tr><th>검증 항목</th><th>성공 기준</th></tr></thead>
        <tbody>
          <tr><td><strong>BBox 크기 증가</strong></td><td>에피소드 진행에 따라 bbox 면적 단조 증가</td></tr>
          <tr><td><strong>중앙 수렴</strong></td><td>종료 시 |center_x − 0.5| &lt; 0.15</td></tr>
          <tr><td><strong>하단 채움</strong></td><td>종료 시 bbox y2 &gt; 0.80</td></tr>
          <tr><td><strong>초록 bbox 비율</strong></td><td>후반부 50% 이상 프레임에서 초록 검출</td></tr>
          <tr><td><strong>최종 면적</strong></td><td>마지막 프레임 area &gt; 0.15 (화면의 15% 이상)</td></tr>
        </tbody>
      </table>
    </div>

    <h2 class="dv-h2">뷰어 사용 방법</h2>
    <div class="dv-card">
      <ul style="padding-left:20px;line-height:1.9">
        <li><strong>Episode Browser 탭</strong> → 에피소드 선택 → 프레임별 bbox 변화 확인</li>
        <li><strong>색상 범례</strong>: 초록/노랑/주황으로 검출 품질 즉시 파악</li>
        <li><strong>BBox 토글</strong>: 상단 탭바의 "BBox 표시" 버튼으로 오버레이 on/off</li>
        <li><strong>entity 이름</strong>: bbox 라벨에 Kosmos-2가 생성한 entity 이름 표시</li>
      </ul>
    </div>

    <h2 class="dv-h2">관련 파일 경로</h2>
    <pre class="dv-pre"><code>ROS_action/v5_data_bak/
  v5_viewer.html            # 메인 시각화 뷰어 (현재 페이지)
  v5_grounding.json         # 820 프레임 grounding 결과
  vla_analyzer_docs.html    # 독립 docs 페이지

docs/
  grounding_briefing.md     # 기술 브리핑 (Markdown)

scripts/
  run_v5_grounding.py       # grounding 실행
  generate_v5_viewer.py     # 뷰어 HTML 생성</code></pre>

    <h2 class="dv-h2">V5 이후 개선 계획</h2>
    <div class="dv-card dv-card-accent" style="margin-bottom:12px">
      <h3 class="dv-h3" style="margin-top:0">단기</h3>
      <ul style="padding-left:20px">
        <li>BBox convergence 패턴 자동 감지 알고리즘 추가</li>
        <li>에피소드별 convergence score 계산 및 랭킹</li>
      </ul>
    </div>
    <div class="dv-card dv-card-accent">
      <h3 class="dv-h3" style="margin-top:0">중기</h3>
      <ul style="padding-left:20px">
        <li><code>image_to_text_projection</code> frozen 유지 학습 설계</li>
        <li>Grounding 신호를 action 학습의 auxiliary loss로 활용</li>
        <li>BBox-guided attention: 바구니 위치를 action prediction에 직접 주입</li>
      </ul>
    </div>
  </section>

  </div><!-- dv-main -->
</div><!-- dv-wrap -->
</div><!-- docs-view -->
"""


# ── HTML 생성 ────────────────────────────────────────────────────
def generate_html(episodes, has_grounding: bool):
    total_frames = sum(e["n_frames"] for e in episodes)
    grounded_eps = sum(1 for e in episodes if e["has_grounding"])

    global_dist = {}
    for ep in episodes:
        for k, v in ep["dist"].items():
            global_dist[k] = global_dist.get(k, 0) + v

    sidebar_items = ""
    for i, ep in enumerate(episodes):
        grounding_dot = '<span style="color:#a3e635;font-size:0.7em;margin-left:4px">● BBox</span>' if ep["has_grounding"] else ""
        dist_pills = " ".join(
            f'<span class="pill" style="background:{ACTION_COLORS.get(k,"#94a3b8")}">{k}×{v}</span>'
            for k, v in ep["dist"].items()
        )
        sidebar_items += f"""
        <div class="ep-item" onclick="showEpisode({i})" id="ep-btn-{i}">
            <div class="ep-time">{ep['time']}{grounding_dot}</div>
            <div class="ep-pills">{dist_pills}</div>
        </div>"""

    episodes_json = json.dumps(episodes, ensure_ascii=False)

    global_bars = ""
    for lbl, cnt in sorted(global_dist.items(), key=lambda x: -x[1]):
        pct = cnt / total_frames * 100
        global_bars += f"""
        <div class="stat-row">
            <span class="stat-label" style="color:{ACTION_COLORS.get(lbl,'#94a3b8')}">{lbl}</span>
            <div class="stat-bar-bg"><div class="stat-bar-fill" style="width:{pct:.1f}%;background:{ACTION_COLORS.get(lbl,'#94a3b8')}"></div></div>
            <span class="stat-count">{cnt} ({pct:.1f}%)</span>
        </div>"""

    grounding_badge = (
        f'<span style="background:#16a34a;color:#fff;padding:3px 10px;border-radius:12px;font-size:0.75em;margin-left:12px">● BBox ({grounded_eps}/{len(episodes)} eps)</span>'
        if has_grounding else
        '<span style="background:#475569;color:#94a3b8;padding:3px 10px;border-radius:12px;font-size:0.75em;margin-left:12px">BBox 없음 — run_v5_grounding.py 실행 필요</span>'
    )

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>MoNaVLA V5 — VLA-Analyzer</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Segoe UI', sans-serif; background: #020617; color: #f8fafc; height: 100vh; display: flex; flex-direction: column; }}

  .header {{ background: #0f172a; border-bottom: 1px solid #1e293b; padding: 12px 24px; display: flex; align-items: center; justify-content: space-between; flex-shrink: 0; }}
  .header h1 {{ color: #38bdf8; font-size: 1.3em; }}
  .header-meta {{ color: #64748b; font-size: 0.85em; text-align: right; }}

  /* ── 탭바 ── */
  .tab-bar {{ background: #0f172a; border-bottom: 2px solid #1e293b; padding: 0 24px; display: flex; align-items: center; gap: 4px; flex-shrink: 0; height: 42px; }}
  .tab-btn {{ background: none; border: none; border-bottom: 3px solid transparent; color: #64748b; padding: 0 16px; height: 100%; font-size: 0.85em; cursor: pointer; transition: all 0.2s; white-space: nowrap; }}
  .tab-btn:hover {{ color: #94a3b8; }}
  .tab-btn.active {{ color: #38bdf8; border-bottom-color: #38bdf8; font-weight: 600; }}
  .tab-spacer {{ flex: 1; }}

  /* BBox 토글 버튼 */
  .toggle-btn {{ background: #1e293b; border: 1px solid #334155; color: #94a3b8; padding: 4px 14px; border-radius: 20px; font-size: 0.78em; cursor: pointer; transition: all 0.2s; }}
  .toggle-btn.active {{ background: #16a34a; border-color: #16a34a; color: #fff; }}
  #bbox-bar {{ display: flex; align-items: center; gap: 8px; }}

  .layout {{ display: flex; flex: 1; overflow: hidden; }}

  .sidebar {{ width: 280px; background: #0f172a; border-right: 1px solid #1e293b; display: flex; flex-direction: column; flex-shrink: 0; }}
  .sidebar-header {{ padding: 12px 16px; border-bottom: 1px solid #1e293b; background: #1e293b; }}
  .sidebar-header h3 {{ color: #94a3b8; font-size: 0.8em; text-transform: uppercase; letter-spacing: 1px; }}
  .sidebar-list {{ overflow-y: auto; flex: 1; }}
  .ep-item {{ padding: 10px 14px; border-bottom: 1px solid #1e293b; cursor: pointer; transition: background 0.15s; }}
  .ep-item:hover {{ background: #1e293b; }}
  .ep-item.active {{ background: #0c4a6e; border-left: 3px solid #38bdf8; }}
  .ep-time {{ font-size: 0.78em; color: #94a3b8; margin-bottom: 5px; font-family: monospace; }}
  .ep-pills {{ display: flex; flex-wrap: wrap; gap: 3px; }}
  .pill {{ font-size: 0.68em; padding: 2px 6px; border-radius: 10px; color: #000; font-weight: bold; opacity: 0.9; }}

  .main {{ flex: 1; display: flex; flex-direction: column; overflow: hidden; }}

  .stats-panel {{ background: #0f172a; border-bottom: 1px solid #1e293b; padding: 14px 20px; flex-shrink: 0; }}
  .stats-title {{ color: #64748b; font-size: 0.75em; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 10px; }}
  .stat-row {{ display: flex; align-items: center; gap: 10px; margin-bottom: 5px; }}
  .stat-label {{ width: 90px; font-size: 0.78em; font-weight: bold; text-align: right; }}
  .stat-bar-bg {{ flex: 1; height: 8px; background: #1e293b; border-radius: 4px; overflow: hidden; }}
  .stat-bar-fill {{ height: 100%; border-radius: 4px; transition: width 0.4s; }}
  .stat-count {{ width: 110px; font-size: 0.75em; color: #64748b; }}

  .ep-detail {{ flex: 1; overflow-y: auto; padding: 20px; }}
  .ep-instruction {{ background: #0f172a; border: 1px dashed #38bdf8; padding: 12px 16px; border-radius: 8px; color: #7dd3fc; font-family: monospace; font-size: 0.9em; margin-bottom: 16px; }}
  .ep-instruction b {{ color: #38bdf8; }}
  .ep-meta {{ display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 16px; }}
  .meta-chip {{ background: #1e293b; padding: 6px 14px; border-radius: 20px; font-size: 0.8em; color: #94a3b8; }}

  .frame-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 12px; }}
  .frame-card {{ background: #1e293b; border-radius: 10px; overflow: hidden; border: 2px solid #334155; transition: border-color 0.2s; }}
  .frame-card:hover {{ border-color: #38bdf8; }}

  /* 이미지 + BBox 오버레이 */
  .frame-img-wrap {{ position: relative; aspect-ratio: 16/9; background: #000; overflow: hidden; }}
  .frame-img-wrap img {{ width: 100%; height: 100%; object-fit: cover; display: block; }}

  /* BBox 오버레이 */
  .bbox-overlay {{ position: absolute; pointer-events: none; top: 0; left: 0; width: 100%; height: 100%; }}
  .bbox-rect {{ position: absolute; border: 2px solid #00ff88; background: rgba(0,255,136,0.08); box-shadow: 0 0 8px rgba(0,255,136,0.5); border-radius: 2px; }}
  .bbox-label {{ position: absolute; background: #00ff88; color: #000; font-size: 0.55em; font-weight: bold; padding: 1px 4px; border-radius: 2px; transform: translateY(-100%); white-space: nowrap; }}
  .bbox-none {{ position: absolute; bottom: 4px; right: 4px; background: rgba(239,68,68,0.85); color: #fff; font-size: 0.6em; padding: 2px 6px; border-radius: 4px; }}

  .frame-info {{ padding: 8px 10px; }}
  .frame-num {{ font-size: 0.72em; color: #64748b; font-family: monospace; }}
  .action-badge {{ display: inline-block; margin-top: 4px; padding: 3px 10px; border-radius: 12px; font-size: 0.72em; font-weight: bold; color: #000; }}
  .action-raw {{ font-size: 0.65em; color: #475569; font-family: monospace; margin-top: 2px; }}
  .caption-text {{ font-size: 0.65em; color: #a3e635; font-style: italic; margin-top: 3px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}

  .placeholder {{ flex: 1; display: flex; align-items: center; justify-content: center; color: #334155; font-size: 1.2em; }}

  /* ── tab content wrapper ── */
  .tab-content {{ display: none; flex: 1; overflow: hidden; }}
  .tab-content.active {{ display: flex; flex-direction: column; }}

  ::-webkit-scrollbar {{ width: 6px; }}
  ::-webkit-scrollbar-track {{ background: #0f172a; }}
  ::-webkit-scrollbar-thumb {{ background: #334155; border-radius: 3px; }}

  /* ═══════════ DOCS VIEW CSS (dv- prefix) ═══════════ */
  .dv-wrap {{ display: flex; flex-direction: column; flex: 1; overflow: hidden; }}
  .dv-header {{ background: #0f172a; border-bottom: 1px solid #1e293b; padding: 0 28px; height: 44px; display: flex; align-items: center; gap: 16px; flex-shrink: 0; }}
  .dv-brand {{ font-size: 0.95rem; font-weight: 700; color: #38bdf8; }}
  .dv-nav {{ display: flex; align-items: center; gap: 10px; }}
  .dv-btn {{ background: #1e293b; border: 1px solid #334155; color: #e2e8f0; padding: 4px 12px; border-radius: 6px; cursor: pointer; font-size: 0.82rem; transition: background 0.15s; }}
  .dv-btn:hover:not(:disabled) {{ background: #334155; }}
  .dv-btn:disabled {{ opacity: 0.35; cursor: default; }}
  .dv-indicator {{ font-size: 0.82rem; color: #94a3b8; }}
  .dv-dots {{ display: flex; align-items: center; gap: 6px; margin-left: 4px; }}
  .dv-dot {{ width: 7px; height: 7px; border-radius: 50%; background: #334155; cursor: pointer; transition: background 0.15s; }}
  .dv-dot.active {{ background: #38bdf8; }}
  .dv-main {{ flex: 1; overflow-y: auto; padding: 32px 40px 60px; max-width: 900px; width: 100%; margin: 0 auto; }}
  .dv-page {{ display: none; }}
  .dv-page.active {{ display: block; }}
  .dv-h1 {{ font-size: 1.7rem; font-weight: 800; color: #38bdf8; margin-bottom: 6px; }}
  .dv-h2 {{ font-size: 1.15rem; font-weight: 700; color: #7dd3fc; margin-top: 32px; margin-bottom: 12px; }}
  .dv-h3 {{ font-size: 0.98rem; font-weight: 600; color: #cbd5e1; margin-top: 20px; margin-bottom: 8px; }}
  .dv-subtitle {{ color: #64748b; font-size: 0.9rem; margin-bottom: 28px; border-bottom: 1px solid #1e293b; padding-bottom: 16px; }}
  .dv-card {{ background: #0f172a; border: 1px solid #334155; border-radius: 8px; padding: 18px 22px; margin-bottom: 18px; }}
  .dv-card-accent {{ border-left: 3px solid #38bdf8; }}
  .dv-card-green  {{ border-left: 3px solid #4ade80; }}
  .dv-card-orange {{ border-left: 3px solid #fb923c; }}
  .dv-table-wrap {{ overflow-x: auto; margin-bottom: 18px; }}
  .dv-table {{ width: 100%; border-collapse: collapse; font-size: 0.85rem; }}
  .dv-table th {{ background: #1e293b; color: #38bdf8; font-weight: 600; padding: 9px 12px; text-align: left; border-bottom: 2px solid #334155; }}
  .dv-table td {{ padding: 8px 12px; border-bottom: 1px solid #1e293b; vertical-align: top; }}
  .dv-table tr:last-child td {{ border-bottom: none; }}
  .dv-pre {{ background: #070f1e; border: 1px solid #1e293b; border-radius: 6px; padding: 14px 16px; overflow-x: auto; margin-bottom: 16px; font-size: 0.8rem; line-height: 1.6; font-family: 'Cascadia Code','Fira Code',monospace; color: #93c5fd; }}
  .dv-callout {{ background: rgba(56,189,248,0.06); border: 1px solid rgba(56,189,248,0.25); border-radius: 6px; padding: 12px 16px; font-size: 0.86rem; color: #7dd3fc; margin-bottom: 16px; }}
  .dv-callout strong {{ color: #38bdf8; }}
  .dv-arch {{ background: #070f1e; border: 1px solid #1e293b; border-radius: 6px; padding: 16px 20px; font-family: monospace; font-size: 0.83rem; color: #64748b; margin-bottom: 16px; line-height: 1.9; }}
  .dv-legend {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 12px; margin-bottom: 18px; }}
  .dv-legend-item {{ background: #0f172a; border: 1px solid #334155; border-radius: 6px; padding: 12px 16px; display: flex; align-items: flex-start; gap: 12px; }}
  .dv-dot {{ width: 14px; height: 14px; border-radius: 50%; flex-shrink: 0; margin-top: 3px; }}
  .dv-timeline {{ margin: 12px 0 18px; }}
  .dv-tl-row {{ display: flex; align-items: center; gap: 10px; padding: 7px 0; border-bottom: 1px solid #1e293b; font-size: 0.83rem; }}
  .dv-tl-row:last-child {{ border-bottom: none; }}
  .dv-tl-f {{ width: 50px; flex-shrink: 0; font-weight: 600; color: #38bdf8; font-family: monospace; }}
  .dv-tl-e {{ flex: 1; }}
  .dv-tl-a {{ width: 90px; flex-shrink: 0; text-align: right; font-family: monospace; font-size: 0.78rem; }}
  .dv-badge {{ display: inline-block; padding: 1px 7px; border-radius: 10px; font-size: 0.74rem; font-weight: 600; margin-right: 3px; }}
  .dv-badge-green  {{ background: rgba(74,222,128,0.15);  color: #4ade80; border: 1px solid rgba(74,222,128,0.3); }}
  .dv-badge-yellow {{ background: rgba(250,204,21,0.12);  color: #facc15; border: 1px solid rgba(250,204,21,0.3); }}
  .dv-badge-orange {{ background: rgba(251,146,60,0.12);  color: #fb923c; border: 1px solid rgba(251,146,60,0.3); }}
  .dv-badge-red    {{ background: rgba(248,113,113,0.12); color: #f87171; border: 1px solid rgba(248,113,113,0.3); }}
</style>
</head>
<body>

<!-- ── 헤더 ── -->
<div class="header">
  <div style="display:flex;align-items:center;gap:16px">
    <h1>MoNaVLA V5 &mdash; VLA-Analyzer</h1>
    <span style="color:#334155;font-size:0.9em">|</span>
    <span style="color:#64748b;font-size:0.82em">{len(episodes)} eps &nbsp;·&nbsp; {total_frames} frames &nbsp;·&nbsp; {grounding_badge}</span>
  </div>
  <div class="header-meta">
    <div>mobile_vla_dataset_v5 &nbsp;|&nbsp; 2026-04-08</div>
  </div>
</div>

<!-- ── 탭바 ── -->
<div class="tab-bar">
  <button class="tab-btn active" id="tab-browser" onclick="switchTab('browser')">Episode Browser</button>
  <button class="tab-btn" id="tab-docs" onclick="switchTab('docs')">Docs</button>
  <div class="tab-spacer"></div>
  <div id="bbox-bar" style="{'display:flex' if has_grounding else 'display:none'}">
    {'<button class="toggle-btn active" id="bbox-toggle-btn" onclick="toggleBBox()">● BBox 표시</button><span style="color:#64748b;font-size:0.75em;margin-left:6px">Kosmos-2 Grounding</span>' if has_grounding else ''}
  </div>
</div>

<!-- ── Browser 탭 콘텐츠 ── -->
<div id="browser-view" class="tab-content active">
  <div class="layout">
    <div class="sidebar">
      <div class="sidebar-header">
        <h3>Episodes ({len(episodes)})</h3>
      </div>
      <div class="sidebar-list">
        {sidebar_items}
      </div>
    </div>

    <div class="main" id="main-panel">
      <div class="stats-panel" id="stats-panel">
        <div class="stats-title">전체 액션 분포 ({total_frames} frames)</div>
        {global_bars}
      </div>
      <div class="ep-detail" id="ep-detail">
        <div class="placeholder">← 에피소드를 선택하세요</div>
      </div>
    </div>
  </div>
</div>

<!-- ── Docs 탭 콘텐츠 ── -->
{DOCS_HTML}

<script>
const EPISODES = {episodes_json};
const ACTION_COLORS = {json.dumps(ACTION_COLORS)};
const HAS_GROUNDING = {'true' if has_grounding else 'false'};
let showBBox = true;
let currentEp = null;

/* ── 탭 전환 ── */
function switchTab(name) {{
  document.getElementById('browser-view').classList.toggle('active', name === 'browser');
  document.getElementById('docs-view').classList.toggle('active', name === 'docs');
  document.getElementById('tab-browser').classList.toggle('active', name === 'browser');
  document.getElementById('tab-docs').classList.toggle('active', name === 'docs');
  const bboxBar = document.getElementById('bbox-bar');
  if (bboxBar) bboxBar.style.display = name === 'browser' ? 'flex' : 'none';
}}

function toggleBBox() {{
  showBBox = !showBBox;
  const btn = document.getElementById('bbox-toggle-btn');
  if (btn) {{
    btn.classList.toggle('active', showBBox);
    btn.textContent = showBBox ? '● BBox 표시' : '○ BBox 숨김';
  }}
  if (currentEp !== null) showEpisode(currentEp);
}}

function makeBBoxOverlay(bboxes) {{
  if (!HAS_GROUNDING || !showBBox || !bboxes || bboxes.length === 0) {{
    return HAS_GROUNDING && showBBox
      ? '<div class="bbox-none">NO BBOX</div>'
      : '';
  }}
  let html = '<div class="bbox-overlay">';
  for (const b of bboxes) {{
    const left  = (b.x1 * 100).toFixed(2);
    const top   = (b.y1 * 100).toFixed(2);
    const w     = ((b.x2 - b.x1) * 100).toFixed(2);
    const h     = ((b.y2 - b.y1) * 100).toFixed(2);
    // BBox 크기로 신뢰도 색상 (클수록 초록, 작을수록 노랑)
    const area = (b.x2 - b.x1) * (b.y2 - b.y1);
    const name = (b.entity || '').toLowerCase();
    // entity 이름으로 분류: basket/box → 초록, gray X → 노랑, 기타 → 주황
    const isBasket = name.includes('basket') || name.includes('box') || name.includes('container');
    const isGray   = name.includes('gray') || name.includes('grey');
    const color = isBasket ? '#00ff88' : isGray ? '#facc15' : '#fb923c';
    const pct = (area * 100).toFixed(1);
    html += `
      <div class="bbox-rect" style="left:${{left}}%;top:${{top}}%;width:${{w}}%;height:${{h}}%;border-color:${{color}};box-shadow:0 0 8px ${{color}}40">
        <span class="bbox-label" style="background:${{color}}">${{b.entity || 'basket'}} ${{pct}}%</span>
      </div>`;
  }}
  html += '</div>';
  return html;
}}

function renderFrames(idx) {{
  const ep = EPISODES[idx];
  let frameCards = '';
  for (const frame of ep.frames) {{
    const bboxHtml = makeBBoxOverlay(frame.bboxes || []);
    const imgTag = frame.exists
      ? `<img src="${{frame.img}}" alt="frame ${{frame.idx}}" loading="lazy">`
      : `<div style="width:100%;height:100%;display:flex;align-items:center;justify-content:center;color:#334155;font-size:0.7em;">NO IMAGE</div>`;
    const captionHtml = (HAS_GROUNDING && frame.caption)
      ? `<div class="caption-text" title="${{frame.caption}}">${{frame.caption.substring(0,60)}}${{frame.caption.length>60?'…':''}}</div>`
      : '';
    frameCards += `
      <div class="frame-card">
        <div class="frame-img-wrap">${{imgTag}}${{bboxHtml}}</div>
        <div class="frame-info">
          <div class="frame-num">Frame ${{String(frame.idx).padStart(4,'0')}}</div>
          <span class="action-badge" style="background:${{frame.color}}">${{frame.action}}</span>
          <div class="action-raw">[${{frame.action_raw.join(', ')}}]</div>
          ${{captionHtml}}
        </div>
      </div>`;
  }}
  return frameCards;
}}

function showEpisode(idx) {{
  document.querySelectorAll('.ep-item').forEach(el => el.classList.remove('active'));
  document.getElementById('ep-btn-' + idx).classList.add('active');
  currentEp = idx;

  const ep = EPISODES[idx];

  // 통계 바 업데이트
  const statsPanel = document.getElementById('stats-panel');
  let barsHtml = `<div class="stats-title">${{ep.time}} — 액션 분포 (${{ep.n_frames}} frames)${{ep.has_grounding ? ' <span style="color:#a3e635;font-size:0.85em">● BBox 있음</span>' : ''}}</div>`;
  for (const [lbl, cnt] of Object.entries(ep.dist).sort((a,b) => b[1]-a[1])) {{
    const pct = (cnt / ep.n_frames * 100).toFixed(1);
    const color = ACTION_COLORS[lbl] || '#94a3b8';
    barsHtml += `
      <div class="stat-row">
        <span class="stat-label" style="color:${{color}}">${{lbl}}</span>
        <div class="stat-bar-bg"><div class="stat-bar-fill" style="width:${{pct}}%;background:${{color}}"></div></div>
        <span class="stat-count">${{cnt}} (${{pct}}%)</span>
      </div>`;
  }}
  statsPanel.innerHTML = barsHtml;

  // 프레임 그리드
  const frameCards = renderFrames(idx);
  document.getElementById('ep-detail').innerHTML = `
    <div class="ep-instruction"><b>Instruction:</b> ${{ep.lang}}</div>
    <div class="ep-meta">
      <span class="meta-chip">📁 ${{ep.fname.substring(0,50)}}...</span>
      <span class="meta-chip">🎬 ${{ep.n_frames}} frames</span>
    </div>
    <div class="frame-grid">${{frameCards}}</div>
  `;
}}

if (EPISODES.length > 0) showEpisode(0);

/* ── Docs 페이지 네비게이션 ── */
let dvCurrent = 1;
const DV_TOTAL = 5;

function dvRenderDots() {{
  const c = document.getElementById('dv-dots');
  if (!c) return;
  c.innerHTML = '';
  for (let i = 1; i <= DV_TOTAL; i++) {{
    const d = document.createElement('div');
    d.className = 'dv-dot' + (i === dvCurrent ? ' active' : '');
    d.title = '페이지 ' + i;
    d.onclick = () => dvGoTo(i);
    c.appendChild(d);
  }}
}}

function dvGoTo(n) {{
  document.getElementById('dv-page-' + dvCurrent).classList.remove('active');
  dvCurrent = Math.max(1, Math.min(DV_TOTAL, n));
  document.getElementById('dv-page-' + dvCurrent).classList.add('active');
  document.getElementById('dv-indicator').textContent = dvCurrent + ' / ' + DV_TOTAL;
  document.getElementById('dv-prev').disabled = dvCurrent === 1;
  document.getElementById('dv-next').disabled = dvCurrent === DV_TOTAL;
  dvRenderDots();
  const m = document.querySelector('.dv-main');
  if (m) m.scrollTo({{top: 0, behavior: 'smooth'}});
}}

function dvChangePage(delta) {{ dvGoTo(dvCurrent + delta); }}

document.addEventListener('keydown', function(e) {{
  const docsActive = document.getElementById('docs-view').classList.contains('active');
  if (!docsActive) return;
  if (e.key === 'ArrowRight' || e.key === 'ArrowDown') dvChangePage(1);
  if (e.key === 'ArrowLeft'  || e.key === 'ArrowUp')   dvChangePage(-1);
}});

dvRenderDots();
</script>
</body>
</html>"""
    return html


# ── 실행 ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    grounding_data = load_grounding()
    has_grounding  = grounding_data is not None

    if has_grounding:
        grounded_count = sum(1 for ep in grounding_data.values() if ep)
        print(f"  BBox 데이터 로드: {grounded_count}개 에피소드")
    else:
        print("  BBox 데이터 없음 (run_v5_grounding.py 실행 후 재생성 가능)")

    print("에피소드 로딩 중...")
    episodes = load_episodes(grounding_data)
    print(f"  → {len(episodes)}개 에피소드 로드 완료")

    print("HTML 생성 중...")
    html = generate_html(episodes, has_grounding)

    OUTPUT_HTML.write_text(html, encoding="utf-8")
    print(f"\n✅ 생성 완료: {OUTPUT_HTML}")
    print(f"   서버: python3 -m http.server 8888 --directory {BASE_DIR}")
    print(f"   URL:  http://localhost:8888/v5_viewer.html")
