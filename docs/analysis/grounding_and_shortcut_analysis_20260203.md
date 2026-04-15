# Mobile VLA Technical Analysis: Grounding and Shortcut Learning
**Date**: 2026-02-03
**Target Task**: Basket Navigation (Left/Right)

## 1. 개요 (Overview)
본 문서는 Mobile VLA의 'Basket Navigation' 작업에서 발생하는 **Hallucination(환각)** 및 **Instruction Grounding(지시어 대응 능력)** 문제를 정밀 분석합니다. 특히, 학습 시 높은 정확도가 실성능으로 이어지지 않는 원인을 규명하고 향후 전략을 수립합니다.

## 2. 실험 비교 분석 (Experimental Comparison)

| Metric | Phase 1: Frozen Baseline | Phase 2: Weighted Classification | Phase 3: Normalized No-Suffix |
| :--- | :--- | :--- | :--- |
| **Normalization** | raw [0, 1] | raw [0, 1] | **CLIP Normalized** (Fix) |
| **Instruction** | suffix added (cheat) | suffix added (cheat) | **Base Instruction only** |
| **Loss Function** | CrossEntropy | **Weighted** CrossEntropy | Weighted CrossEntropy |
| **Val Accuracy** | ~85% | ~99% (Overfitted) | ~30% -> ~99% (Overfitted) |
| **API Test Success**| Low (~20%) | Low (~22%) | **Very Low (~12%)** |
| **Hallucination** | High (Moving straight) | High (Left bias) | High (Text-dependency) |
| **Grounding** | Failed | Failed | **Failed (Root Cause Found)** |

## 3. 핵심 발견 (Key Findings)

### A. 데이터 정규화 불일치 (Normalization Mismatch)
- **발견**: Kosmos-2 백본은 CLIP (Mean 0, Std 1) 방식으로 학습되었으나, 기존 학습 코드는 이미지를 `[0, 1]` 범위로만 입력했습니다.
- **결과**: 추론 시 (API 서버)에는 정규화된 이미지가 입력되어 모델이 학습 시와 다른 특징(Feature Map)을 생성하여 오작동했습니다. (Normalization Fix로 해결)

### B. 문자열 지찰 학습 (Textual Shortcut Learning) - **치명적**
- **발견**: 학습 데이터셋에 `, sliding left`와 같은 액션 정보를 지시어에 포함함으로써 모델이 이미지를 보지 않고 텍스트만 읽어 정답을 맞히는 현상을 발견했습니다.
- **증거**: "Fly to the moon"과 같은 의미 없는 지시어에도 모델이 텍스트 빈도에 따른 특정 액션을 고수함.
- **결론**: Frozen VLM 백본 상태에서는 시각 특징이 Policy Head로 충분히 전달되지 않아, 모델이 가장 쉬운 길(텍스트 정답지 읽기)을 택한 것입니다.

## 4. 향후 전략: "다리 연결(Bridge Connection)"
LoRA Fine-tuning은 강력하지만 자원을 많이 소모합니다. 따라서 LoRA 이전에 ** modality 간의 연결 고리**를 강화하는 설정을 우선 시도합니다.

### 추천 전략: **Projector & Resampler Unfreeze**
- **논리**: VLM 백본 전체는 동결하되, 비전 특징을 텍스트 공간으로 변환해주는 `Projector` 레이어만 학습 모드로 전환합니다.
- **기대 효과**: 비전 정보(왼쪽의 화분 등)가 텍스트 명령과 동일한 공간에서 해석되어 Policy Head에 전달됨으로써 Grounding 성능이 비약적으로 향상될 것입니다.

## 5. 결론 (Conclusion)
단순한 Loss 가중치나 Head 층을 늘리는 것만으로는 "이미지를 보고 이해하는 능력"을 키울 수 없습니다. **Modalities 간의 통로(Projector)**를 열어주는 것이 Hallucination 해결의 핵심 열쇠입니다.

---
**Repository Context**:
- Current Config: `Mobile_VLA/configs/mobile_vla_basket_left_classification_weighted.json`
- Latest Script: `scripts/train/active/train_basket_left_classification_weighted.sh`
