# Plan: 추론 모드 모델 선택 (exp49~54)

**작성일**: 2026-05-22  
**상태**: 승인 대기

---

## 현재 구조 문제

- `VLA_MODEL=exp49` 환경변수로만 모델 고정 → 런타임 전환 불가
- `EXP_MODES`에 exp49만 있음, 나머지 exp 전환 UI 없음
- `/config` 엔드포인트가 speed_scaling/skip_n만 처리, 모델 전환 없음

---

## 변경 범위

### 1. `proxy_inference_server.py`

#### 1-a. `_GOAL_NAV_WEIGHTS` 에 exp52 추가

```python
_GOAL_NAV_WEIGHTS: dict[str, Path] = {
    "exp46": ROOT / "runs/v5_nav/mlp/exp46/exp46_mlp.pt",
    "exp49": ROOT / "runs/v5_nav/mlp/exp49/exp49_mlp.pt",
    "exp50": ROOT / "runs/v5_nav/mlp/exp50/exp50_mlp.pt",
    "exp51": ROOT / "runs/v5_nav/mlp/exp51/exp51_mlp.pt",
    "exp52": ROOT / "runs/v5_nav/mlp/exp52/exp52_mlp.pt",  # 추가 (lang_vis=2048)
}
```

#### 1-b. 싱글턴 → per-model 캐시

```python
# 기존
goal_nav_instance: Optional[GoalNavInferenceModel] = None

# 변경
_goal_nav_cache: dict[str, GoalNavInferenceModel] = {}
_active_goal_nav_model: str = os.getenv("VLA_MODEL", "exp49")
```

#### 1-c. `_get_goal_nav_model()` 수정 — 캐시 키로 per-model 관리

```python
def _get_goal_nav_model(model_name: str, refresh: bool = False) -> GoalNavInferenceModel:
    global _goal_nav_cache, _active_goal_nav_model
    if refresh:
        _goal_nav_cache.pop(model_name, None)  # 해당 모델만 캐시 제거
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    if model_name not in _goal_nav_cache:
        override = os.getenv("VLA_GOAL_NAV_WEIGHTS_PATH")
        weights_path = Path(override) if override else _GOAL_NAV_WEIGHTS[model_name]
        grounding_model_path = Path(os.getenv("VLA_GROUNDING_MODEL_PATH", str(DEFAULT_GROUNDING_MODEL)))
        device = resolve_device(os.getenv("VLA_GOAL_NAV_DEVICE", "auto"))
        grounding_device = resolve_device(os.getenv("VLA_PROXY_GROUNDING_DEVICE", "auto"))
        _goal_nav_cache[model_name] = GoalNavInferenceModel(
            weights_path=weights_path,
            grounding_model_path=grounding_model_path,
            grounding_device=grounding_device,
            device=device,
        )
    _active_goal_nav_model = model_name
    return _goal_nav_cache[model_name]
```

#### 1-d. `get_model()` 수정

```python
def get_model(refresh: bool = False):
    if _active_goal_nav_model in _GOAL_NAV_WEIGHTS:
        return _get_goal_nav_model(_active_goal_nav_model, refresh)
    return _get_proxy_model(refresh)
```

#### 1-e. `ConfigRequest` 에 `model` 필드 추가

```python
class ConfigRequest(BaseModel):
    speed_scaling: Optional[bool] = None
    grounding_skip_n: Optional[int] = None
    smooth_enabled: Optional[bool] = None
    smooth_alpha_xy: Optional[float] = None
    smooth_alpha_az: Optional[float] = None
    model: Optional[str] = None  # 추가: "exp49" | "exp50" | "exp51" | "exp52"
```

#### 1-f. `/config` 엔드포인트 — model 전환 처리

```python
@app.post("/config")
async def set_config(request: ConfigRequest, ...) -> dict:
    # 모델 전환 먼저 처리
    if request.model is not None:
        if request.model not in _GOAL_NAV_WEIGHTS:
            return {"status": "error", "reason": f"Unknown model: {request.model}"}
        _get_goal_nav_model(request.model)  # 전환 + 캐시 확보
    
    model = get_model()
    if isinstance(model, GoalNavInferenceModel):
        cfg = model.set_config(
            speed_scaling=request.speed_scaling,
            grounding_skip_n=request.grounding_skip_n,
            smooth_enabled=request.smooth_enabled,
            smooth_alpha_xy=request.smooth_alpha_xy,
            smooth_alpha_az=request.smooth_alpha_az,
        )
        cfg["active_model"] = _active_goal_nav_model
        return {"status": "success", "config": cfg}
    return {"status": "skipped", "reason": "Not a GoalNavInferenceModel"}
```

> exp52 (d_in=2083, lang_vis) 로드는 되지만 feature dim 불일치로 predict 실패 — 추후 별도 GroundingBackend 확장 필요. 선택 시 UI 경고 표시.

---

### 2. `gradio_inference_dashboard.py`

#### 2-a. `EXP_MODES` 확장

```python
EXP_MODES = {
    "GoalNav-fixed (Exp49, 고정속도)": {
        "instruction": GOAL_NAV_PRESETS[0],
        "backend_mode": "GoalNav (exp49)",
        "model": "exp49",
        "speed_scaling": False,
        "grounding_skip_n": 3,
        "desc": "기본 GoalNav — 96.4% val acc",
    },
    "GoalNav-scaled (Exp49, 거리비례속도)": {
        ...
        "model": "exp49",
    },
    "GoalNav (Exp50, flip-aug)": {
        "instruction": GOAL_NAV_PRESETS[0],
        "backend_mode": "GoalNav (exp50)",
        "model": "exp50",
        "speed_scaling": False,
        "grounding_skip_n": 3,
        "desc": "flip augmentation 2x — 92.0% val acc",
    },
    "GoalNav (Exp51, crop-aug)": {
        "instruction": GOAL_NAV_PRESETS[0],
        "backend_mode": "GoalNav (exp51)",
        "model": "exp51",
        "speed_scaling": False,
        "grounding_skip_n": 3,
        "desc": "crop augmentation 4x — 93.4% val acc",
    },
    "GoalNav (Exp52, lang+vis) ⚠️": {
        "instruction": GOAL_NAV_PRESETS[0],
        "backend_mode": "GoalNav (exp52)",
        "model": "exp52",
        "speed_scaling": False,
        "grounding_skip_n": 3,
        "desc": "⚠️ lang+vis 2048-dim — 실시간 추출 미지원, 실험적",
    },
    "PathType-fixed (Exp47, 고정속도)": {
        ...
        "model": None,  # proxy model, GoalNav 아님
    },
}
```

#### 2-b. `ApiInferenceBackend.set_config()` 에 model 추가

```python
def set_config(self, speed_scaling, grounding_skip_n, model=None, ...) -> dict:
    payload = {"speed_scaling": speed_scaling, "grounding_skip_n": grounding_skip_n}
    if model is not None:
        payload["model"] = model
    return self._post("/config", payload)
```

#### 2-c. `on_exp_mode_change()` 에서 model 전달

```python
def on_exp_mode_change(mode_name, api_url, backend_mode):
    cfg = EXP_MODES.get(mode_name, ...)
    model_key = cfg.get("model")
    if backend_mode == "API Server":
        result = ApiInferenceBackend(api_url).set_config(
            speed_scaling=cfg["speed_scaling"],
            grounding_skip_n=cfg["grounding_skip_n"],
            model=model_key,          # 추가
        )
        cfg_status = f"✅ 적용: model={model_key}, ..."
```

#### 2-d. `exp_mode` Dropdown에 desc 표시 (선택적)

현재 Dropdown은 key 문자열만 표시 → desc는 `exp_config_status` textbox에 표시.

```python
def on_exp_mode_change(...):
    ...
    desc = cfg.get("desc", "")
    cfg_status = f"✅ 적용: model={model_key} | {desc}" if desc else cfg_status
```

---

## 수정 파일 요약

| 파일 | 변경 | 크기 |
|------|------|------|
| `proxy_inference_server.py` | goal_nav_cache, ConfigRequest, /config, get_model | +30줄 수정 |
| `gradio_inference_dashboard.py` | EXP_MODES 4항목 추가, set_config model 파라미터, on_exp_mode_change | +20줄 |

---

## exp52 주의

- weights 로드는 가능 (GoalNavInferenceModel이 d_in=2083 자동 인식)
- **predict 호출 시 feature dim 불일치로 실패** (GroundingBackend → vis_feat 1024 vs 필요 2048)
- 선택 가능하지만 실제 추론 불가 — UI에 ⚠️ 표시로 구분

## exp53/54 제외

- 별도 inference class 필요 → 별도 계획 수립 후 추가

---

## 완료 체크리스트

- [x] proxy_inference_server.py: `_goal_nav_cache` + `_active_goal_nav_model` 전환
- [x] proxy_inference_server.py: `_get_goal_nav_model()` per-model 캐시
- [x] proxy_inference_server.py: `get_model()` 수정
- [x] proxy_inference_server.py: `ConfigRequest` model 필드 추가
- [x] proxy_inference_server.py: `/config` model 전환 처리
- [x] proxy_inference_server.py: `_GOAL_NAV_WEIGHTS` exp52 추가
- [x] gradio_inference_dashboard.py: `EXP_MODES` exp50/51/52 추가
- [x] gradio_inference_dashboard.py: `set_config()` model 파라미터
- [x] gradio_inference_dashboard.py: `on_exp_mode_change()` model 전달
