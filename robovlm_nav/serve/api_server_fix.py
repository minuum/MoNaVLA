"""
FastAPI Inference Server for Mobile VLA
교수님 서버에서 모델 호출을 위한 API 서버

입력: 이미지 + Language instruction
출력: 2DOF actions [linear_x, linear_y]  # 학습 데이터 기준

보안: API Key 인증
교수님 합의: Chunk=1,5,10 모델 지원 (첫 번째 액션만 실행)

Note: 학습 시 linear_x, linear_y로 학습했음 (실제 로봇 제어 시 linear_y를 angular_z로 매핑 필요)
"""

from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
import torch
import numpy as np
from PIL import Image
import base64
import io
import time
from typing import List, Optional
import logging
import os
import secrets

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Mobile VLA Inference API", version="1.0.0")

# API Key 설정
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

# 환경 변수에서 API Key 읽기 (없으면 생성)
def get_api_key():
    api_key = os.getenv("VLA_API_KEY")
    if not api_key:
        # API Key 자동 생성 및 출력
        api_key = secrets.token_urlsafe(32)
        logger.warning("="*60)
        logger.warning("⚠️  VLA_API_KEY 환경 변수가 없습니다!")
        logger.warning(f"생성된 API Key: {api_key}")
        logger.warning("다음 명령어로 저장하세요:")
        logger.warning(f'export VLA_API_KEY="{api_key}"')
        logger.warning("="*60)
    return api_key

VALID_API_KEY = get_api_key()

async def verify_api_key(api_key: str = Depends(api_key_header)):
    """API Key 검증"""
    if api_key is None:
        logger.warning("❌ 인증 실패: API Key가 제공되지 않음")
        raise HTTPException(
            status_code=403,
            detail="API Key required. Please provide X-API-Key header."
        )
    if api_key != VALID_API_KEY:
        logger.warning(f"❌ 인증 실패: {api_key[:10]}...")
        raise HTTPException(
            status_code=403,
            detail="Invalid API Key"
        )
    return api_key

# Global model instance (lazy loading)
model_instance = None


class InferenceRequest(BaseModel):
    """추론 요청 스키마"""
    image: str  # base64 encoded image
    instruction: str  # Language instruction
    snap_to_grid: Optional[bool] = None  # Enable/Disable discrete action filtering
    snap_threshold: Optional[float] = 0.8 # Optimized threshold
    

class InferenceResponse(BaseModel):
    """추론 응답 스키마"""
    action: List[float]  # [linear_x, linear_y]  # 학습 데이터 기준
    latency_ms: float  # Inference latency in milliseconds
    model_name: str
    chunk_size: int  # 모델의 chunk size (fwd_pred_next_n)
    full_chunk: Optional[List[List[float]]] = None  # Future trajectory
    raw_action: Optional[List[float]] = None  # Raw action for debugging
    

class MobileVLAInference:
    """Mobile VLA 추론 파이프라인"""
    
    def __init__(self, checkpoint_path: str, config_path: str, device: str = "cuda"):
        """
        Args:
            checkpoint_path: LoRA Fine-tuned 모델 checkpoint 경로
            config_path: Config JSON 파일 경로
            device: "cuda" or "cpu"
        """
        self.device = device
        self.checkpoint_path = checkpoint_path
        self.config_path = config_path
        
        logger.info(f"Loading model from {checkpoint_path}")
        logger.info(f"Using device: {device}")
        
        # Load config
        # Load config recursively
        self.config = self._load_config_recursive(config_path)
        
        # Inference settings (from config or defaults)
        self.default_snap_to_grid = self.config.get('snap_to_grid', True)  # Default Enable
        self.default_snap_threshold = self.config.get('snap_threshold', 0.8)
        
        # Load model
        self._load_model()
        
        # History buffer for images
        self.window_size = self.config.get('window_size', 8)
        self.image_history = []
        
        # Persistence for smoothing
        self.last_action = np.zeros(self.action_dim)
        self.smoothing_factor = self.config.get('smoothing_factor', 1.0)
        
        # Frame counter (for first-frame enforcement)
        self.frame_count = 0
        
        logger.info("Model loaded successfully with smoothing enabled")
        
    def _load_config_recursive(self, config_path):
        import json
        import os
        from robovlms.model.backbone.base_backbone import deep_update
        
        with open(config_path, 'r') as f:
            config = json.load(f)
            
        parent_path = config.get("parent")
        if parent_path is not None:
            # resolve relative to current config file
            base_dir = os.path.dirname(config_path)
            # handle cases where parent path in config is relative to VLA_ROOT
            if parent_path.startswith("configs/") or parent_path.startswith("Mobile_VLA/"):
                parts = parent_path.split("/")
                if "configs" in parts:
                    idx = parts.index("configs")
                    parent_path = os.path.join(*parts[idx:])
                parent_path = os.path.join(os.path.dirname(base_dir), parent_path)
            else:
                parent_path = os.path.join(base_dir, parent_path)
                
            if os.path.exists(parent_path):
                parent_config = self._load_config_recursive(parent_path)
                # merge: config overrides parent
                config = deep_update(parent_config, config)
            else:
                logger.warning(f"Parent config not found: {parent_path}")
                
        return config

    def _load_model(self):
        """모델 로딩"""
        import sys
        from pathlib import Path
        
        # Add RoboVLMs to path
        vla_root = Path(__file__).parent.parent.parent
        robovlms_paths = [
            vla_root / 'third_party' / 'RoboVLMs',
            vla_root / 'RoboVLMs_upstream',
            vla_root / 'RoboVLMs'
        ]
        for p in robovlms_paths:
            if p.exists() and str(p) not in sys.path:
                sys.path.insert(0, str(p))
        
        from robovlms.train.mobile_vla_trainer import MobileVLATrainer
        
        # Inject model backbone mapping required by newer V3 configs
        try:
            from robovlms.model.backbone.robokosmos import RoboKosMos
            import robovlms.model.backbone as backbone
            backbone.__dict__["RoboVLM-Nav"] = RoboKosMos
            
            import robovlms.model.policy_head as policy_head
            from robovlms.model.policy_head.mobile_vla_policy import MobileVLAClassificationDecoder, MobileVLALSTMDecoder
            policy_head.__dict__["NavPolicy"] = MobileVLAClassificationDecoder
            policy_head.__dict__["NavPolicyRegression"] = MobileVLALSTMDecoder
            
            logger.info("🔧 Injected RoboVLM-Nav & NavPolicy mapping")
        except Exception as base_e:
            logger.warning(f"⚠️ Failed to inject model mapping: {base_e}")

        # Load from Lightning checkpoint
        logger.info(f"Loading checkpoint: {self.checkpoint_path}")
        logger.info(f"Using config: {self.config_path}")
        
        self.model = MobileVLATrainer.load_from_checkpoint(
            self.checkpoint_path,
            configs=self.config,
            strict=False  # Allow missing keys
        )
        
        self.model.to(self.device)
        self.model.eval()
        logger.info(f"Model loaded on {self.device}")
        
        # Load and cache processor
        from transformers import AutoProcessor
        processor_path = self.config.get('model_path', '')
        if not processor_path or not os.path.exists(processor_path):
            processor_path = 'microsoft/kosmos-2-patch14-224'
        logger.info(f"Loading processor from {processor_path}")
        self.processor = AutoProcessor.from_pretrained(processor_path)
        
        # Get model info
        self.fwd_pred_next_n = self.config.get('fwd_pred_next_n', 1)
        self.action_dim = self.config.get('action_dim', 2)
        
        # Check if classification model
        act_head_config = self.config.get('act_head', {})
        self.is_classification = act_head_config.get('type') in ['MobileVLAClassificationDecoder', 'NavPolicy']
        logger.info(f"Is classification model: {self.is_classification}")
        
        # Class mapping for classification models
        # 9개 클래스(STOP, F, B, L, R, FL, FR, BL, BR)에 대한 액션 매핑 추가
        self.class_to_action = {
            0: np.array([0.0, 0.0]),
            1: np.array([1.15, 0.0]),
            2: np.array([-1.15, 0.0]),
            3: np.array([0.0, 1.15]),
            4: np.array([0.0, -1.15]),
            5: np.array([1.15, 1.15]),
            6: np.array([1.15, -1.15]),
            7: np.array([-1.15, 1.15]),
            8: np.array([-1.15, -1.15])
        }
        
        logger.info(f"Model: Chunk={self.fwd_pred_next_n}, Action_dim={self.action_dim}")
        
    def preprocess_image(self, image_base64: str) -> Image.Image:
        """Base64 이미지를 PIL Image로 변환"""
        # Decode base64
        image_bytes = base64.b64decode(image_base64)
        image = Image.open(io.BytesIO(image_bytes)).convert('RGB')
        return image
    
    def _apply_snap_to_grid(self, action: np.ndarray, threshold: float = 0.35) -> np.ndarray:
        """
        액션을 [-1.15, 0.0, 1.15] 이산 액션셋으로 매핑
        최근 모델 통계(Y Mean 0.01, X Mean 0.8)를 바탕으로 최적화된 Gain/Bias 적용
        """
        snapped = np.zeros_like(action)
        
        # Action Dim: [linear_x, linear_y]
        # For Classification models, the model already outputs discrete targets (1.15, -1.15, etc.)
        # so we only need to handle small drifts or zero preservation.
        if action.ndim == 1:
            for i in range(len(action)):
                val = action[i]
                if abs(val) > threshold:
                    snapped[i] = 1.15 if val > 0 else -1.15
                else:
                    snapped[i] = 0.0
        else:
            for t in range(action.shape[0]):
                for i in range(action.shape[1]):
                    val = action[t, i]
                    if abs(val) > threshold:
                        snapped[t, i] = 1.15 if val > 0 else -1.15
                    else:
                        snapped[t, i] = 0.0
            
        return snapped

    def predict(self, image_base64: str, instruction: str, 
                snap_to_grid: Optional[bool] = None, 
                snap_threshold: Optional[float] = None) -> tuple[np.ndarray, np.ndarray, float]:
        """
        추론 실행
        
        Args:
            image_base64: Image data
            instruction: Text command
            snap_to_grid: Force enable/disable snap logic (overrides config)
            snap_threshold: Deadzone threshold (overrides config)

        Returns:
            (action, full_chunk, latency_ms, raw_action): 2DOF action [linear_x, linear_y], latency, and raw action
        """
        start_time = time.time()
        
        # Determine settings
        use_snap = snap_to_grid if snap_to_grid is not None else self.default_snap_to_grid
        threshold = snap_threshold if snap_threshold is not None else self.default_snap_threshold
        original_action = None
        
        with torch.no_grad():
            # Preprocess image (base64 -> PIL)
            pil_image = self.preprocess_image(image_base64)
            
            # Prepare inputs (Kosmos format)
            # Use cached processor
            processor = self.processor
            
            # Optional: Instruction Mapping for robustness (Phase 5 Standard)
            # Short keywords are expanded to "Strong Prompts" identified during evaluation
            instr_map = {
                "left": "Steer left to the brown pot",
                "right": "Steer right to the brown pot",
                "straight": "Go straight to the brown pot",
                "go left": "Steer left to the brown pot",
                "go right": "Steer right to the brown pot",
                "navigate left": "Perform left navigation to the object",
                "navigate right": "Perform right navigation to the object"
            }
            
            # Prepare inputs (Kosmos format)
            # Match RoboVLMs training prompt: "<grounding>An image of a robot {instruction}"
            clean_instruction = instruction.strip()
            if not clean_instruction.startswith("<grounding>"):
                if not clean_instruction.startswith("An image of a robot"):
                    full_prompt = f"<grounding>An image of a robot {clean_instruction}"
                else:
                    full_prompt = f"<grounding>{clean_instruction}"
            else:
                full_prompt = clean_instruction
                
            # Add to history buffer
            self.image_history.append(pil_image)
            if len(self.image_history) > self.window_size:
                self.image_history.pop(0)
            
            # Pad history if not full
            current_history = self.image_history.copy()
            if len(current_history) < self.window_size:
                # Use a zero-tensor like black image for initial padding if we want to emphasize 'start'
                # But VLA usually likes first-image repetition. Let's keep repetition but ensure it is stable.
                first_img = current_history[0]
                while len(current_history) < self.window_size:
                    current_history.insert(0, first_img)
            
            # Process all images in history
            inputs = processor(
                images=current_history,
                text=[full_prompt] * self.window_size,
                return_tensors="pt"
            )
            
            # Move to device
            for key in inputs:
                if isinstance(inputs[key], torch.Tensor):
                    inputs[key] = inputs[key].to(self.device)
            
            # Add batch dimension (B, T, C, H, W)
            if inputs['pixel_values'].dim() == 4:
                inputs['pixel_values'] = inputs['pixel_values'].unsqueeze(0)  # (1, T, C, H, W)
            
            # Prepare inputs for model.inference()
            rgb = inputs['pixel_values']  # (B, T, C, H, W)
            language = inputs['input_ids']  # (B, T, seq_len)
            text_mask = inputs['attention_mask']
            
            # Ensure batch size is 1 for language and mask (RoboVLMs repeats them internally)
            if language.dim() == 2 and language.shape[0] > 1:
                language = language[0:1, :]
            elif language.dim() == 3:
                language = language[:, -1, :] # (8, T, seq_len) -> (8, seq_len)
                if language.shape[0] > 1:
                    language = language[0:1, :]
                
            if text_mask.dim() == 2 and text_mask.shape[0] > 1:
                text_mask = text_mask[0:1, :]
            elif text_mask.dim() == 3:
                text_mask = text_mask[:, -1, :]
                if text_mask.shape[0] > 1:
                    text_mask = text_mask[0:1, :]
            
            # Add hand_rgb dummy (B, T, C, H, W)
            hand_rgb = torch.zeros_like(rgb)
            
            # Call model.inference()
            prediction = self.model.model.inference(
                vision_x=rgb,
                lang_x=language,
                attention_mask=text_mask,
                action_labels=None,
                action_mask=None,
                caption_labels=None,
                caption_mask=None,
                vision_gripper=None
            )
            
            # Extract action from prediction
            if 'action' in prediction:
                action_output = prediction['action']
                
                # Handle tuple
                if isinstance(action_output, tuple):
                    action_output = action_output[0]
                
                # Extract from tensor
                if isinstance(action_output, torch.Tensor):
                    if action_output.dim() == 4:
                        if self.is_classification:
                            # (B, T, chunk, num_classes)
                            # Use T=-1 to get prediction for the latest frame in the window
                            logits = action_output[0, -1, :, :].cpu().numpy()
                            class_indices = np.argmax(logits, axis=-1)
                            full_chunk = np.array([self.class_to_action[idx] for idx in class_indices])
                        else:
                            # (B, T, chunk, action_dim)
                            full_chunk = action_output[0, -1, :, :].cpu().numpy()
                        first_action = full_chunk[0]
                    elif action_output.dim() == 3:
                        if self.is_classification:
                            # (B, T, num_classes) or (B, chunk, num_classes)
                            logits = action_output[0, -1, :].cpu().numpy() if action_output.dim() == 3 else action_output[0, :, :].cpu().numpy()
                            # Ensure we have class indices
                            if logits.ndim == 1: # (num_classes)
                                idx = np.argmax(logits)
                                first_action = self.class_to_action[idx]
                                full_chunk = np.expand_dims(first_action, axis=0)
                            else: # (chunk, num_classes)
                                class_indices = np.argmax(logits, axis=-1)
                                full_chunk = np.array([self.class_to_action[idx] for idx in class_indices])
                        else:
                            full_chunk = action_output[0, -1, :].cpu().numpy() if action_output.dim() == 3 else action_output[0, :, :].cpu().numpy()
                            if full_chunk.ndim == 1:
                                full_chunk = np.expand_dims(full_chunk, axis=0)
                        first_action = full_chunk[0]
                    elif action_output.dim() == 2:
                        if self.is_classification:
                            logits = action_output[0, :].cpu().numpy()
                            idx = np.argmax(logits)
                            first_action = self.class_to_action[idx]
                        else:
                            first_action = action_output[0, :].cpu().numpy()
                        full_chunk = np.expand_dims(first_action, axis=0)
                    elif action_output.dim() == 1:
                        if self.is_classification:
                            idx = torch.argmax(action_output).item()
                            first_action = self.class_to_action[idx]
                        else:
                            first_action = action_output.cpu().numpy()
                        full_chunk = np.expand_dims(first_action, axis=0)
                    else:
                        raise ValueError(f"Unexpected action tensor shape: {action_output.shape}")
                else:
                    raise ValueError(f"Action must be a torch.Tensor, got: {type(action_output)}")
            else:
                raise ValueError("Could not find action in prediction output")
            
            # Apply Smoothing
            if self.last_action is not None:
                first_action = self.smoothing_factor * first_action + (1 - self.smoothing_factor) * self.last_action
            self.last_action = first_action.copy()

            # Apply Snap-to-Grid if enabled
            if use_snap:
                original_action = first_action.copy()
                first_action = self._apply_snap_to_grid(first_action, threshold)
                
                # Also snap the full chunk if needed
                full_chunk = self._apply_snap_to_grid(full_chunk, threshold)
                
                logger.debug(f"Snapped action: {original_action} -> {first_action}")
            
            logger.info(f"Extracted action (linear_x, linear_y): {first_action}")
            logger.info(f"Full chunk shape: {full_chunk.shape}")
            
        latency_ms = (time.time() - start_time) * 1000
        
        # Frame 1 Safety Override
        if len(self.image_history) == 1:
            logger.info("🛑 Frame 1: Safety override")
            return np.array([0.0, 0.0]), np.zeros_like(full_chunk), latency_ms, np.array([0.0, 0.0])
        
        return first_action, full_chunk, latency_ms, original_action if use_snap else first_action


def get_model():
    """모델 인스턴스 가져오기 (lazy loading)"""
    global model_instance
    
    if model_instance is None:
        model_name = os.getenv("VLA_MODEL_NAME", "v3_exp07_lora")
        
        # 모델별 체크포인트 및 config 경로
        model_configs = {
            "v3_exp08_center_goal": {
                "checkpoint": "/home/soda/vla/runs/v3_classification/kosmos/mobile_vla_v3_exp08_center_goal/2026-03-05/v3-exp08-center-goal/epoch_epoch=07-val_loss=val_loss=0.031.ckpt",
                "config": "/home/soda/vla/configs/mobile_vla_v3_exp08_center_goal.json"
            },
            "v3_exp07_lora": {
                "checkpoint": "/home/soda/vla/epoch_epoch=05-val_loss=val_loss=0.044.ckpt",
                "config": "/home/soda/vla/configs/mobile_vla_v3_exp07_lora.json"
            },
            "unified_regression_win12": {
                "checkpoint": "runs/unified_regression_win12/kosmos/mobile_vla_unified_finetune/2026-02-05/unified_regression_win12_20260205/epoch=9-step=600.ckpt",
                "config": "Mobile_VLA/configs/mobile_vla_unified_regression_win12.json"
            },
            "basket_chunk5": {
                "checkpoint": "runs/mobile_vla_no_chunk_20251209/kosmos/mobile_vla_finetune/2025-12-17/mobile_vla_chunk5_20251217/epoch_epoch=06-val_loss=val_loss=0.067.ckpt",
                "config": "Mobile_VLA/configs/mobile_vla_chunk5_20251217.json"
            },
            "chunk10_epoch8": {
                "checkpoint": "runs/mobile_vla_no_chunk_20251209/kosmos/mobile_vla_finetune/2025-12-17/mobile_vla_chunk10_20251217/epoch_epoch=08-val_loss=val_loss=0.312.ckpt",
                "config": "Mobile_VLA/configs/mobile_vla_chunk10_20251217.json"
            },
            "basket_left_only": {
                "checkpoint": "runs/basket_left_only/kosmos/mobile_vla_left_only_finetune/2026-02-01/basket_left_only_20260201/last-v1.ckpt",
                "config": "Mobile_VLA/configs/mobile_vla_basket_left_only.json"
            },
            "exp06_resampler": {
                "checkpoint": "runs/unified_regression_win12/kosmos/mobile_vla_unified_finetune_resampler/2026-02-06/unified_reg_win12_k6_resampler_20260205/last.ckpt",
                "config": "Mobile_VLA/configs/mobile_vla_unified_reg_win12_k6_resampler.json"
            },
            "exp12_hybrid": {
                "checkpoint": "runs/unified_regression_win12/kosmos/mobile_vla_exp12_win6_k1_resampler/2026-02-11/exp12_win6_k1_resampler/epoch=epoch=06-val_loss=val_loss=0.0017.ckpt",
                "config": "Mobile_VLA/configs/mobile_vla_exp12_win6_k1_resampler.json"
            },
            "exp04_baseline": {
                "checkpoint": "runs/unified_regression_win12/kosmos/mobile_vla_unified_finetune/2026-02-05/unified_regression_win12_20260205/epoch=9-step=600.ckpt",
                "config": "Mobile_VLA/configs/mobile_vla_unified_regression_win12.json"
            },
            "exp05_chunk1": {
                "checkpoint": "runs/unified_regression_win12/kosmos/mobile_vla_unified_finetune_k1/2026-02-05/unified_reg_win12_k1_20260205/epoch=5-step=2136.ckpt",
                "config": "Mobile_VLA/configs/mobile_vla_unified_reg_win12_k1.json"
            },
            "exp09_latent128": {
                "checkpoint": "runs/unified_regression_win12/kosmos/mobile_vla_exp09_resampler_latent128/2026-02-07/exp09_resampler_latent128/last.ckpt",
                "config": "Mobile_VLA/configs/mobile_vla_exp09_latent128.json"
            },
            "exp16_win6": {
                "checkpoint": "runs/unified_regression_win12/kosmos/mobile_vla_exp16_win6_k1/2026-02-09/exp16_win6_k1/last.ckpt",
                "config": "Mobile_VLA/configs/mobile_vla_exp16_win6_k1.json"
            },
            "exp17_win8": {
                "checkpoint": "runs/unified_regression_win12/kosmos/mobile_vla_exp17_win8_k1/2026-02-10/exp17_win8_k1/epoch=epoch=09-val_loss=val_loss=0.0013.ckpt",
                "config": "Mobile_VLA/configs/mobile_vla_exp17_win8_k1.json"
            },
            "basket_grounded_epoch10": {
                "checkpoint": "runs/basket_left_only/kosmos/mobile_vla_left_only_finetune/2026-02-02/basket_left_grounded_20260202/epoch_epoch=10-val_loss=val_loss=0.002.ckpt",
                "config": "Mobile_VLA/configs/mobile_vla_basket_left_only.json"
            },
            "basket_classification": {
                "checkpoint": "checkpoints/basket_classification_v1.ckpt",
                "config": "Mobile_VLA/configs/mobile_vla_basket_left_classification.json"
            },
            "basket_classification_weighted": {
                "checkpoint": "runs/basket_left_only/kosmos/mobile_vla_left_only_finetune/2026-02-02/basket_left_classification_weighted_20260202/epoch_epoch=01-val_loss=val_loss=0.014.ckpt",
                "config": "Mobile_VLA/configs/mobile_vla_basket_left_classification_weighted.json"
            },
            "basket_classification_epoch10": {
                "checkpoint": "runs/basket_left_only/kosmos/mobile_vla_left_only_finetune/2026-02-02/basket_left_classification_20260202/epoch_epoch=09-val_loss=val_loss=0.003.ckpt",
                "config": "Mobile_VLA/configs/mobile_vla_basket_left_classification.json"
            },
            "basket_classification_weighted_norm": {
                "checkpoint": "runs/basket_left_only/kosmos/mobile_vla_left_only_finetune/2026-02-03/basket_left_weighted_norm/epoch_epoch=09-val_loss=val_loss=0.011.ckpt",
                "config": "Mobile_VLA/configs/mobile_vla_basket_left_classification_weighted.json"
            },
            "basket_no_suffix_v1": {
                "checkpoint": "runs/basket_left_only/kosmos/mobile_vla_left_only_finetune/2026-02-03/basket_left_no_suffix_v1/last.ckpt",
                "config": "Mobile_VLA/configs/mobile_vla_basket_left_classification_weighted.json"
            },
            "basket_grounding_v1": {
                "checkpoint": "runs/basket_left_only/kosmos/mobile_vla_left_only_finetune/2026-02-04/basket_mixed_grounding_v2_window12/last.ckpt",
                "config": "Mobile_VLA/configs/mobile_vla_basket_left_classification_weighted.json"
            },
            "basket_grounding_v2_win12": {
                "checkpoint": "runs/basket_left_only/kosmos/mobile_vla_left_only_finetune/2026-02-04/basket_mixed_grounding_v2_window12/last.ckpt",
                "config": "Mobile_VLA/configs/mobile_vla_basket_left_classification_weighted.json"
            },
            "exp_v2_17_win8": {
                "checkpoint": "RoboVLMs_upstream/runs/exp_v2_series/kosmos/mobile_vla_exp_v2_17/2026-02-15/exp-v2-17/epoch_epoch=09-val_loss=val_loss=0.001.ckpt",
                "config": "Mobile_VLA/configs/mobile_vla_exp_v2_17.json"
            },
            "exp_v2_12_hybrid": {
                "checkpoint": "RoboVLMs_upstream/runs/exp_v2_series/kosmos/mobile_vla_exp_v2_12/2026-02-16/exp-v2-12/epoch_epoch=07-val_loss=val_loss=0.001.ckpt",
                "config": "Mobile_VLA/configs/mobile_vla_exp_v2_12.json"
            }
        }
        
        # Get model config
        if model_name not in model_configs:
            logger.warning(f"Unknown model '{model_name}', defaulting to 'v3_exp07_lora'")
            model_name = "v3_exp07_lora"
        
        config = model_configs[model_name]
        checkpoint_path = os.getenv("VLA_CHECKPOINT_PATH", config["checkpoint"])
        config_path = os.getenv("VLA_CONFIG_PATH", config["config"])
        
        logger.info(f"Loading model: {model_name}")
        logger.info(f"Checkpoint: {checkpoint_path}")
        logger.info(f"Config: {config_path}")
        
        model_instance = MobileVLAInference(
            checkpoint_path=checkpoint_path,
            config_path=config_path,
            device="cuda" if torch.cuda.is_available() else "cpu"
        )
    
    return model_instance


@app.get("/")
async def root():
    """API 정보 (인증 불필요)"""
    return {
        "name": "Mobile VLA Inference API",
        "version": "1.0.0",
        "status": "running",
        "auth": "API Key required (X-API-Key header)"
    }


@app.get("/health")
async def health_check():
    """헬스 체크 (인증 불필요)"""
    gpu_memory = None
    if torch.cuda.is_available():
        gpu_memory = {
        }
    
    return {
        "status": "healthy",
        "model_loaded": model_instance is not None,
        "device": "cuda" if torch.cuda.is_available() else "cpu",
        "gpu_memory": gpu_memory
    }


@app.get("/model/info")
async def model_info(api_key: str = Depends(verify_api_key)):
    """모델 정보 조회 (API Key 필수)"""
    try:
        model = get_model()
        
        return {
            "model_name": os.getenv("VLA_MODEL_NAME", "basket_left_only"),
            "checkpoint_path": model.checkpoint_path,
            "config_path": model.config_path,
            "fwd_pred_next_n": model.fwd_pred_next_n,
            "action_dim": model.action_dim,
            "freeze_backbone": model.config.get('freeze_backbone', True),
            "lora_enable": model.config.get('lora_enable', False),
            "device": model.device
        }
    except Exception as e:
        logger.error(f"Failed to get model info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/model/list")
async def list_models(api_key: str = Depends(verify_api_key)):
    """사용 가능한 모델 목록 조회 (API Key 필수)"""
    # 모델별 체크포인트 및 config 경로 (get_model 함수와 동일)
    model_configs = {
        "v3_exp08_center_goal": {
            "checkpoint": "/home/soda/vla/runs/v3_classification/kosmos/mobile_vla_v3_exp08_center_goal/2026-03-05/v3-exp08-center-goal/epoch_epoch=07-val_loss=val_loss=0.031.ckpt",
            "config": "/home/soda/vla/configs/mobile_vla_v3_exp08_center_goal.json",
            "description": "V3 EXP-08 Center Goal (Epoch 7)",
            "fwd_pred_next_n": 1,
            "recommended": True
        },
        "basket_chunk5_legacy": {
            "checkpoint": "runs/mobile_vla_no_chunk_20251209/kosmos/mobile_vla_finetune/2025-12-17/mobile_vla_chunk5_20251217/epoch_epoch=06-val_loss=val_loss=0.067.ckpt",
            "config": "Mobile_VLA/configs/mobile_vla_chunk5_20251217.json",
            "description": "Legacy Best model (val_loss=0.067)",
            "fwd_pred_next_n": 5
        },
        "chunk10_epoch8": {
            "checkpoint": "runs/mobile_vla_no_chunk_20251209/kosmos/mobile_vla_finetune/2025-12-17/mobile_vla_chunk10_20251217/epoch_epoch=08-val_loss=val_loss=0.312.ckpt",
            "config": "Mobile_VLA/configs/mobile_vla_chunk10_20251217.json",
            "description": "Chunk10 Epoch 8",
            "fwd_pred_next_n": 10
        },
        "basket_left_only": {
            "checkpoint": "runs/basket_left_only/kosmos/mobile_vla_left_only_finetune/2026-02-01/basket_left_only_20260201/last-v1.ckpt",
            "config": "Mobile_VLA/configs/mobile_vla_basket_left_only.json",
            "description": "Basket Navigation - LEFT ONLY (Epoch 10, v2)",
            "fwd_pred_next_n": 5
        }
    }
    
    current_model = os.getenv("VLA_MODEL_NAME", "v3_exp08_center_goal")
    
    return {
        "available_models": model_configs,
        "current_model": current_model,
        "model_loaded": model_instance is not None
    }


class ModelSwitchRequest(BaseModel):
    """모델 전환 요청 스키마"""
    model_name: str  # basket_chunk5, chunk10_epoch8, no_chunk_epoch4


@app.post("/model/switch")
async def switch_model(request: ModelSwitchRequest, api_key: str = Depends(verify_api_key)):
    """모델 전환 (API Key 필수)
    
    서버 재시작 없이 런타임에 모델 변경 가능
    """
    global model_instance
    
    try:
        # Get list of models from get_model's local model_configs (conceptually)
        # For simplicity, update the hardcoded list
        available_models = [
            "v3_exp08_center_goal", "v3_exp07_lora", "unified_regression_win12", "basket_chunk5", "chunk10_epoch8", 
            "basket_left_only", "basket_chunk5_legacy", "basket_no_suffix_v1",
            "basket_grounding_v1", "basket_grounding_v2_win12",
            "exp_v2_17_win8", "exp_v2_12_hybrid"
        ]
        
        if request.model_name not in available_models:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid model name. Available: {available_models}"
            )
        
        logger.info(f"🔄 Switching model to: {request.model_name}")
        
        # 기존 모델 메모리 해제
        if model_instance is not None:
            del model_instance
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            model_instance = None
        
        # 환경 변수 업데이트
        os.environ["VLA_MODEL_NAME"] = request.model_name
        
        # 새 모델 로드
        new_model = get_model()
        
        logger.info(f"✅ Model switched successfully to: {request.model_name}")
        
        return {
            "status": "success",
            "previous_model": os.getenv("VLA_MODEL_NAME", "basket_left_only"),
            "current_model": request.model_name,
            "model_info": {
                "checkpoint_path": new_model.checkpoint_path,
                "fwd_pred_next_n": new_model.fwd_pred_next_n,
                "action_dim": new_model.action_dim,
                "device": new_model.device
            },
        }
        
    except Exception as e:
        logger.error(f"Failed to switch model: {e}")
        raise HTTPException(status_code=500, detail=str(e))



@app.post("/reset")
async def reset_episode():
    """에피소드 초기화 (히스토리 버퍼 비우기)"""
    model = get_model()
    if model:
        model.image_history = []
        model.last_action = np.zeros(model.action_dim)
        model.frame_count = 0
        logger.info("Episode history and smoothing buffer reset")
    return {"status": "success", "message": "History buffer cleared"}

@app.post("/predict", response_model=InferenceResponse)
async def predict(request: InferenceRequest, api_key: str = Depends(verify_api_key)):
    """
    추론 엔드포인트 (API Key 필수)
    
    Example:
        curl -X POST http://localhost:8000/predict \
          -H "X-API-Key: your-api-key" \
          -H "Content-Type: application/json" \
          -d '{"image": "base64_string", "instruction": "..."}'
    """
    try:
        model = get_model()
        
        # Increment frame count
        model.frame_count += 1
        
        # Force [0, 0] for the very first frame (mandatory stationary start)
        if model.frame_count == 1:
            logger.info("🆕 First frame detected: Enforcing mandatory [0.0, 0.0] action")
            # We still add to history if we want to maintain context
            # We call predict once just to update internal history/buffers, but ignore the result
            _, full_chunk, latency_ms, raw_action = model.predict(
                image_base64=request.image,
                instruction=request.instruction,
                snap_to_grid=request.snap_to_grid,
                snap_threshold=request.snap_threshold
            )
            action = np.zeros(2) # Force zero
        else:
            action, full_chunk, latency_ms, raw_action = model.predict(
                image_base64=request.image,
                instruction=request.instruction,
                snap_to_grid=request.snap_to_grid,
                snap_threshold=request.snap_threshold
            )
        
        logger.info(f"✅ Prediction: {action}, Chunk: {full_chunk.shape}, Latency: {latency_ms:.1f}ms")
        
        return InferenceResponse(
            action=action.tolist(),
            latency_ms=latency_ms,
            model_name=os.getenv("VLA_MODEL_NAME", "basket_chunk5"),
            chunk_size=model.fwd_pred_next_n,
            full_chunk=full_chunk.tolist(),
            raw_action=raw_action.tolist() if hasattr(raw_action, 'tolist') else raw_action
        )
        
    except Exception as e:
        logger.error(f"Prediction failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/test")
async def test_endpoint(api_key: str = Depends(verify_api_key)):
    """
    테스트 엔드포인트 - 더미 데이터로 API 테스트 (API Key 필수)
    
    Returns:
        샘플 prediction 결과
    """
    import base64
    from io import BytesIO
    from PIL import Image
    import numpy as np
    
    # Create dummy RGB image
    dummy_img = Image.new('RGB', (1280, 720), color=(255, 0, 0))
    
    # Convert to base64
    buffer = BytesIO()
    dummy_img.save(buffer, format='PNG')
    img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    # Test instruction (Unified with training data)
    instruction = "Navigate around obstacles and reach the front of the beverage bottle on the left"
    
    # Simulate prediction (2 DOF)
    dummy_action = [1.15, 0.319]  # [linear_x, angular_z]
    
    return {
        "message": "Test endpoint - using dummy data",
        "instruction": instruction,
        "action": dummy_action,
        "note": "This is a test endpoint. Use POST /predict for real inference."
    }


if __name__ == "__main__":
    import uvicorn
    
    # Run server
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
