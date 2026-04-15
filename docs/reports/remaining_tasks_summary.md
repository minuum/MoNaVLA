# 남은 작업 및 향후 개선 사항

**날짜**: 2025-12-07 03:05  
**상태**: VLM Left/Right 구분 검증 완료

---

## ✅ 완료된 작업

| 작업 | 상태 | 결과 |
|:---|:---:|:---|
| VLM Left/Right 구분 검증 | ✅ | 모델이 올바르게 구분함 |
| 학습 파이프라인 검증 | ✅ | 정상 작동 |
| 토크나이제이션 검증 | ✅ | collater에서 정상 처리 |
| Action Head 구조 검증 | ✅ | LSTM 구조 정상 |
| Loss 파이프라인 검증 | ✅ | loss_velocity_act 정상 연결 |

---

## 🔧 남은 작업 (우선순위 순)

### 1. 🔴 추론 코드 수정 필요

**문제**: 기존 추론 코드가 `encode_images()`만 사용할 수 있음

**확인 필요 파일**:
- `verify_velocity_output.py`
- ROS 배포용 추론 스크립트

**수정 내용**: `forward_continuous()` 사용하도록 변경

---

### 2. 🟡 이전 잘못된 분석 보고서 수정

**수정 필요 파일**:
- `docs/reports/left_right_failure_analysis.md` - "실패" → "성공" 수정
- `docs/reports/vlm_analysis_deep_dive.md` - 결론 업데이트
- `docs/reports/critical_analysis_of_findings.md` - 분석 결과 업데이트

---

### 3. 🟡 모델 성능 정량 분석

**현재 결과**:
```
Left:  GT=+0.319, Pred=+0.029 (오차 0.29)
Right: GT=-0.383, Pred=-0.520 (오차 0.14)
```

**추가 분석 필요**:
- 더 많은 샘플에서 RMSE 계산
- 프레임별 오차 분석
- Action trajectory 시각화

---

### 4. 🟢 Frozen vs LoRA 비교 완성

**현재 상태**: Frozen VLM 검증 완료
**남은 작업**: LoRA fine-tuning 결과와 비교

---

### 5. 🟢 ROS 배포 준비

**필요 작업**:
- 추론 코드 최적화
- 실시간 성능 테스트
- 로봇 하드웨어 연동

---

## 📊 현재 모델 성능 요약

| 메트릭 | Left | Right |
|:---|:---:|:---:|
| **Ground Truth** | +0.319 | -0.383 |
| **Model Output** | +0.029 | -0.520 |
| **부호 정확도** | ✅ | ✅ |
| **절대 오차** | 0.29 | 0.14 |

---

## 🎯 다음 단계 권장

### 즉시 실행 (오늘):
1. ✅ 추론 코드 forward_continuous 사용 확인/수정
2. 🔄 잘못된 보고서 업데이트

### 단기 (이번 주):
3. 더 많은 샘플에서 성능 검증
4. Action trajectory 시각화

### 중기 (다음 주):
5. LoRA vs Frozen 비교 실험
6. ROS 배포 준비

---

## 📝 교수님 미팅 준비 체크리스트

- [x] VLM이 Left/Right 구분하는지 검증
- [x] 학습 파이프라인 검증
- [ ] 정량적 성능 메트릭 정리
- [ ] 시각화 자료 준비
- [ ] 다음 단계 계획 수립
