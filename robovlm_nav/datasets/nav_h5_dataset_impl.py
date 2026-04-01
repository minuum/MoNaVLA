import os
from pathlib import Path
import h5py
import numpy as np
import torch
from PIL import Image
from torch.utils.data import Dataset
import torchvision.transforms as T
# from robovlms.utils.model_utils import load_image
import random

class MobileVLAH5Dataset(Dataset):
    def __init__(
        self,
        data_dir,
        episode_pattern='episode_*.h5',
        window_size=8,
        fwd_pred_next_n=5,
        image_size=224,
        discrete_action=False,
        abs_action=False,
        is_validation=False,
        train_split=0.9,
        num_classes=9,
        instruction_preset='default',
        min_episode_frames=10,
        augment=False,
        use_color_jitter=False,
        use_random_crop=False,
        curvature_only=False,
        counterfactual_stop_prob=0.0,
        **kwargs
    ):
        self.data_dir = Path(data_dir)
        self.window_size = window_size
        self.fwd_pred_next_n = fwd_pred_next_n
        self.image_size = image_size
        self.discrete_action = discrete_action
        self.abs_action = abs_action
        self.num_classes = num_classes
        self.instruction_preset = instruction_preset
        self.min_episode_frames = min_episode_frames
        self.augment = augment
        self.use_color_jitter = use_color_jitter
        self.use_random_crop = use_random_crop
        self.curvature_only = curvature_only
        # [Counterfactual Stop] 학습 중 이 확률로 Stop 명령 + zero action으로 오버라이드
        # is_validation 설정 전에 저장 (나중에 val에서는 비활성화)
        self._counterfactual_stop_prob = counterfactual_stop_prob
        self.tokenizer = kwargs.get('tokenizer', None)
        
        # [NEW] Handle is_training from GRDataModule/third_party
        if 'is_training' in kwargs:
            is_validation = not kwargs['is_training']
        self.is_validation = is_validation

        # Get all episode files
        all_files = sorted(list(self.data_dir.glob(episode_pattern)))
        
        # Filter too short episodes
        self.episode_files = []
        for f in all_files:
            try:
                with h5py.File(f, 'r') as hf:
                    if len(hf['images']) >= self.min_episode_frames:
                        self.episode_files.append(f)
            except Exception as e:
                print(f"Error reading {f}: {e}")

        # Split
        num_episodes = len(self.episode_files)
        split_idx = int(num_episodes * 0.8)
        
        if self.is_validation:
            self.episode_files = self.episode_files[split_idx:]
        else:
            self.episode_files = self.episode_files[:split_idx]

        # Precompute frame indices for __len__ and __getitem__
        self.frame_indices = []
        filtered_files = []
        for ep_idx, f in enumerate(self.episode_files):
            with h5py.File(f, 'r') as hf:
                num_frames = len(hf['images'])
                
                # [Option B] Curvature Only Filtering
                if self.curvature_only:
                    actions = hf['actions'][:]
                    # If all actions are straight (x > 0.3, abs(y) < 0.3), skip this episode
                    is_straight_only = True
                    for a in actions:
                        ax, ay = a[0], a[1]
                        # Not straight if: turning (abs(ay) > 0.3) OR stopping/backward (ax < 0.3)
                        if abs(ay) > 0.3 or ax < 0.3:
                            is_straight_only = False
                            break
                    if is_straight_only:
                        continue
                
                filtered_files.append(f)
                # We need at least window_size frames AND space for fwd_pred_next_n
                # Max valid start frame is num_frames - fwd_pred_next_n - 1
                for start_f in range(0, num_frames - self.window_size - self.fwd_pred_next_n + 1):
                    # Local index relative to filtered_files list
                    self.frame_indices.append((len(filtered_files) - 1, start_f))
        
        self.episode_files = filtered_files
        print(f"{'Validation' if self.is_validation else 'Training'} dataset initialized with {len(self.episode_files)} episodes and {len(self.frame_indices)} valid sequences.")

        # Transforms
        if self.use_color_jitter:
            self.color_jitter = T.ColorJitter(brightness=0.4, contrast=0.4, saturation=0.4, hue=0.1)
        if self.use_random_crop:
            self.random_crop = T.RandomResizedCrop(self.image_size, scale=(0.8, 1.0))

    def __len__(self):
        return len(self.frame_indices)

    def _get_action_aware_instruction(self, actions):
        """Build a training-only instruction variant from the next predicted action.
        Added Random Noise to prevent the model from over-relying on instruction text.
        """
        # 20% 확률로 일반적인 명령어를 주어, 모델이 이미지를 강제로 보게 함 (Noisy Instruction)
        if random.random() < 0.2:
            generic_variations = [
                "Navigate to the gray basket",
                "Go to the target object",
                "Proceed to the destination",
                "바구니가 보일 때까지 계속 이동해",
                "목표물을 향해 가줘",
                "앞에 보이는 바구니로 도달해"
            ]
            return f"<grounding>An image of a robot {random.choice(generic_variations)}"

        target_idx = min(self.window_size, len(actions) - 1)
        # actions shape handling
        if len(actions.shape) == 3:
            # actions: [window, next_n, 2]
            tx, ty = actions[target_idx][0][0], actions[target_idx][0][1]
        else:
            # actions: [window, 2]
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
                "Halt in front of the object",
                "Stand by at current position",
                "Maintain pose near the basket",
                "Freeze movement",
                "바구니 앞에서 멈춰",
                "움직임을 중단하고 대기해",
                "현재 위치에서 정지"
            ]
        elif curr_act_type == "forward":
            variations = [
                "Direct route to the gray basket",
                "Straight ahead to the target",
                "Proceed front toward the object",
                "Navigate straight",
                "바구니를 향해 쭉 직진해",
                "정면 목표로 전진",
                "방향 꺾지 말고 그대로 가"
            ]
        elif curr_act_type == "left":
            variations = [
                "Rotate left toward the basket",
                "Spin left to see the target",
                "Steer toward the left side",
                "Left turn required",
                "좌측으로 회전해",
                "왼쪽으로 각도를 틀어",
                "우측 말고 왼쪽 방향으로 보정해"
            ]
        elif curr_act_type == "right":
            variations = [
                "Rotate right toward the basket",
                "Spin right to see the target",
                "Steer toward the right side",
                "Right turn required",
                "우측으로 회전해",
                "오른쪽으로 조향을 바꿔",
                "바구니 보일 때까지 우측으로 움직여"
            ]
        elif curr_act_type == "diag_fl":
            variations = [
                "Angle toward left-front side",
                "Diagonal path to the left",
                "Shift left while moving",
                "Bear left of the basket",
                "왼쪽 대각선으로 비스듬히 접근해",
                "전진하면서 왼쪽으로 살짝 틀어",
                "왼쪽 앞 방향으로 경로 조정"
            ]
        elif curr_act_type == "diag_fr":
            variations = [
                "Angle toward right-front side",
                "Diagonal path to the right",
                "Shift right while moving",
                "Bear right of the basket",
                "오른쪽 대각선으로 비스듬히 가",
                "우측 전방을 향해 완만하게 회전해",
                "전진하면서 조향을 오른쪽으로 살짝 유지해"
            ]
        else:
            variations = ["Navigate to the gray basket"]
        

        return f"<grounding>An image of a robot {random.choice(variations)}"

    def __getitem__(self, idx):
        ep_idx, start_frame = self.frame_indices[idx]
        
        with h5py.File(self.episode_files[ep_idx], 'r') as f:
            total_len = len(f['images'])
            total_frames_needed = self.window_size
            total_actions_needed = self.window_size + self.fwd_pred_next_n - 1
            
            # 이미지 로드 (window_size 만큼)
            images = []
            for t in range(start_frame, min(start_frame + total_frames_needed, total_len)):
                img_array = f['images'][t]
                img = Image.fromarray(img_array.astype(np.uint8))
                
                # [V3] Color Jitter
                if self.use_color_jitter:
                    img = self.color_jitter(img)
                
                # [V3] Random Crop
                if self.use_random_crop:
                    img = self.random_crop(img)
                else:
                    img = img.resize((self.image_size, self.image_size), Image.BILINEAR)
                
                img_tensor = torch.from_numpy(np.array(img)).float() / 255.0
                img_tensor = img_tensor.permute(2, 0, 1)
                
                # Normalization (CLIP/Kosmos-2 mean & std)
                mean = torch.tensor([0.48145466, 0.4578275, 0.40821073]).view(3, 1, 1)
                std = torch.tensor([0.26862954, 0.26130258, 0.27577711]).view(3, 1, 1)
                img_tensor = (img_tensor - mean) / std
                
                images.append(img_tensor)
            
            while len(images) < total_frames_needed:
                images.append(torch.zeros_like(images[-1]) if images else torch.zeros(3, self.image_size, self.image_size))
            
            # -------------------------------------------------------------------------
            # [LFS Update] 액션 로드 (Chunking을 위해 충분한 길이를 FLAT하게 로드)
            # -------------------------------------------------------------------------
            actions = []
            if 'actions' not in f:
                for _ in range(total_actions_needed):
                    actions.append(np.zeros(2))
            else:
                episode_actions = f['actions'][:]
                episode_len = episode_actions.shape[0]
                
                for t in range(start_frame, min(start_frame + total_actions_needed, episode_len)):
                    actions.append(episode_actions[t][:2].copy())
                
                # 부족한 액션 패딩
                while len(actions) < total_actions_needed:
                    actions.append(np.zeros(2))
            
            actions = np.array(actions)
            # -------------------------------------------------------------------------
            
            # [Counterfactual Stop] 학습 중 지정된 확률로 Stop 명령 + zero action 주입
            # 목적: 모델이 텍스트를 무시하면 틀리는 상황을 강제 생성 → Text Sensitivity 학습
            # Validation에서는 절대 적용하지 않음
            _apply_counterfactual_stop = (
                not self.is_validation
                and self._counterfactual_stop_prob > 0.0
                and random.random() < self._counterfactual_stop_prob
            )
            
            if _apply_counterfactual_stop:
                # Stop 명령어 변형
                stop_variations = [
                    "Stop in front of the gray basket",
                    "Halt immediately",
                    "Freeze and stay still",
                    "Do not move",
                    "바구니 앞에서 멈춰",
                    "정지해",
                    "움직이지 마",
                ]
                language_base = f"<grounding>An image of a robot {random.choice(stop_variations)}"
                # 액션을 모두 0으로 오버라이드 (정지 = 속도 0)
                actions = np.zeros_like(actions)
            else:
                use_action_aware_train = (self.instruction_preset == "action_aware_train")
                if use_action_aware_train:
                    language_base = self._get_action_aware_instruction(actions)
                elif 'language_instruction' in f:
                    raw = f['language_instruction'][0]
                    language_base = raw.decode('utf-8') if isinstance(raw, bytes) else str(raw)
                else:
                    language_base = "Navigate to the gray basket"

            # -------------------------------------------------------------------------
            # [LFS Update] Augmentation - Image Flip (좌우 반전)
            # -------------------------------------------------------------------------
            if self.augment:
                # 50% 확률로 좌우 반전
                if random.random() < 0.5:
                    # 1. 이미지 반전
                    images = [T.functional.hflip(img) for img in images]
                    
                    # 2. 액션/레이블 반전 (좌우가 바뀌면 LEFT ↔ RIGHT, FL ↔ FR 도 바뀌어야 함)
                    if not self.discrete_action:
                        # Continuous action: [linear_x, angular_z] -> angular_z 부호 반전
                        actions_tensor_aug = torch.from_numpy(np.array(actions)).float()
                        actions_tensor_aug[..., 1] = -actions_tensor_aug[..., 1]
                        actions = actions_tensor_aug.numpy()
                    
                    # 3. 언어 텍스트 반전 (LEFT ↔ RIGHT 교체)
                    lang_map = {
                        "left": "right", "right": "left",
                        "좌측": "우측", "우측": "좌측",
                        "왼쪽": "오른쪽", "오른쪽": "왼쪽"
                    }
                    for k, v in lang_map.items():
                        if k in language_base:
                            language_base = language_base.replace(k, "temp_target").replace(v, k).replace("temp_target", v)
                            break
            # -------------------------------------------------------------------------

        # 텐서 변환
        images_tensor = torch.stack(images)  # (total_frames_needed, C, H, W)
        
        if self.discrete_action:
            cls_labels = []
            for a in actions:
                # a is (2,)
                curr_x, curr_y = a[0], a[1]
                x, y = float(curr_x), float(curr_y)
                
                is_x_pos = x > 0.3
                is_x_neg = x < -0.3
                is_y_pos = y > 0.3
                is_y_neg = y < -0.3
                
                # 9-classes: 0:Stop, 1:F, 2:B, 3:L, 4:R, 5:FL, 6:FR, 7:BL, 8:BR
                if not is_x_pos and not is_x_neg and not is_y_pos and not is_y_neg:
                    label = 0
                elif is_x_pos and not (is_y_pos or is_y_neg):
                    label = 1
                elif is_x_neg and not (is_y_pos or is_y_neg):
                    label = 2
                elif not (is_x_pos or is_x_neg) and is_y_pos:
                    label = 3
                elif not (is_x_pos or is_x_neg) and is_y_neg:
                    label = 4
                elif is_x_pos and is_y_pos:
                    label = 5
                elif is_x_pos and is_y_neg:
                    label = 6
                elif is_x_neg and is_y_pos:
                    label = 7
                elif is_x_neg and is_y_neg:
                    label = 8
                else:
                    label = 0
                cls_labels.append(label)
            
            # 9 classes -> 6 classes mapping
            if self.num_classes == 6:
                # 0:Stop, 1:F, 2:B(Stop), 3:L, 4:R, 5:FL, 6:FR
                mapping = {0: 0, 1: 1, 3: 2, 4: 3, 5: 4, 6: 5}
                cls_labels = [mapping.get(int(l), 0) for l in cls_labels]
            
            actions_tensor = torch.tensor(cls_labels, dtype=torch.long)
            action_chunck = actions_tensor  # For compatibility
        else:
            # Continuous action: Predict next N actions for each frame in window
            # actions shape: (window_size + next_n - 1, 2 or 6 or higher)
            actions_tensor_full = torch.from_numpy(np.array(actions)).float()
            
            # [CRITICAL] Slice to 2D [linear_x, angular_z] for navigation
            if actions_tensor_full.shape[-1] > 2:
                actions_tensor_full = actions_tensor_full[..., :2]
                
            actions_tensor_full = torch.clamp(actions_tensor_full, -1.0, 1.0)
            
            # chunk_size is fwd_pred_next_n
            # Create action_chunck (B, seq_len, chunk_size, 2)
            action_chunks = []
            for t in range(self.window_size):
                chunk = actions_tensor_full[t : t + self.fwd_pred_next_n]
                if len(chunk) < self.fwd_pred_next_n:
                    pad_len = self.fwd_pred_next_n - len(chunk)
                    last_val = chunk[-1] if len(chunk) > 0 else torch.zeros(2)
                    chunk = torch.cat([chunk, last_val.repeat(pad_len, 1)], dim=0)
                action_chunks.extend(chunk)
            
            # Reshape into (seq_len, chunk_size, 2)
            action_chunck = torch.stack(action_chunks).reshape(self.window_size, self.fwd_pred_next_n, 2)
            actions_tensor = actions_tensor_full[:self.window_size] # (window_size, 2)
        
        data_dict = {
            'rgb': images_tensor,
            'hand_rgb': torch.zeros_like(images_tensor),
            'action': actions_tensor,
            'action_chunck': action_chunck,
            'image_mask': torch.ones(self.window_size),
            'chunck_mask': torch.ones(self.window_size, self.fwd_pred_next_n),
            'lang': language_base,
            'raw_text': language_base,
            'data_source': 'mobile_vla_action',
            'attention_mask': torch.ones(self.window_size),
        }

        # [CRITICAL] Tokenize the instruction
        if self.tokenizer is not None:
            # Kosmos-2 tokenizer expects a specific format or just text
            tokenized = self.tokenizer(
                language_base,
                padding='max_length',
                truncation=True,
                max_length=256,
                return_tensors='pt'
            )
            data_dict['text'] = tokenized['input_ids'].squeeze(0)
            data_dict['text_mask'] = tokenized['attention_mask'].squeeze(0)
        else:
            # Fallback (should not happen in real training via GRDataModule)
            data_dict['text'] = torch.zeros(256, dtype=torch.long)
            data_dict['text_mask'] = torch.zeros(256, dtype=torch.long)

        return data_dict

    def collater(self, data):
        """Standard collater for batching."""
        batch = {}
        for key in data[0].keys():
            if key in ['lang', 'raw_text', 'data_source']:
                batch[key] = [d[key] for d in data]
            else:
                batch[key] = torch.stack([d[key] for d in data])
        return batch
