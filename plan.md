# Plan: 5/15 미팅 결정 — CLIP Vision LoRA + 정량 검증
작성일: 2026-05-15

---

## 1. 핵심 과학적 질문 (from 미팅)

> **"3개 트라젝토리만으로 왜 됐나? LEFT를 외운 건가, 박스를 본 건가?"**

현재 상태:
- 9 에피소드 (좌/중앙/우 × 3개), ~150 샘플
- 3번 테스트 → 3번 성공
- 인스트럭션: `"basket under left"` 등 방향어 포함

**문제:** 모델이 아래 중 어느 이유로 성공하는지 불명확
- (A) `"left"` 텍스트 패턴 암기 → left 액션 출력
- (B) CLIP 비전이 박스 위치를 시각적으로 인식 → 방향 결정

---

## 2. 교수님 지시 사항 (5/15 미팅)

```
1. CLIP 비전 인코더 16~24번 레이어에만 LoRA 적용
2. 언어(LM) 쪽은 완전 frozen
3. 데이터: 좌/중앙/우 각 10개 트라젝토리 (조이스틱 비동기 수집)
4. 테스트: "box를 찾아가라" 방향어 없는 프롬프트로도 동작하는지
5. 정량 결과: 각 방향 N번 시도 → N번 성공 테이블
```

**가설:** CLIP high-level 블락(시맨틱 정렬 레이어)에 LoRA를 걸면
박스 객체 인식이 명시적으로 강화되고, 9개가 아닌 30개 트라젝토리로
generalizable한 visual grounding이 가능해진다.

---

## 3. 아키텍처

```
현재 Exp49/Step2 (변경 없음):
  CLIP(frozen) → vision_feat(1024) → MLP → action

신규 (이 플랜):
  CLIP(layers 0-15 frozen, layers 16-23 LoRA) → vision_feat(1024) → MLP → action

핵심 변경: CLIP 마지막 8블락(16~23, 0-indexed)에 LoRA(r=16)
LM 쪽: 완전 frozen (건드리지 않음)
```

**왜 16~24인가:**
- CLIP ViT-L/14의 24블락 중 마지막 8개가 semantic alignment layer
- 이 레이어들이 객체 인식과 언어 정렬에 직접 관여
- Low(0~7), Mid(8~15)는 엣지/텍스처 — 건드릴 이유 없음

---

## 4. 단계별 실행 계획

### Phase 0: 조이스틱 확인 (선행 조건)
- [ ] 조이스틱 박스 동작 여부 확인
- [ ] 비동기 데이터 수집 스크립트와 연결 테스트

### Phase 1: 데이터 수집
- [ ] 방식: 조이스틱 비동기 (기존 고정 격자 방식 → 교체)
- [ ] 목표: 좌 10개 + 중앙 10개 + 우 10개 = **30 트라젝토리**
- [ ] 에피소드당 ~15-20 프레임 → 총 450~600 샘플
- [ ] 인스트럭션 두 가지 준비:
  - 방향어 포함: `"basket under left"` / `"basket in center"` / `"basket under right"`
  - 방향어 없음: `"go to the box"` (테스트케이스용)

### Phase 2: CLIP LoRA 구현
- [ ] `robovlm_nav/models/` 또는 proxy server 내 CLIP 레이어 접근 경로 파악
- [ ] LoRA 적용 대상: `model.vision_model.encoder.layers[16:24]`
  - target modules: `q_proj`, `v_proj` (attention만, r=16, alpha=32)
- [ ] layers 0-15: `requires_grad_(False)` 유지
- [ ] LM 전체: frozen 유지
- [ ] MLP 헤드: 기존 Exp49 구조 재사용 (1024-dim 입력)

### Phase 3: 학습
- [ ] 데이터: 30 트라젝토리 bbox_dataset
- [ ] LoRA 파라미터만 학습, MLP 헤드 같이 학습
- [ ] epochs: 300, AdamW, CosineAnnealing

### Phase 4: 테스트케이스 (정량 결과)

교수님 요구 형식:

| 프롬프트 타입 | 방향 | 시도 횟수 | 성공 횟수 | 성공률 |
|---|---|---|---|---|
| 방향어 포함 | 왼쪽 | 5 | ? | ?% |
| 방향어 포함 | 중앙 | 5 | ? | ?% |
| 방향어 포함 | 오른쪽 | 5 | ? | ?% |
| **방향어 없음** | 왼쪽 | 5 | ? | ?% |
| **방향어 없음** | 중앙 | 5 | ? | ?% |
| **방향어 없음** | 오른쪽 | 5 | ? | ?% |

**판별 기준:**
- 방향어 있을 때 성공 + 방향어 없을 때도 성공 → **박스 시각 인식** 근거
- 방향어 있을 때만 성공 → **텍스트 패턴 암기** 의심
- 방향어 없을 때 무작위 → **언어 의존적**

---

## 5. 코드 변경 범위

| 파일 | 변경 내용 |
|---|---|
| `robovlm_nav/serve/proxy_inference_server.py` | CLIP 16-24 LoRA 로드 지원 |
| `scripts/train_clip_lora_exp53.py` | 신규 학습 스크립트 |
| `configs/bbox_nav_exp53_clip_lora.json` | 실험 config |
| `scripts/test_clip_lora_testcases.py` | 테스트케이스 자동화 |

---

## 6. Exp52와의 관계

Exp52 (Language-Conditioned Visual Features)는 **별도 보존**.
이 플랜(Exp53)과 방향이 다름:

| 항목 | Exp52 | Exp53 (이 플랜) |
|---|---|---|
| 접근 | LM joint forward → image token | CLIP 16-24 LoRA → visual grounding |
| LM 역할 | 이미지 처리에 언어 attention 개입 | 완전 frozen |
| 목표 | True VLA (언어가 시각 변조) | 박스 인식 강화 + 검증 |
| 데이터 | 기존 150 ep | 신규 30 트라젝토리 |

---

## 7. 완료 기준

- [ ] 방향어 없이 `"go to the box"`만으로 좌/중/우 각 5회 중 4회 이상 성공
- [ ] 정량 테이블 완성 (교수님 보고용)
- [ ] 박스 인식 vs 텍스트 암기 판별 근거 제시
