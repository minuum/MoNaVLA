# GitHub Citation: https://github.com/Robot-VLAs/RoboVLMs/blob/main/robovlms/data/calvin_dataset.py
# Mobile VLA용 HDF5 데이터셋 로더 (RoboVLMs CALVIN 데이터셋 구조 참고)

import glob
import h5py
import numpy as np
import torch
from PIL import Image
from torch.utils.data import Dataset
from pathlib import Path
import torchvision.transforms as T
from robovlms.utils.model_utils import build_tokenizer


class MobileVLAH5Dataset(Dataset):
    """
    Mobile VLA HDF5 데이터셋 로더
    
    Args:
        data_dir: HDF5 파일들이 있는 디렉토리
        episode_pattern: 에피소드 파일 패턴 (예: "episode_20251106_*.h5")
        window_size: 히스토리 윈도우 크기
        action_chunk_size: 액션 청크 크기 (fwd_pred_next_n)
        model_name: 모델 이름 (토크나이저용)
        image_size: 이미지 크기
        rgb_pad: RGB 증강 패딩
        train_split: 학습/검증 분할 비율
        is_validation: 검증 데이터셋 여부
    """
    
    def __init__(
        self,
        data_dir,
        episode_pattern="episode_*.h5",
        window_size=8,
        action_chunk_size=10,
        model_name="kosmos",
        image_size=224,
        rgb_pad=10,
        train_split=0.8,
        is_validation=False,
        shift_first=False,
        abs_action=False,  # 액션 절대값 사용 (방향 제거)
        augment=False,     # 데이터 증강 (Mirroring 등)
        discrete_action=False, # 분류 방식 사용 여부 (6개 클래스)
        use_color_jitter=False,  # [V3] Color Jitter 증강
        use_random_crop=False,   # [V3] Random Crop 증강
        instruction_preset=None, # [EXP-08+] instruction 프리셋 ('center_goal' 등)
        min_episode_frames=None, # [EXP-09+] 허용 최소 에피소드 프레임 수. None이면 window+chunk 기준
        **kwargs
    ):
        self.data_dir = data_dir
        self.episode_pattern = episode_pattern
        self.window_size = window_size
        self.action_chunk_size = action_chunk_size
        self.model_name = model_name
        self.image_size = image_size
        self.rgb_pad = rgb_pad
        self.train_split = train_split
        self.is_validation = is_validation
        self.shift_first = shift_first
        self.abs_action = abs_action  # 방향 제거 옵션
        self.augment = augment and (not is_validation)  # 검증셋에는 증강 미적용
        self.is_training = not is_validation
        # instruction 프리셋:
        # - None: 기본 left/right goal phrasing
        # - center_goal: EXP-08 style goal-completion phrasing
        # - action_aware_train: training only, action-conditioned phrasing
        self.instruction_preset = instruction_preset
        # [EXP-09+] 가변 길이 에피소드 허용을 위한 최소 프레임 수
        # None이면 window_size + fwd_pred_next_n 과 동일 (기존 동작 유지)
        self.min_episode_frames = min_episode_frames
        
        # [V3] Color Jitter & Random Crop — 학습셋에만 적용
        self.use_color_jitter = use_color_jitter and (not is_validation)
        self.use_random_crop = use_random_crop and (not is_validation)
        
        if self.use_color_jitter:
            self.color_jitter = T.ColorJitter(
                brightness=0.4, contrast=0.4, saturation=0.3, hue=0.1
            )
        if self.use_random_crop:
            # 원본 이미지에서 80~100% 영역을 crop하여 image_size로 resize
            self.random_crop = T.RandomResizedCrop(
                size=image_size, scale=(0.8, 1.0), ratio=(0.9, 1.1)
            )
        
        # 에피소드 파일 로드
        episode_files = sorted(glob.glob(f"{data_dir}/{episode_pattern}"))
        if len(episode_files) == 0:
            raise ValueError(f"No episodes found in {data_dir} with pattern {episode_pattern}")
        
        # Train/Val 분할
        split_idx = int(len(episode_files) * train_split)
        if is_validation:
            self.episode_files = episode_files[split_idx:]
        else:
            self.episode_files = episode_files[:split_idx]
        
        # 각 에피소드의 프레임 수 계산 (유효한 에피소드만 포함)
        self.episode_lengths = []
        self.cumulative_lengths = [0]
        valid_episode_files = []
        for ep_file in self.episode_files:
            with h5py.File(ep_file, 'r') as f:
                if 'images' not in f or 'actions' not in f:
                    print(f"  ⚠️ Skipping incomplete episode (missing keys): {Path(ep_file).name}")
                    continue
                length = len(f['images'])
                valid_episode_files.append(ep_file)
                self.episode_lengths.append(length)
                self.cumulative_lengths.append(self.cumulative_lengths[-1] + length)
        self.episode_files = valid_episode_files
        
        self.total_frames = self.cumulative_lengths[-1]
        
        print(f"MobileVLAH5Dataset initialized:")
        print(f"  data_dir: {data_dir}")
        print(f"  episode_pattern: {episode_pattern}")
        print(f"  num_episodes: {len(self.episode_files)}")
        print(f"  total_frames: {self.total_frames}")
        print(f"  window_size: {window_size}")
        print(f"  action_chunk_size: {action_chunk_size}")
        print(f"  shift_first: {shift_first}")
        print(f"  model_name: {model_name}")
        print(f"  rgb_pad: {rgb_pad}")
        print(f"  train_split: {train_split}")
        print(f"  is_training: {not is_validation}")
        
        # 토크나이저 및 text_fn 초기화
        self.tokenizer = kwargs.get("tokenizer", None)
        self.tokenizer_config = kwargs.get("tokenizer_config", None)
        self.model_name = model_name
        self.window_size = window_size
        self.action_chunk_size = action_chunk_size  # 사용하지 않음 (호환성 유지)
        self.fwd_pred_next_n = kwargs.get("fwd_pred_next_n", action_chunk_size)  # kwargs에서 가져오기
        # discrete_action 설정 (인자 또는 kwargs에서 확인)
        self.discrete_action = discrete_action or kwargs.get("discrete_action", False)
        
        # BOLD PRINT to check value at initialization
        print(f"!!! MobileVLAH5Dataset INITIALIZED with discrete_action = {self.discrete_action} !!!")
        
        # text_fn 초기화 (tokenizer_config가 있으면)
        if self.tokenizer_config is not None and self.tokenizer is not None:
            from robovlms.data.data_utils import get_text_function
            tokenizer_type = self.tokenizer_config.get("tokenizer_type", "kosmos")
            max_text_len = self.tokenizer_config.get("max_text_len", 256)
            self.text_fn = get_text_function(self.tokenizer, tokenizer_type, max_text_len)
        else:
            self.text_fn = None
    
    def __len__(self):
        # 각 에피소드에서 window_size + fwd_pred_next_n 만큼의 프레임이 필요
        # [EXP-09+] min_episode_frames 설정 시 해당 값 이상의 에피소드도 포함
        total_frames_needed = self.window_size + self.fwd_pred_next_n
        min_valid = self.min_episode_frames if self.min_episode_frames is not None else total_frames_needed
        valid_frames = 0
        for length in self.episode_lengths:
            if length >= min_valid:
                # 짧은 에피소드는 항상 start=0에서만 샘플링 (range 1)
                max_samples = max(1, length - total_frames_needed + 1) if length >= total_frames_needed else 1
                valid_frames += max_samples
        return max(1, valid_frames)
    
    def _find_episode_and_frame(self, idx):
        """전체 인덱스를 에피소드와 프레임 인덱스로 변환"""
        for ep_idx, (start, end) in enumerate(zip(self.cumulative_lengths[:-1], self.cumulative_lengths[1:])):
            if idx < end - start:
                frame_idx = idx
                return ep_idx, frame_idx
            idx -= (end - start)
        return len(self.episode_files) - 1, 0

    def _get_action_aware_instruction(self, actions):
        """Build a training-only instruction variant from the next predicted action."""
        target_idx = min(self.window_size, len(actions) - 1)
        tx, ty = actions[target_idx][0], actions[target_idx][1]

        curr_act_type = "forward"
        if abs(tx) < 0.3 and abs(ty) < 0.3:
            curr_act_type = "stop"
        elif tx > 0.3 and abs(ty) < 0.3:
            curr_act_type = "forward"
        elif tx < -0.3 and abs(ty) < 0.3:
            curr_act_type = "backward"
        elif abs(tx) < 0.3 and ty > 0.3:
            curr_act_type = "left"
        elif abs(tx) < 0.3 and ty < -0.3:
            curr_act_type = "right"
        elif tx > 0.3 and ty > 0.3:
            curr_act_type = "diag_fl"
        elif tx > 0.3 and ty < -0.3:
            curr_act_type = "diag_fr"

        if curr_act_type == "stop":
            variations = [
                "Stop in front of the gray basket",
                "Halt at the target location",
                "Maintain position near the basket",
                "Stop the robot now",
            ]
        elif curr_act_type == "forward":
            variations = [
                "Navigate straight to the gray basket",
                "Move forward to the basket",
                "Go straight to the target",
                "Proceed forward",
            ]
        elif curr_act_type == "left":
            variations = [
                "Steer left toward the gray basket",
                "Turn left to reach the target",
                "Navigate left to the basket",
                "Make a left turn toward the object",
            ]
        elif curr_act_type == "right":
            variations = [
                "Steer right toward the gray basket",
                "Turn right to reach the target",
                "Navigate right to the basket",
                "Make a right turn toward the object",
            ]
        elif curr_act_type == "diag_fl":
            variations = [
                "Navigate diagonally left toward the gray basket",
                "Move forward-left to the basket",
                "Steer slightly left while moving forward",
            ]
        elif curr_act_type == "diag_fr":
            variations = [
                "Navigate diagonally right toward the gray basket",
                "Move forward-right to the basket",
                "Steer slightly right while moving forward",
            ]
        else:
            variations = [
                "Navigate to the gray basket",
                "Move toward the target",
            ]

        return np.random.choice(variations)
    
    def __getitem__(self, idx):
        # Random Temporal Sampling for better diversity
        # Instead of sequential indexing, randomly select episode and start frame
        
        total_frames_needed = self.window_size + self.fwd_pred_next_n
        
        # Random episode selection (with reproducibility for validation)
        if self.is_validation:
            # Validation: deterministic sampling for reproducibility
            ep_idx = idx % len(self.episode_files)
            np.random.seed(idx)  # Deterministic random for this sample
        else:
            # Training: truly random episode selection
            ep_idx = np.random.randint(0, len(self.episode_files))
        
        # HDF5 파일 로드
        with h5py.File(self.episode_files[ep_idx], 'r') as f:
            total_len = len(f['images'])
            
            # Random start frame within valid range
            max_start = max(0, total_len - total_frames_needed)
            if self.is_validation:
                # Validation: deterministic start
                start_frame = (idx // len(self.episode_files)) % (max_start + 1) if max_start > 0 else 0
            else:
                # Training: random start
                start_frame = np.random.randint(0, max_start + 1) if max_start > 0 else 0
            
            # 이미지 로드 (random start부터 total_frames_needed 프레임)
            images = []
            for t in range(start_frame, min(start_frame + total_frames_needed, total_len)):
                img_array = f['images'][t]
                img = Image.fromarray(img_array.astype(np.uint8))
                
                # [V3] Color Jitter — PIL 단계에서 적용 (정규화 전)
                if self.use_color_jitter:
                    img = self.color_jitter(img)
                
                # [V3] Random Crop — PIL 단계에서 적용
                if self.use_random_crop:
                    img = self.random_crop(img)
                else:
                    img = img.resize((self.image_size, self.image_size), Image.BILINEAR)
                
                img_tensor = torch.from_numpy(np.array(img)).float() / 255.0
                img_tensor = img_tensor.permute(2, 0, 1)
                
                # Normalization (CLIP/Kosmos-2 mean & std)
                # Fixes domain shift between training (was [0,1]) and inference (Normalized)
                mean = torch.tensor([0.48145466, 0.4578275, 0.40821073]).view(3, 1, 1)
                std = torch.tensor([0.26862954, 0.26130258, 0.27577711]).view(3, 1, 1)
                img_tensor = (img_tensor - mean) / std
                
                images.append(img_tensor)
            
            # Padding if needed (edge case)
            while len(images) < total_frames_needed:
                images.append(torch.zeros_like(images[-1]) if images else torch.zeros(3, self.image_size, self.image_size))
            
            # 액션 로드
            actions = []
            if 'actions' not in f:
                # 안전장치: actions 키 없는 파일은 zero action으로 처리
                print(f"⚠️ No 'actions' key in {self.episode_files[ep_idx]}, using zeros.")
                for _ in range(total_frames_needed):
                    actions.append(np.zeros(2))
            else:
                episode_actions = f['actions'][:] # Load all actions for the episode
                episode_len = episode_actions.shape[0]
                
                # For hybrid planning (action chunking), we need sequence of actions
                if self.fwd_pred_next_n > 1:
                    # For each frame in the window_size, we need a chunk of actions
                    for i in range(self.window_size):
                        current_frame_abs_idx = start_frame + i
                        start_act = current_frame_abs_idx
                        end_act = min(start_act + self.fwd_pred_next_n, episode_len)
                        
                        # Slice next_n actions: shape [next_n, 2]
                        chunk = episode_actions[start_act:end_act, :2] # Only take first 2 dimensions
                        
                        # Pad if last few frames of episode
                        if chunk.shape[0] < self.fwd_pred_next_n:
                            padding = np.zeros((self.fwd_pred_next_n - chunk.shape[0], chunk.shape[1]), dtype=chunk.dtype)
                            chunk = np.concatenate([chunk, padding], axis=0)
                        actions.append(chunk)

                    # np.stack 이전에 패딩을 수행하여 AttributeError 방지
                    while len(actions) < total_frames_needed:
                        actions.append(np.zeros((self.fwd_pred_next_n, 2)))
                    actions = np.stack(actions) # shape [window_size, fwd_pred_next_n, 2]
                else:
                    # Standard 1-step prediction, load actions for total_frames_needed
                    for t in range(start_frame, min(start_frame + total_frames_needed, episode_len)):
                        action_2d = episode_actions[t][:2]  # linear_x, linear_y만 사용
                        actions.append(action_2d.copy())
            
            # Padding for actions (always ensure total_frames_needed for consistency)
            # This fixes the 'maximum size N but size 10' error in V4 inference
            while len(actions) < total_frames_needed:
                actions.append(np.zeros(2))
            
            use_action_aware_train = (
                self.instruction_preset == "action_aware_train" and self.is_training
            )
            if use_action_aware_train:
                language_base = self._get_action_aware_instruction(actions)
            elif 'language_instruction' in f:
                raw = f['language_instruction'][0]
                language_base = raw.decode('utf-8') if isinstance(raw, bytes) else str(raw)
            else:
                ep_name = str(f.attrs.get('episode_name', '')).lower()
                if not ep_name:
                    ep_name = Path(self.episode_files[ep_idx]).stem.lower()

                if 'left' in ep_name:
                    direction = 'left'
                elif 'right' in ep_name:
                    direction = 'right'
                else:
                    direction = None

                if self.instruction_preset == 'center_goal':
                    language_base = "Navigate toward the gray basket until it is centered in the frame"
                elif direction == 'left':
                    language_base = "Navigate to the gray basket visible on the left side of the frame"
                elif direction == 'right':
                    language_base = "Navigate to the gray basket visible on the right side of the frame"
                else:
                    language_base = "Navigate to the gray basket"

            language = language_base



        # -------------------------------------------------------------------------
        # Data Augmentation: Mirroring (Left <-> Right)
        # -------------------------------------------------------------------------
        if self.augment and np.random.rand() < 0.5:
            # 1. Flip Images
            images = [torch.flip(img, [2]) for img in images]
            
            # 2. Invert linear_y Action (Left <-> Right)
            actions = [np.array([a[0], -a[1]]) for a in actions]
            
            # 3. Swap Language 'left' <-> 'right' in the entire instruction
            # This handles both base language and our dynamic suffix (sliding left <-> sliding right)
            temp_lang = language.lower()
            temp_lang = temp_lang.replace('left', 'PLACEHOLDER').replace('right', 'left').replace('PLACEHOLDER', 'right')
            # Restore capitalization if needed
            language = temp_lang.capitalize()
        # -------------------------------------------------------------------------

        # 텐서 변환
        images_tensor = torch.stack(images)  # (total_frames_needed, C, H, W)
        
        if self.discrete_action:
            if idx % 100 == 0: # 너무 자주 찍히지 않게 조절
                print(f"DEBUG: __getitem__ processing discrete actions for idx {idx}")
            # Action Classification Mapping (Omniwheel 9-classes)
            # 0: Stop, 1: F, 2: B, 3: L, 4: R, 5: FL, 6: FR, 7: BL, 8: BR
            cls_labels = []
            for a in actions:
                # 텐서나 배열인 경우 .item()을 사용하여 안전하게 스칼라 추출
                try:
                    curr_x = a[0].item() if hasattr(a[0], 'item') else a[0]
                    curr_y = a[1].item() if hasattr(a[1], 'item') else a[1]
                    x, y = float(curr_x), float(curr_y)
                except:
                    # 혹시라도 a 자체가 더 복잡한 구조일 경우 대비 (fallback)
                    x, y = float(np.ravel(a)[0]), float(np.ravel(a)[1])
                
                # Threshold를 0.3으로 설정하여 미세한 노이즈 무시
                is_x_pos = x > 0.3
                is_x_neg = x < -0.3
                is_y_pos = y > 0.3
                is_y_neg = y < -0.3
                
                if not is_x_pos and not is_x_neg and not is_y_pos and not is_y_neg:
                    label = 0 # Stop
                elif is_x_pos and not (is_y_pos or is_y_neg):
                    label = 1 # Forward
                elif is_x_neg and not (is_y_pos or is_y_neg):
                    label = 2 # Backward
                elif not (is_x_pos or is_x_neg) and is_y_pos:
                    label = 3 # Left
                elif not (is_x_pos or is_x_neg) and is_y_neg:
                    label = 4 # Right
                elif is_x_pos and is_y_pos:
                    label = 5 # Diag FL
                elif is_x_pos and is_y_neg:
                    label = 6 # Diag FR
                elif is_x_neg and is_y_pos:
                    label = 7 # Diag BL
                elif is_x_neg and is_y_neg:
                    label = 8 # Diag BR
                else:
                    label = 0 # Default Stop
                cls_labels.append(label)
            actions_tensor = torch.tensor(cls_labels, dtype=torch.long)
        else:
            actions_tensor = torch.from_numpy(np.array(actions)).float()  # (total_frames_needed, 2)
            
            # 방향 제거 옵션: linear_y의 절대값 사용
            if self.abs_action:
                actions_tensor[:, 1] = torch.abs(actions_tensor[:, 1])  # linear_y만 절대값
            
            # 액션 정규화 [-1, 1] (abs_action일 때는 [0, 1]이 됨)
            actions_tensor = torch.clamp(actions_tensor, -1.0, 1.0)
        
        # 언어 토크나이징 (더미 - collate_fn에서 실제 처리)
        input_ids = torch.zeros(256, dtype=torch.long)
        attention_mask = torch.ones(256, dtype=torch.long)
        
        return {
            'rgb': images_tensor,
            'hand_rgb': torch.zeros_like(images_tensor),
            'actions': actions_tensor,
            'action_mask': torch.ones(total_frames_needed),
            'image_mask': torch.ones(total_frames_needed),
            'text': input_ids,
            'text_mask': attention_mask,
            'lang': language,
            'raw_text': language,
            'data_source': 'mobile_vla_action',
            'attention_mask': torch.ones(total_frames_needed),
        }
    
    def collater(self, data):
        """
        배치 데이터를 처리하는 collater 메서드
        DiskCalvinDataset의 collater를 참고하여 구현
        """
        # 액션 텐서 스택 (DiskCalvinDataset과 동일한 구조)
        # s["actions"]는 (window_size + fwd_pred_next_n, 2) 형태
        action_tensors = torch.from_numpy(
            np.array([s["actions"].numpy() for s in data])
        )[:, :-1]  # 마지막 프레임 제거 (DiskCalvinDataset과 동일)
        # Shape: (B, window_size + fwd_pred_next_n - 1, 2 또는 1)
        
        # 액션 마스크 스택
        action_mask = torch.from_numpy(
            np.array([s["action_mask"].numpy() for s in data])
        )[:, :-1]  # 마지막 프레임 제거
        
        # 이미지 텐서 스택
        image_tensors = torch.stack([s["rgb"] for s in data], dim=0)  # (B, window_size + fwd_pred_next_n, C, H, W)
        
        # 이미지 마스크 스택
        image_mask = torch.from_numpy(
            np.array([s["image_mask"].numpy() for s in data])
        )
        
        # Gripper 이미지 스택 (더미)
        gripper_tensors = torch.stack([s["hand_rgb"] for s in data], dim=0)  # (B, window_size + fwd_pred_next_n, C, H, W)
        
        # 언어 토크나이징 (text_fn 사용)
        stacked_language = [s["lang"] for s in data]
        if self.text_fn is not None:
            text_tensors, attention_mask = self.text_fn(stacked_language)
        else:
            # text_fn이 없으면 더미 사용 (초기화 시점)
            text_tensors = torch.stack([s["text"] for s in data], dim=0)
            attention_mask = torch.stack([s["text_mask"] for s in data], dim=0)
        
        # DiskCalvinDataset과 동일한 방식으로 chunk 생성 (unfold 사용)
        image_chunk = image_tensors.unfold(1, self.fwd_pred_next_n, 1).permute(
            0, 1, 5, 2, 3, 4
        )[:, 1:]  # 첫 번째 제거
        image_tensors = image_tensors[:, : self.window_size]  # window_size만 사용
        
        gripper_chunk = gripper_tensors.unfold(1, self.fwd_pred_next_n, 1).permute(
            0, 1, 5, 2, 3, 4
        )[:, 1:]
        gripper_tensors = gripper_tensors[:, : self.window_size]
        
        fwd_mask = image_mask.unfold(1, self.fwd_pred_next_n, 1)[:, 1:]
        
        # 액션 chunk 생성 (unfold 사용)
        action_chunck = action_tensors.unfold(1, self.fwd_pred_next_n, 1)
        if not self.discrete_action:
            action_chunck = action_chunck.permute(0, 1, 3, 2)
        action_mask = action_mask.unfold(1, self.fwd_pred_next_n, 1)
        
        res = {
            "rgb": image_tensors,  # (B, window_size, C, H, W)
            "hand_rgb": gripper_tensors,  # (B, window_size, C, H, W)
            "action": action_tensors,  # (B, window_size + fwd_pred_next_n - 1, 2)
            "text": text_tensors,  # (B, seq_len)
            "text_mask": attention_mask,  # (B, seq_len)
            "fwd_rgb_chunck": image_chunk,  # (B, window_size + fwd_pred_next_n - 2, fwd_pred_next_n, C, H, W)
            "fwd_hand_rgb_chunck": gripper_chunk,  # (B, window_size + fwd_pred_next_n - 2, fwd_pred_next_n, C, H, W)
            "fwd_mask": fwd_mask,  # (B, window_size + fwd_pred_next_n - 2, fwd_pred_next_n)
            "action_chunck": action_chunck,  # (B, window_size + fwd_pred_next_n - 2, fwd_pred_next_n, 2)
            "chunck_mask": action_mask,  # (B, window_size + fwd_pred_next_n - 2, fwd_pred_next_n)
            "raw_text": stacked_language,  # List[str]
            "data_source": "mobile_vla_action",
        }
        return res
