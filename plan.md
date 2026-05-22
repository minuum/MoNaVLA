# Plan: 모션 스무딩 A+B (inference + control)

**작성일**: 2026-05-22  
**상태**: 승인 대기

---

## 문제 정의

현재 vla-inference-gradio 흐름에서 로봇 움직임이 뚝뚝 끊기는 이유 2가지:

1. **액션 점프 (inter-step)**: 매 스텝마다 8-class classifier가 완전히 다른 벡터를 출력  
   예: `FORWARD→[1.15,0,0]` → `ROT_L→[0,0,0.8]` → 즉각 방향 전환  
2. **Bang-Bang 실행 (intra-step)**: 0.4초간 최대 속도로 이동 후 즉시 STOP. 관성 무시.

---

## Option A — proxy_inference_server.py: EMA Smoothing

**대상 클래스**: `GoalNavInferenceModel` (line 849~)  
**핵심**: speed_scale 적용 후, 반환 전에 이전 액션과 EMA 블렌딩

### A-1. `__init__()` 초기화 추가

```python
# 기존: line 876 speed_scaling_enabled 아래에 추가
self.smooth_enabled: bool = os.getenv("VLA_SMOOTH", "1") != "0"
self.smooth_alpha_xy: float = float(os.getenv("VLA_SMOOTH_ALPHA_XY", "0.65"))
self.smooth_alpha_az: float = float(os.getenv("VLA_SMOOTH_ALPHA_AZ", "0.80"))
self.prev_action_3d: list[float] = [0.0, 0.0, 0.0]
```

**alpha 설계 의도**:
- `lx, ly (alpha=0.65)`: 현재 65% + 이전 35% → 직진/횡이동 전환 부드럽게
- `az (alpha=0.80)`: 현재 80% + 이전 20% → 회전은 더 빠르게 반응 (방향 수정 지연 방지)

### A-2. `reset()` 에 prev 초기화 추가

```python
# 기존 reset() 끝에 추가
self.prev_action_3d = [0.0, 0.0, 0.0]
```

### A-3. `predict()` — speed_scale 블록 이후, return 직전에 EMA 적용

```python
# 현재 line 1015 (self.inference_count += 1) 바로 위에 삽입
if self.smooth_enabled and self.inference_count > 0:
    p = self.prev_action_3d
    scaled_3d = [
        self.smooth_alpha_xy * scaled_3d[0] + (1 - self.smooth_alpha_xy) * p[0],
        self.smooth_alpha_xy * scaled_3d[1] + (1 - self.smooth_alpha_xy) * p[1],
        self.smooth_alpha_az * scaled_3d[2] + (1 - self.smooth_alpha_az) * p[2],
    ]
    scaled_2d = [scaled_3d[0], scaled_3d[1]]

self.prev_action_3d = list(scaled_3d)
```

> ⚠️ `inference_count`는 line 1015에서 증가하므로, 첫 스텝은 `count == 0` → EMA 스킵 (초기 prev=[0,0,0]과 블렌딩 방지)

### A-4. `set_config()` 에 smooth 토글 추가

```python
# 기존 파라미터 옆에 추가
def set_config(
    self,
    speed_scaling: Optional[bool] = None,
    grounding_skip_n: Optional[int] = None,
    smooth_enabled: Optional[bool] = None,       # 추가
    smooth_alpha_xy: Optional[float] = None,     # 추가
    smooth_alpha_az: Optional[float] = None,     # 추가
) -> dict:
    ...
    if smooth_enabled is not None:
        self.smooth_enabled = smooth_enabled
    if smooth_alpha_xy is not None:
        self.smooth_alpha_xy = max(0.0, min(1.0, smooth_alpha_xy))
    if smooth_alpha_az is not None:
        self.smooth_alpha_az = max(0.0, min(1.0, smooth_alpha_az))
    return {
        ...,
        "smooth_enabled": self.smooth_enabled,
        "smooth_alpha_xy": self.smooth_alpha_xy,
        "smooth_alpha_az": self.smooth_alpha_az,
    }
```

### A-5. return dict에 디버그 필드 추가

```python
# 기존 return dict에 추가
"smooth_applied": self.smooth_enabled and self.inference_count > 0,
"smooth_alpha_xy": self.smooth_alpha_xy,
"smooth_alpha_az": self.smooth_alpha_az,
```

---

## Option B — vla_control_utils.py: Soft Ramp-Up

**대상 메서드**: `VLAControlManager` 클래스에 `move_and_stop_ramped()` 추가  
**핵심**: 이동 시작 시 50ms 동안 속도를 3단계로 점진 증가, 이후 잔여 시간 풀스피드

### B-1. `move_and_stop_ramped()` 메서드 추가

```python
def move_and_stop_ramped(self, lx, ly, az, source="ramp_mode"):
    """Soft ramp-up (50ms, 3-step) then full speed for remaining duration."""
    with self.movement_lock:
        if self.movement_timer:
            self.movement_timer.cancel()

        self.current_action = {"lx": lx, "ly": ly, "az": az}

        ramp_dur = 0.05          # 50ms ramp-up
        ramp_steps = 3
        step_dur = ramp_dur / ramp_steps   # ~16.7ms per step

        # Soft ramp-up: 33% → 67% → 100%
        for i in range(1, ramp_steps + 1):
            scale = i / ramp_steps
            self.publish_and_move(
                lx * scale, ly * scale, az * scale,
                source=f"{source}_ramp{i}"
            )
            time.sleep(step_dur)

        # Full speed for remaining duration
        log_msg = self.publish_and_move(lx, ly, az, source=source)

        remaining = self.move_duration - ramp_dur   # 0.35s
        def _timed_stop():
            self.robust_stop(source=f"{source}_autostop")

        self.movement_timer = threading.Timer(remaining, _timed_stop)
        self.movement_timer.daemon = True
        self.movement_timer.start()

        return log_msg
```

**타이밍 다이어그램**:
```
t=0.000  publish(33%)   ← 시작
t=0.017  publish(67%)
t=0.033  publish(100%)  ← 풀스피드 시작
t=0.050  publish(100%)  ← full-speed command (timer 기준점)
t=0.400  STOP           ← 자동 정지
```

> ⚠️ `movement_lock` 내에서 동기 ramp 실행 (50ms) → 다음 호출이 lock 대기하므로 동시 실행 없음  
> ⚠️ `publish_and_move`는 lock을 사용하지 않으므로 deadlock 없음

---

## Option C — gradio_inference_dashboard.py: 호출 교체

**대상 라인**: line 628 (`move_and_stop_timed` → `move_and_stop_ramped`)

```python
# 변경 전 (line 628)
state["current_log"] = ros_node.control.move_and_stop_timed(
    float(action[0]),
    float(action[1]),
    float(action[2]) if action.size > 2 else 0.0,
    source="gradio_inference",
)

# 변경 후
state["current_log"] = ros_node.control.move_and_stop_ramped(
    float(action[0]),
    float(action[1]),
    float(action[2]) if action.size > 2 else 0.0,
    source="gradio_inference",
)
```

**수동 드라이브(line 791)는 변경하지 않는다** — 사람이 직접 조작할 때는 즉각 반응이 맞음.

---

## 수정 파일 요약

| 파일 | 변경 위치 | 변경 크기 |
|------|----------|---------|
| `robovlm_nav/serve/proxy_inference_server.py` | `GoalNavInferenceModel.__init__`, `reset`, `predict`, `set_config`, return dict | +20줄 |
| `robovlm_nav/serve/vla_control_utils.py` | `move_and_stop_ramped()` 신규 메서드 | +25줄 |
| `scripts/gradio_inference_dashboard.py` | line 628 메서드명 교체 | 1줄 |

---

## 트레이드오프

| 항목 | 이득 | 리스크 |
|------|------|--------|
| A: EMA lx/ly | FORWARD↔횡이동 전환 부드러움 | 방향 전환 0.35s 지연 |
| A: EMA az | 회전 지연 최소화 | alpha 0.80 충분한지 실환경 확인 필요 |
| B: Ramp | 하드웨어 충격 감소 | 유효 이동시간 0.4→0.35s 단축 (-12.5%) |
| 둘 다 OFF 가능 | `VLA_SMOOTH=0`, `move_and_stop_timed` 유지 | 기존 동작 그대로 |

---

## 완료 체크리스트

- [x] proxy_inference_server.py `__init__` smooth 변수 추가
- [x] proxy_inference_server.py `reset()` prev_action 초기화
- [x] proxy_inference_server.py `predict()` EMA 블록 삽입
- [x] proxy_inference_server.py `set_config()` smooth 파라미터 노출
- [x] proxy_inference_server.py return dict debug 필드 추가
- [x] vla_control_utils.py `move_and_stop_ramped()` 메서드 추가
- [x] gradio_inference_dashboard.py line 628 메서드명 교체
