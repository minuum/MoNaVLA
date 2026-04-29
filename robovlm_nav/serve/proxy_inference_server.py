"""
FastAPI inference server for Exp19 bbox/proxy navigation.

This is a draft integration layer for the research proxy model:
- online Kosmos-2 grounding
- bbox history + 16x16 grayscale image feature
- Exp19 proxy features
- small MLP classifier

Unlike the ckpt-based Mobile VLA server, this path does not load a drop-in
trainer checkpoint. It either loads a saved proxy MLP weights file or trains
the MLP at startup from the cached bbox dataset.
"""

from __future__ import annotations

import base64
import io
import json
import logging
import os
import secrets
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Optional

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import cv2
import h5py
import numpy as np
import torch
import torch.nn as nn
from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import APIKeyHeader
from PIL import Image
from pydantic import BaseModel

try:
    from transformers import AutoModelForVision2Seq, AutoProcessor
except ImportError as exc:
    raise RuntimeError("transformers is required for proxy_inference_server.py") from exc


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Mobile VLA Exp19 Proxy API", version="0.1.0")

ROOT = Path(project_root)
DATA_DIR = ROOT / "ROS_action" / "mobile_vla_dataset_v5"
DATASET_FILE = ROOT / "docs" / "v5" / "bbox_nav_step1" / "bbox_dataset.json"
DEFAULT_WEIGHTS_PATH = ROOT / "docs" / "v5" / "bbox_nav_exp19_proxy" / "exp19_proxy_mlp.pt"
DEFAULT_GROUNDING_MODEL = ROOT / ".vlms" / "kosmos-2-patch14-224"

API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

NUM_CLASSES = 8
WINDOW = 3
IMG_SIZE = 16
CONSISTENCY_K = 5
CX_TOL = 0.08
AREA_TOL = 0.08
FULLSCREEN_AREA_THRESHOLD = 0.85
GROUNDING_PROMPT = "<grounding>The gray basket is at"
CLASS_NAMES = ["STOP", "FORWARD", "LEFT", "RIGHT", "FWD+L", "FWD+R", "ROT_L", "ROT_R"]
ACTION_2D = {
    0: [0.0, 0.0],
    1: [1.15, 0.0],
    2: [0.0, 1.15],
    3: [0.0, -1.15],
    4: [1.15, 1.15],
    5: [1.15, -1.15],
    6: [0.0, 0.0],
    7: [0.0, 0.0],
}
ACTION_3D = {
    0: [0.0, 0.0, 0.0],
    1: [1.15, 0.0, 0.0],
    2: [0.0, 1.15, 0.0],
    3: [0.0, -1.15, 0.0],
    4: [1.15, 1.15, 0.0],
    5: [1.15, -1.15, 0.0],
    6: [0.0, 0.0, 0.25],
    7: [0.0, 0.0, -0.25],
}

model_instance = None


def get_api_key() -> str:
    api_key = os.getenv("VLA_API_KEY")
    if not api_key:
        api_key = secrets.token_urlsafe(32)
        logger.warning("=" * 60)
        logger.warning("VLA_API_KEY is not set.")
        logger.warning("Generated API key: %s", api_key)
        logger.warning('Export it with: export VLA_API_KEY="%s"', api_key)
        logger.warning("=" * 60)
    return api_key


VALID_API_KEY = get_api_key()


async def verify_api_key(api_key: str = Depends(api_key_header)) -> str:
    if api_key != VALID_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")
    return api_key


class InferenceRequest(BaseModel):
    image: str
    instruction: str


class InferenceResponse(BaseModel):
    action: list[float]
    latency_ms: float
    model_name: str
    strategy: str
    source: str
    buffer_status: dict[str, Any]
    predicted_class: Optional[int] = None
    predicted_label: Optional[str] = None
    action_3d: Optional[list[float]] = None
    bbox: Optional[dict[str, Any]] = None
    grounding_caption: Optional[str] = None
    grounding_latency_ms: Optional[float] = None
    goal_near_proxy: Optional[bool] = None
    instruction_used: bool = False


class ProxyMLP(nn.Module):
    def __init__(self, input_dim: int, num_classes: int = NUM_CLASSES):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, 256),
            nn.ReLU(),
            nn.Dropout(0.25),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, num_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


class GroundingBackend:
    def __init__(self, model_path: Path, device: torch.device):
        if not model_path.exists():
            raise FileNotFoundError(f"Grounding model not found: {model_path}")
        self.model_path = model_path
        self.device = device
        self.processor = AutoProcessor.from_pretrained(str(model_path))
        self.model = AutoModelForVision2Seq.from_pretrained(
            str(model_path),
            torch_dtype=torch.float16 if device.type == "cuda" else torch.float32,
        ).to(device).eval()
        logger.info("Loaded grounding backend from %s on %s", model_path, device)

    def _parse_basket_bbox(self, caption: str, entities: list[Any]) -> Optional[dict[str, Any]]:
        keywords = ("basket", "gray box", "container", "gray")
        candidates = []
        for entity_name, _span, boxes in entities:
            for box in boxes:
                x1, y1, x2, y2 = [float(v) for v in box]
                if max(x1, y1, x2, y2) > 1.5:
                    x1, y1, x2, y2 = x1 / 1000.0, y1 / 1000.0, x2 / 1000.0, y2 / 1000.0
                area = (x2 - x1) * (y2 - y1)
                if area > FULLSCREEN_AREA_THRESHOLD:
                    continue
                candidates.append(
                    {
                        "entity": entity_name,
                        "x1": x1,
                        "y1": y1,
                        "x2": x2,
                        "y2": y2,
                        "cx": (x1 + x2) / 2.0,
                        "cy": (y1 + y2) / 2.0,
                        "area": area,
                        "is_basket": any(k in entity_name.lower() for k in keywords),
                    }
                )

        matched = [b for b in candidates if b["is_basket"]]
        if matched:
            return matched[0]

        caption_lower = caption.lower()
        if "far left" in caption_lower:
            return {"entity": "caption:far_left", "cx": 0.1, "cy": 0.5, "area": 0.05}
        if "far right" in caption_lower:
            return {"entity": "caption:far_right", "cx": 0.9, "cy": 0.5, "area": 0.05}
        if "left" in caption_lower and "right" not in caption_lower:
            return {"entity": "caption:left", "cx": 0.25, "cy": 0.5, "area": 0.05}
        if "right" in caption_lower and "left" not in caption_lower:
            return {"entity": "caption:right", "cx": 0.75, "cy": 0.5, "area": 0.05}
        if "center" in caption_lower:
            return {"entity": "caption:center", "cx": 0.5, "cy": 0.5, "area": 0.05}
        if candidates:
            return candidates[0]
        return None

    def run(self, image_rgb: np.ndarray) -> dict[str, Any]:
        pil_image = Image.fromarray(image_rgb.astype(np.uint8)).convert("RGB")
        inputs = self.processor(text=GROUNDING_PROMPT, images=pil_image, return_tensors="pt")
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        pixel_values = inputs["pixel_values"].to(torch.float16 if self.device.type == "cuda" else torch.float32)

        start = time.time()
        with torch.no_grad():
            generated = self.model.generate(
                pixel_values=pixel_values,
                input_ids=inputs["input_ids"],
                attention_mask=inputs["attention_mask"],
                image_embeds=None,
                image_embeds_position_mask=inputs.get("image_embeds_position_mask"),
                use_cache=True,
                max_new_tokens=64,
            )
        latency_ms = (time.time() - start) * 1000.0

        new_ids = generated[:, inputs["input_ids"].shape[1] :]
        raw = self.processor.batch_decode(new_ids, skip_special_tokens=False)[0]
        caption, entities = self.processor.post_process_generation(raw)
        bbox = self._parse_basket_bbox(caption, entities)
        return {
            "caption": caption,
            "bbox": bbox,
            "latency_ms": latency_ms,
        }


def load_dataset(dataset_path: Path) -> list[dict[str, Any]]:
    if not dataset_path.exists():
        raise FileNotFoundError(f"Dataset file not found: {dataset_path}")
    return json.loads(dataset_path.read_text())


def load_episode_frames(stem: str) -> np.ndarray:
    path = next(DATA_DIR.glob(f"{stem}.h5"))
    with h5py.File(path, "r") as handle:
        if "observations" in handle and "images" in handle["observations"]:
            images = handle["observations"]["images"][:]
        else:
            images = handle["images"][:]
    return images


def frame_to_small_feature(frame_rgb: np.ndarray) -> np.ndarray:
    pil = Image.fromarray(frame_rgb.astype(np.uint8)).convert("L").resize((IMG_SIZE, IMG_SIZE))
    arr = np.asarray(pil, dtype=np.float32) / 255.0
    return arr.reshape(-1)


def recent_bbox_consistency(frames: list[dict[str, Any]], t: int) -> float:
    start = max(0, t - CONSISTENCY_K + 1)
    tail = frames[start : t + 1]
    valid = [frame for frame in tail if frame["has_bbox"]]
    if not valid:
        return 0.0
    if len(valid) == 1:
        return 1.0

    stable_pairs = 0
    total_pairs = 0
    for prev, cur in zip(valid[:-1], valid[1:]):
        total_pairs += 1
        if (
            abs(float(cur["cx"]) - float(prev["cx"])) <= CX_TOL
            and abs(float(cur["area"]) - float(prev["area"])) <= AREA_TOL
        ):
            stable_pairs += 1
    return stable_pairs / max(total_pairs, 1)


def build_proxy_features(frames: list[dict[str, Any]], t: int) -> list[float]:
    cur = frames[t]
    prev = frames[t - 1] if t > 0 else None
    return [
        float(cur["area"]),
        abs(float(cur["cx"]) - 0.5),
        0.0 if prev is None else abs(float(cur["cx"]) - float(prev["cx"])),
        recent_bbox_consistency(frames, t),
    ]


def make_episode_split(dataset: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rng = np.random.default_rng(42)
    by_path = defaultdict(list)
    for idx, episode in enumerate(dataset):
        by_path[episode["path_type"]].append(idx)

    train_idx, test_idx = [], []
    for idxs in by_path.values():
        rng.shuffle(idxs)
        k = max(1, int(len(idxs) * 0.2))
        test_idx.extend(idxs[:k])
        train_idx.extend(idxs[k:])

    return [dataset[i] for i in train_idx], [dataset[i] for i in test_idx]


def goal_near_proxy(frame: dict[str, Any]) -> bool:
    return bool(frame["has_bbox"]) and float(frame["area"]) >= 0.27 and abs(float(frame["cx"]) - 0.5) <= 0.03125


class ProxyInferenceModel:
    def __init__(
        self,
        dataset_file: Path,
        weights_path: Path,
        proxy_device: torch.device,
        grounding_device: torch.device,
        grounding_model_path: Path,
        epochs: int,
        force_retrain: bool,
    ):
        self.dataset_file = dataset_file
        self.weights_path = weights_path
        self.proxy_device = proxy_device
        self.grounding_device = grounding_device
        self.grounding_model_path = grounding_model_path
        self.epochs = epochs
        self.force_retrain = force_retrain
        self.model_name = "exp19_proxy_mlp"
        self.model: Optional[ProxyMLP] = None
        self.model_info: dict[str, Any] = {}
        self.history: list[dict[str, Any]] = []
        self.inference_count = 0

        self.grounder = GroundingBackend(grounding_model_path, grounding_device)
        self._load_or_train()

    def _build_windows(self, dataset: list[dict[str, Any]]) -> tuple[np.ndarray, np.ndarray]:
        features, labels = [], []
        for episode in dataset:
            images = load_episode_frames(episode["episode"])
            frames = episode["frames"]
            img_feats = [frame_to_small_feature(images[f["frame_idx"]]) for f in frames]
            for t in range(len(frames)):
                feat = []
                for k in range(WINDOW):
                    idx = max(0, t - (WINDOW - 1 - k))
                    frame = frames[idx]
                    feat.extend([frame["cx"], frame["cy"], frame["area"], float(frame["has_bbox"])])
                feat.extend(img_feats[t].tolist())
                feat.extend(build_proxy_features(frames, t))
                features.append(feat)
                labels.append(frames[t]["gt_class"])
        return np.asarray(features, dtype=np.float32), np.asarray(labels, dtype=np.int64)

    def _train_model(self) -> tuple[ProxyMLP, dict[str, Any]]:
        dataset = load_dataset(self.dataset_file)
        train_ds, test_ds = make_episode_split(dataset)
        x_train, y_train = self._build_windows(train_ds)
        x_test, y_test = self._build_windows(test_ds)

        model = ProxyMLP(input_dim=x_train.shape[1]).to(self.proxy_device)
        class_counts = np.bincount(y_train, minlength=NUM_CLASSES).astype(np.float32)
        class_counts = np.where(class_counts == 0, 1.0, class_counts)
        weights = torch.tensor(1.0 / class_counts, dtype=torch.float32, device=self.proxy_device)
        weights = weights / weights.sum() * NUM_CLASSES
        loss_fn = nn.CrossEntropyLoss(weight=weights)
        optimizer = torch.optim.AdamW(model.parameters(), lr=2e-3, weight_decay=1e-4)

        x_train_t = torch.tensor(x_train, dtype=torch.float32, device=self.proxy_device)
        y_train_t = torch.tensor(y_train, dtype=torch.long, device=self.proxy_device)
        x_test_t = torch.tensor(x_test, dtype=torch.float32, device=self.proxy_device)
        y_test_t = torch.tensor(y_test, dtype=torch.long, device=self.proxy_device)

        best_acc = -1.0
        best_state = None
        for epoch in range(self.epochs):
            model.train()
            order = torch.randperm(len(x_train_t), device=self.proxy_device)
            for start in range(0, len(order), 128):
                batch = order[start : start + 128]
                logits = model(x_train_t[batch])
                loss = loss_fn(logits, y_train_t[batch])
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()

            model.eval()
            with torch.no_grad():
                preds = model(x_test_t).argmax(dim=-1)
                acc = (preds == y_test_t).float().mean().item()
            if acc > best_acc:
                best_acc = acc
                best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
            if epoch % 40 == 0 or epoch == self.epochs - 1:
                logger.info("Proxy MLP epoch %03d: test_acc=%.3f best=%.3f", epoch, acc, best_acc)

        assert best_state is not None
        model.load_state_dict(best_state)
        model.eval()

        package = {
            "state_dict": best_state,
            "input_dim": int(x_train.shape[1]),
            "epochs": int(self.epochs),
            "dataset_file": str(self.dataset_file),
            "test_acc": float(best_acc),
            "train_windows": int(len(x_train)),
            "test_windows": int(len(x_test)),
        }
        return model, package

    def _load_or_train(self) -> None:
        if self.weights_path.exists() and not self.force_retrain:
            package = torch.load(self.weights_path, map_location="cpu", weights_only=False)
            input_dim = int(package["input_dim"])
            model = ProxyMLP(input_dim=input_dim)
            model.load_state_dict(package["state_dict"])
            self.model = model.to(self.proxy_device).eval()
            self.model_info = {
                "source": "loaded",
                "weights_path": str(self.weights_path),
                "test_acc": package.get("test_acc"),
                "train_windows": package.get("train_windows"),
                "test_windows": package.get("test_windows"),
                "epochs": package.get("epochs"),
            }
            logger.info("Loaded proxy MLP weights from %s", self.weights_path)
            return

        logger.info("Training proxy MLP from cached dataset: %s", self.dataset_file)
        model, package = self._train_model()
        self.weights_path.parent.mkdir(parents=True, exist_ok=True)
        torch.save(package, self.weights_path)
        self.model = model
        self.model_info = {
            "source": "trained",
            "weights_path": str(self.weights_path),
            "test_acc": package.get("test_acc"),
            "train_windows": package.get("train_windows"),
            "test_windows": package.get("test_windows"),
            "epochs": package.get("epochs"),
        }
        logger.info("Saved proxy MLP weights to %s", self.weights_path)

    def reset(self) -> None:
        self.history.clear()
        self.inference_count = 0

    def _decode_image(self, image_base64: str) -> np.ndarray:
        image_bytes = base64.b64decode(image_base64)
        pil = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        return np.array(pil)

    def _bbox_frame(self, bbox: Optional[dict[str, Any]]) -> dict[str, Any]:
        if not bbox:
            return {"cx": 0.5, "cy": 0.5, "area": 0.0, "has_bbox": False}
        return {
            "cx": float(bbox["cx"]),
            "cy": float(bbox["cy"]),
            "area": float(bbox["area"]),
            "has_bbox": True,
        }

    def _build_online_feature(self, current_rgb: np.ndarray) -> np.ndarray:
        frame = frame_to_small_feature(current_rgb)
        feat: list[float] = []
        current_idx = len(self.history) - 1
        for k in range(WINDOW):
            idx = max(0, current_idx - (WINDOW - 1 - k))
            item = self.history[idx]
            feat.extend([item["cx"], item["cy"], item["area"], float(item["has_bbox"])])
        feat.extend(frame.tolist())
        feat.extend(build_proxy_features(self.history, current_idx))
        return np.asarray(feat, dtype=np.float32)

    def predict(self, image_base64: str, instruction: str) -> dict[str, Any]:
        if self.model is None:
            raise RuntimeError("Proxy model is not loaded")

        start = time.time()
        image_rgb = self._decode_image(image_base64)
        grounding = self.grounder.run(image_rgb)
        bbox = grounding["bbox"]

        self.history.append(self._bbox_frame(bbox))
        if len(self.history) > max(WINDOW, CONSISTENCY_K):
            self.history = self.history[-max(WINDOW, CONSISTENCY_K) :]

        feature = self._build_online_feature(image_rgb)
        x = torch.tensor(feature[None, :], dtype=torch.float32, device=self.proxy_device)
        with torch.no_grad():
            logits = self.model(x)
            pred_class = int(logits.argmax(dim=-1).item())

        self.inference_count += 1
        return {
            "action": ACTION_2D[pred_class],
            "action_3d": ACTION_3D[pred_class],
            "latency_ms": (time.time() - start) * 1000.0,
            "predicted_class": pred_class,
            "predicted_label": CLASS_NAMES[pred_class],
            "bbox": bbox,
            "grounding_caption": grounding["caption"],
            "grounding_latency_ms": grounding["latency_ms"],
            "goal_near_proxy": goal_near_proxy(self.history[-1]),
            "buffer_status": {
                "history_size": len(self.history),
                "window": WINDOW,
                "consistency_k": CONSISTENCY_K,
            },
            "source": self.model_info.get("source", "loaded"),
            "instruction_used": False,
            "instruction": instruction,
        }


def resolve_device(raw: str, fallback_cuda: bool = True) -> torch.device:
    raw = raw.strip().lower()
    if raw == "cpu":
        return torch.device("cpu")
    if raw == "cuda":
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    return torch.device("cuda" if fallback_cuda and torch.cuda.is_available() else "cpu")


def get_model(refresh: bool = False) -> ProxyInferenceModel:
    global model_instance
    if refresh:
        model_instance = None
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    if model_instance is None:
        dataset_file = Path(os.getenv("VLA_PROXY_DATASET_FILE", str(DATASET_FILE)))
        weights_path = Path(os.getenv("VLA_PROXY_WEIGHTS_PATH", str(DEFAULT_WEIGHTS_PATH)))
        grounding_model_path = Path(os.getenv("VLA_GROUNDING_MODEL_PATH", str(DEFAULT_GROUNDING_MODEL)))
        proxy_device = resolve_device(os.getenv("VLA_PROXY_DEVICE", "auto"))
        grounding_device = resolve_device(os.getenv("VLA_PROXY_GROUNDING_DEVICE", "auto"))
        epochs = int(os.getenv("VLA_PROXY_TRAIN_EPOCHS", "220"))
        force_retrain = os.getenv("VLA_PROXY_FORCE_RETRAIN", "false").lower() == "true"

        model_instance = ProxyInferenceModel(
            dataset_file=dataset_file,
            weights_path=weights_path,
            proxy_device=proxy_device,
            grounding_device=grounding_device,
            grounding_model_path=grounding_model_path,
            epochs=epochs,
            force_retrain=force_retrain,
        )
    return model_instance


@app.get("/")
async def root() -> dict[str, Any]:
    return {
        "name": "Mobile VLA Exp19 Proxy API",
        "version": "0.1.0",
        "status": "running",
        "auth": "API Key required (X-API-Key header)",
        "note": "Instruction is accepted for API compatibility but Exp19 proxy ignores text.",
    }


@app.get("/health")
async def health_check() -> dict[str, Any]:
    gpu_memory = None
    if torch.cuda.is_available():
        gpu_memory = {
            "allocated_gb": float(torch.cuda.memory_allocated() / 1024**3),
            "reserved_gb": float(torch.cuda.memory_reserved() / 1024**3),
            "device_name": torch.cuda.get_device_name(0),
        }

    model = model_instance
    return {
        "status": "healthy",
        "model_loaded": model is not None,
        "model_name": None if model is None else model.model_name,
        "gpu_memory": gpu_memory,
        "proxy_info": None if model is None else model.model_info,
        "dataset_file": None if model is None else str(model.dataset_file),
        "weights_path": None if model is None else str(model.weights_path),
        "grounding_model_path": None if model is None else str(model.grounding_model_path),
        "proxy_device": None if model is None else str(model.proxy_device),
        "grounding_device": None if model is None else str(model.grounding_device),
    }


@app.post("/predict", response_model=InferenceResponse)
async def predict(request: InferenceRequest, api_key: str = Depends(verify_api_key)) -> InferenceResponse:
    del api_key
    try:
        model = get_model()
        result = model.predict(request.image, request.instruction)
        return InferenceResponse(
            action=result["action"],
            latency_ms=result["latency_ms"],
            model_name=model.model_name,
            strategy="proxy_mlp",
            source=result["source"],
            buffer_status=result["buffer_status"],
            predicted_class=result["predicted_class"],
            predicted_label=result["predicted_label"],
            action_3d=result["action_3d"],
            bbox=result["bbox"],
            grounding_caption=result["grounding_caption"],
            grounding_latency_ms=result["grounding_latency_ms"],
            goal_near_proxy=result["goal_near_proxy"],
            instruction_used=result["instruction_used"],
        )
    except Exception as exc:
        logger.exception("Proxy prediction failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/reset")
async def reset_history(api_key: str = Depends(verify_api_key)) -> dict[str, Any]:
    del api_key
    model = get_model()
    model.reset()
    return {"status": "success", "message": "Proxy history reset"}


@app.get("/test")
async def test_endpoint(api_key: str = Depends(verify_api_key)) -> dict[str, Any]:
    del api_key
    dummy = Image.new("RGB", (224, 224), color=(128, 128, 128))
    buf = io.BytesIO()
    dummy.save(buf, format="PNG")
    return {
        "message": "Test endpoint",
        "image_b64_len": len(base64.b64encode(buf.getvalue()).decode("utf-8")),
        "note": "Use POST /predict for real inference.",
    }


if __name__ == "__main__":
    import argparse
    import uvicorn

    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=int(os.getenv("VLA_PORT", "8000")))
    parser.add_argument("--host", type=str, default="0.0.0.0")
    args = parser.parse_args()

    logger.info("Pre-loading Exp19 proxy model before server start...")
    get_model()
    logger.info("Proxy model ready. Starting uvicorn...")
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
