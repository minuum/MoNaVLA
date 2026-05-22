# Plan: Exp53 CLIP-LoRA Inference Pipeline

**작성일**: 2026-05-22  
**상태**: 승인 대기

---

## 리서치 요약

exp53 체크포인트 분석:
- `runs/v5_nav/mlp/exp53_clip_lora.pt` → MLP만 저장, 키: `{'mlp', 'val_acc'}`
  - `ckpt['mlp']` 는 GoalNavMLP 전체 state_dict (`net.0.weight` 같이 `net.` 접두사 있음)
  - d_in=1059 (exp49와 동일: bbox32 + vis1024 + goal3)
  - 별도 `d_in` 키 없음 → weight shape에서 추론
- `runs/v5_nav/mlp/clip_lora_adapter/` → PEFT LoRA adapter
  - base_model_class: `Kosmos2VisionModel`
  - target_modules: `q_proj`, `v_proj`
  - layers_to_transform: 16~23 (마지막 8 레이어)
  - r=16, lora_alpha=32

exp49 대비 달라지는 건 **vision_model에 LoRA 적용 하나뿐**. 나머지 파이프라인(grounding, feature build, MLP) 동일.

---

## 변경 범위

### 1. `proxy_inference_server.py`

#### 1-a. `_GOAL_NAV_WEIGHTS`에 exp53 추가

```python
_GOAL_NAV_WEIGHTS: dict[str, Path] = {
    ...
    "exp53": ROOT / "runs" / "v5_nav" / "mlp" / "exp53_clip_lora.pt",
}
```

#### 1-b. `_GOAL_NAV_LORA_ADAPTERS` 신규 추가

```python
_GOAL_NAV_LORA_ADAPTERS: dict[str, Path] = {
    "exp53": ROOT / "runs" / "v5_nav" / "mlp" / "clip_lora_adapter",
}
```

#### 1-c. `GroundingBackend.__init__()` — vis LoRA 파라미터 추가

```python
def __init__(
    self,
    model_path: Path,
    device: torch.device,
    vis_lora_adapter_path: Optional[Path] = None,  # 추가
):
    ...
    # 기존 grounding LoRA 블록 아래에 추가:
    if vis_lora_adapter_path is not None and vis_lora_adapter_path.exists():
        try:
            from peft import PeftModel
            self.model.vision_model = PeftModel.from_pretrained(
                self.model.vision_model, str(vis_lora_adapter_path)
            ).eval()
            logger.info("Loaded vis LoRA adapter from %s", vis_lora_adapter_path)
        except Exception as e:
            logger.warning("Failed to load vis LoRA adapter (%s); using base", e)
```

#### 1-d. `GoalNavInferenceModel.__init__()` — lora_adapter_path 파라미터 추가

```python
def __init__(
    self,
    weights_path: Path,
    grounding_model_path: Path,
    grounding_device: torch.device,
    device: torch.device,
    lora_adapter_path: Optional[Path] = None,  # 추가
):
    ...
    self.grounder = GroundingBackend(
        grounding_model_path, grounding_device,
        vis_lora_adapter_path=lora_adapter_path,  # 추가
    )
```

#### 1-e. `GoalNavInferenceModel._load()` — exp53 format 처리

exp53 체크포인트는 `d_in`, `model_state_dict` 키가 없고 `mlp`(full state_dict), `val_acc` 만 있음.

```python
def _load(self, weights_path: Path) -> None:
    ckpt = torch.load(weights_path, map_location="cpu", weights_only=False)

    if "mlp" in ckpt and "model_state_dict" not in ckpt:
        # exp53 format
        state = ckpt["mlp"]
        d_in = state["net.0.weight"].shape[1]
        self.window = 8
        self.goal_dim = d_in - 32 - VIS_DIM  # 1059-32-1024=3
        net = GoalNavMLP(d_in=d_in)
        net.load_state_dict(state)  # net. 접두사 포함
        overall_acc = ckpt.get("val_acc")
    else:
        # exp49/50/51 format
        d_in = int(ckpt["d_in"])
        self.window = int(ckpt.get("window", 8))
        self.goal_dim = int(ckpt.get("goal_dim") or 0)
        net = GoalNavMLP(d_in=d_in)
        net.net.load_state_dict(ckpt["model_state_dict"])
        overall_acc = ckpt.get("overall_acc")

    self.model = net.to(self.device).eval()
    self.model_info = {
        "source": "loaded",
        "weights_path": str(weights_path),
        "d_in": d_in,
        "window": self.window,
        "goal_dim": self.goal_dim,
        "overall_acc": overall_acc,
    }
    logger.info(
        "Loaded GoalNav MLP from %s (d_in=%d, window=%d, goal_dim=%d, acc=%.4f)",
        weights_path, d_in, self.window, self.goal_dim, overall_acc or 0.0,
    )
```

#### 1-f. `_get_goal_nav_model()` — lora_path 전달

```python
lora_path = _GOAL_NAV_LORA_ADAPTERS.get(model_name)
_goal_nav_cache[model_name] = GoalNavInferenceModel(
    weights_path=weights_path,
    grounding_model_path=grounding_model_path,
    grounding_device=grounding_device,
    device=device,
    lora_adapter_path=lora_path,
)
```

---

### 2. `gradio_inference_dashboard.py`

`EXP_MODES`에 exp53 항목 추가 (PathType 앞에):

```python
"GoalNav (Exp53, CLIP-LoRA)": {
    "instruction": GOAL_NAV_PRESETS[0],
    "backend_mode": "GoalNav (exp53)",
    "model": "exp53",
    "speed_scaling": False,
    "grounding_skip_n": 3,
    "desc": "CLIP LoRA fine-tuned vision encoder — 94.7% val acc",
},
```

---

## 수정 파일 요약

| 파일 | 변경 | 크기 |
|------|------|------|
| `proxy_inference_server.py` | _GOAL_NAV_WEIGHTS exp53, _GOAL_NAV_LORA_ADAPTERS 신규, GroundingBackend vis LoRA, GoalNavInferenceModel lora 파라미터, _load() exp53 format, _get_goal_nav_model() lora 전달 | +35줄 |
| `gradio_inference_dashboard.py` | EXP_MODES exp53 항목 추가 | +8줄 |

---

## 완료 체크리스트

- [x] proxy_inference_server.py: `_GOAL_NAV_WEIGHTS` exp53 추가
- [x] proxy_inference_server.py: `_GOAL_NAV_LORA_ADAPTERS` 신규
- [x] proxy_inference_server.py: `GroundingBackend` vis_lora_adapter_path 파라미터
- [x] proxy_inference_server.py: `GoalNavInferenceModel` lora_adapter_path 파라미터
- [x] proxy_inference_server.py: `_load()` exp53 format 처리
- [x] proxy_inference_server.py: `_get_goal_nav_model()` lora_path 전달
- [x] gradio_inference_dashboard.py: `EXP_MODES` exp53 추가
