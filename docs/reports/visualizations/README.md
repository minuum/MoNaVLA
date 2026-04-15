# 교수님 질문 Q1-Q5 시각화 자료

**생성일**: 2025-12-04  
**목적**: 논문 수준의 전문적인 시각화로 연구 결과 제시

---

## 📊 생성된 시각화 목록

### Q1: Context Vector 검증
**파일**: `Q1_context_vector_analysis.png` (578 KB)  
**내용**:
- **(A)** VLM 아키텍처 및 Context 추출 구조
  - Image → Vision Encoder (1024D) + Language Encoder (1024D) → Context Vector (2048D)
  - Hook Point 표시
- **(B)** Kosmos-2 vs RoboVLMs context vector 분포 비교
  - Histogram overlay
  - 통계치 (mean, std) 표시
- **(C)** Feature별 상관관계 분석
  - Scatter plot: Kosmos-2 vs RoboVLMs per-feature mean
  - Correlation coefficient

**활용**:
- 리포트: `docs/reports/Q1_Context_Vector_Report.md`
- 교수님 프레젠테이션 시 Figure 1로 사용

---

### Q2: Velocity Output 검증
**파일**: `Q2_velocity_output.png` (766 KB)  
**내용**:
- **(A)** Linear X Velocity: Predicted vs Ground Truth
  - Time series plot with RMSE
- **(B)** Angular Z Velocity: Predicted vs Ground Truth
  - Time series plot with RMSE
- **(C)** 예측 에러 분포
  - Histogram for both linear and angular errors
- **(D-E)** Scatter plots (상관관계)
  - Perfect prediction line (y=x)
  - Correlation coefficient
- **(F)** 종합 성능 메트릭 테이블
  - RMSE, Correlation, Mean/Std Error
  - Quality assessment

**활용**:
- 리포트: `docs/reports/Q2_Velocity_Output_Report.md`
- "제대로 된 x, y 값을 뿌려주는가?" 질문에 대한 정량적 증거

---

### Q3: Left+Right 균형 데이터 효과
**파일**: `Q3_balance_comparison.png` (671 KB)  
**내용**:
- **(A)** Training/Validation Loss 곡선
  - Case 1 (Left only 250) vs Case 3 (Left+Right 500)
  - Best epoch markers
  - Log scale
- **(B)** 데이터 분포
  - Stacked bar chart: Left (blue) + Right (red)
  - Episode counts
- **(C)** 최종 성능 메트릭 비교
  - Bar chart: Val Loss, Train Loss, RMSE
  - Value labels on bars
- **(D)** 일반화 성능
  - Success rate (%) on Left/Right/Mixed scenarios
  - Case 1 vs Case 3 comparison
- **(E)** Accuracy vs Generalization Trade-off
  - Scatter plot with annotations
  - Shows Case 1 (high accuracy, low generalization)
  - Shows Case 3 (balanced)

**활용**:
- 리포트: `docs/reports/Q3_LeftRight_Balance_Report.md`
- "균형 데이터가 왜 중요한가?" 시각적 설명

---

### Q4: 7-DOF → 2-DOF 변환 불가능성
**파일**: `Q4_7dof_to_2dof.png` (175 KB)  
**내용**:
- **(A)** Action Space 차원 불일치
  - Manipulation (7-DOF): x, y, z, roll, pitch, yaw, gripper
  - Mobile (2-DOF): linear_x, angular_z
  - Cross mark showing incompatibility
- **(B)** 해결책: Action Head 교체
  - VLM Backbone (shared, frozen)
  - Split to different action heads
  - Manipulation Head (2048D → 7D)
  - Mobile Head (2048D → 2D)
  - Checkmarks showing both work

**활용**:
- 리포트: `docs/reports/Q4_7DOF_to_2DOF_Report.md`
- "왜 직접 변환이 안 되는가?" 명확한 시각적 설명

---

### Q5: 추론 시나리오 및 Latency
**파일**: `Q5_inference_scenario.png` (353 KB)  
**내용**:
- **(A)** 실시간 추론 파이프라인
  - 7 단계 flow: Image Capture → Preprocessing → VLM → Context → LSTM → Action Chunk → Velocity
  - 각 단계별 latency (ms)
  - Total: 122ms < 200ms target
- **(B)** Latency Breakdown (Bar Chart)
  - VLM이 가장 오래 걸림 (50ms)
  - Target line (200ms)
- **(C)** Action Chunk 실행 타임라인
  - 0.4s 간격으로 10개 action 실행
  - Timeline from 0 to 4 seconds

**활용**:
- 리포트: `docs/reports/Q5_Inference_Scenario_Report.md`
- "0.4초 간격 추론이 가능한가?" 실증

---

## 🎨 디자인 특징

### 논문 품질 표준
1. **색상 팔레트**
   - Primary: #2E86AB (Blue) - 주요 데이터
   - Secondary: #A23B72 (Purple) - 보조 데이터
   - Success: #06A77D (Green) - 성공/목표
   - Warning: #F18F01 (Orange) - 주의/강조
   - Danger: #C73E1D (Red) - 에러/문제

2. **타이포그래피**
   - Font: DejaVu Sans (논문 표준)
   - Title: 12pt, Bold
   - Axis labels: 11pt, Bold
   - Legends: 9pt
   - Annotations: 8-10pt

3. **레이아웃**
   - Multi-panel figures (A, B, C, ...)
   - Consistent spacing and alignment
   - Grid for readability
   - No top/right spines (clean look)

4. **데이터 표현**
   - Markers for data points
   - Error regions (fill_between)
   - Annotations with boxes
   - Statistical info display
   - Legends with shadows

### 참조 스타일
- Nature/Science journals
- CVPR/ICCV/NeurIPS conferences
- Robotics conferences (ICRA, IROS, CoRL)

---

## 📝 사용 방법

### 1. 마크다운에 삽입
```markdown
![Figure Title](visualizations/Q1_context_vector_analysis.png)

**Figure 1**: Description
- **(A)** Panel A description
- **(B)** Panel B description
```

### 2. LaTeX 논문에 삽입
```latex
\begin{figure}[t]
  \centering
  \includegraphics[width=\linewidth]{visualizations/Q1_context_vector_analysis.png}
  \caption{Context Vector Analysis. (A) VLM architecture...}
  \label{fig:context_analysis}
\end{figure}
```

### 3. PowerPoint 프레젠테이션
- PNG 파일을 직접 삽입
- High DPI (300) 로 생성되어 확대해도 선명

---

## 🔄 재생성 방법

### 전체 시각화 재생성
```bash
cd /home/billy/25-1kp/vla
python3 scripts/generate_paper_visualizations.py
python3 scripts/generate_q2_visualization.py
```

### 개별 수정
- 스크립트 수정 후 해당 함수만 실행
- 예: Q3만 수정하려면 `create_q3_balance_comparison()` 수정

---

## 📊 통계

| 시각화 | 파일 크기 | 패널 수 | 차트 유형 |
|:---|---:|---:|:---|
| Q1 | 578 KB | 3 | Architecture, Histogram, Scatter |
| Q2 | 766 KB | 6 | Time series, Histogram, Scatter, Table |
| Q3 | 671 KB | 5 | Line, Stacked bar, Bar, Scatter |
| Q4 | 175 KB | 2 | Diagram, Architecture |
| Q5 | 353 KB | 3 | Pipeline, Bar, Timeline |
| **합계** | **2.5 MB** | **19** | **12 types** |

---

## ✅ 체크리스트

- [x] Q1: Context Vector 분석
- [x] Q2: Velocity Output 검증
- [x] Q3: 균형 데이터 효과
- [x] Q4: 7DOF→2DOF 변환
- [x] Q5: 추론 시나리오
- [x] 모든 리포트에 이미지 삽입
- [x] 고해상도 (300 DPI)
- [x] 논문 스타일 준수
- [x] 통계치 표시
- [x] 범례 및 주석

---

**Status**: ✅ All visualizations complete and integrated!  
**Quality**: Paper-ready, publication-quality figures  
**Updated**: 2025-12-04 16:30
