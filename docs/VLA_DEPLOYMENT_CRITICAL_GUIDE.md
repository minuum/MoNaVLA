# 🚨 VLA 모델 배포 및 추론 통합 가이드 (Critical Guide)

본 문서는 **Mobile VLA (V2, EXP-17 등)** 모델을 로봇 추론 서버(Jetson/Edge)에 배포할 때 발생하는 **"환각 현상(직진 편향, 정지 불능)"**을 방지하기 위한 핵심 보정 사항을 정리한 기술 문서입니다.

현재 로봇 서버(`inference_server.py`)와 학습된 모델(`api_server_fix.py`) 간의 환경 차이로 인해 모델 성능이 99%에서 0% 가까이 떨어지는 현상이 발생하고 있습니다. 아래 사항들을 **반드시** 반영해야 정상적인 추론이 가능합니다.

---

## 🛑 1. 핵심 원인: 왜 로봇은 "직진"만 하는가? (Hallucination Analysis)

현재 로봇 서버 로그(`inference_server.py`) 분석 결과, 두 가지 치명적인 설정 오류가 확인되었습니다.

1.  **강제 양자화 (INT8 Quantization)**: 
    *   V2 모델은 `BF16` 또는 `FP16`으로 정밀하게 학습되었습니다.
    *   이를 보정(Calibration) 없이 `BitsAndBytes INT8`로 강제 로딩하면 가중치 정보가 손실되어 모델이 가장 "평균적인 안전한 값(직진 또는 정지)"만 출력하는 **Mode Collapse**에 빠집니다.
2.  **시계열 맥락 부재 (Missing Temporal Context)**:
    *   본 VLA 모델은 **Video VLM** 기반으로, 과거 **Window Size (6~12 프레임)** 동안의 변화를 보고 속도와 방향을 결정합니다.
    *   현재 로봇 서버는 **단일 프레임(Single Frame)**만 입력하고 있어, 모델은 "정지 사진"을 보고 움직임을 예측해야 하는 불가능한 상황에 놓여 있습니다.

---

## ✅ 2. 필수 수정 사항 (Mandatory Fixes)

다음 3가지 사항은 **선택이 아닌 필수**입니다. 하나라도 누락될 경우 모델은 정상 동작하지 않습니다.

### ① 정밀도 원복 (Disable INT8, Use FP16/BF16)
*   **현상**: `✅ Model loaded with BitsAndBytes INT8` (로그 확인됨)
*   **수정**: `BitsAndBytesConfig`를 제거하고, 표준 Torch 로딩을 사용하십시오.
*   **코드 예시**:
    ```python
    # ❌ (Don't) DO NOT USE INT8
    # bnb_config = BitsAndBytesConfig(load_in_8bit=True, ...) 
    
    # ✅ (Do) Use BFloat16 or Float16
    model = MobileVLATrainer(config)
    model.load_state_dict(checkpoint['state_dict'], strict=False)
    model.to('cuda')
    
    if torch.cuda.is_bf16_supported():
        model = model.bfloat16()  # Ampere(Orin) 이상 권장
    else:
        model = model.half()      # 구형 GPU
    ```

### ② 히스토리 버퍼 구현 (Implement Window Buffer)
*   **현상**: 입력 텐서 shape가 `(1, 1, 3, 224, 224)` (단일 프레임)
*   **수정**: 학습 설정(`config.json`)의 `window_size` (보통 8~12)에 맞춰 **FIFO Queue**를 구현해야 합니다.
*   **로직**:
    1.  새 이미지가 들어오면 큐에 추가 (`append`).
    2.  큐가 꽉 차면 가장 오래된 프레임 제거 (`pop(0)`).
    3.  **중요**: 큐가 비어있는 초기 단계(Cold Start)에서는 **첫 프레임을 복제**하여 큐를 채웁니다 (Padding).
*   **코드 예시**:
    ```python
    # 초기화
    self.history = []
    self.window_size = config.get('window_size', 8)
    
    # 추론 루프 내
    self.history.append(current_image_tensor)
    if len(self.history) > self.window_size:
        self.history.pop(0)
        
    # 패딩 (Cold Start)
    input_frames = list(self.history)
    while len(input_frames) < self.window_size:
        input_frames.insert(0, input_frames[0]) # 첫 프레임 복제
        
    # 모델 입력: (1, T, 3, 224, 224)
    model_input = torch.stack(input_frames).unsqueeze(0)
    ```

### ③ 프롬프트 정규화 (Prompt Engineering)
*   **현상**: 단순 명령어("go left")만 입력 시 성능 저하 가능성.
*   **수정**: 학습 데이터와 정확히 일치하는 포맷을 사용해야 합니다. V2 모델은 **Grounding Tag**와 **Prefix**에 민감합니다.
*   **포맷**:
    ```python
    # 학습된 포맷
    full_prompt = f"<grounding>An image of a robot {instruction}"
    ```

---

## 🚀 3. 권장 설정 (Recommended Settings for V2)

### 3.1. Instruction Mapping (Strong Prompts)
V2-12/17 모델은 특정 단어에 더 강하게 반응합니다. 로봇 서버에서 입력을 변환해주면 더 좋습니다.
| 입력 (User) | 변환 (Model Input) | 비고 |
| :--- | :--- | :--- |
| "left" | "Steer left to the **brown pot**" | 색상 정보(brown pot)가 핵심 |
| "right" | "Steer right to the **brown pot**" | 타겟 명시 |
| "stop" | "Stop the robot" | 명확한 정지 명령 |

### 3.2. Action Post-processing (Snap-to-Grid)
VLA 모델은 연속적인 값을 출력하므로, 미세한 노이즈로 인해 로봇이 떨릴 수 있습니다.
*   **Snap Threshold (0.8)**: 출력값이 매우 작거나 모호할 때 과감히 0으로 죽이거나 1로 올리는 필터링이 필요할 수 있습니다 (현재 V2 모델은 성능이 좋아 필수는 아니지만 안전장치로 권장).

---

## 📊 요약 Checklist

로봇 서버 담당자에게 전달할 체크리스트입니다.

- [ ] **[Critical]** `BitsAndBytes` INT8 로딩 코드가 제거되었는가? (FP16/BF16 사용)
- [ ] **[Critical]** `image_history` 버퍼가 구현되어 입력 텐서의 `Seq_Len`이 `window_size`(예: 8)와 일치하는가?
- [ ] **[Important]** Prompt가 `<grounding>An image of a robot ...` 형식으로 전처리되는가?
- [ ] **[Check]** 출력 Action의 `Linear X`, `Linear Y` (또는 Angular Z) 매핑이 로봇의 좌표계와 일치하는가?

위 사항들이 반영되지 않으면 V2 모델은 **무조건** 제 성능을 내지 못합니다.
