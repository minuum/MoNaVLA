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

    PATH_TYPE_INSTRUCTIONS = {
        "left": [
            "Navigate to the left toward the gray basket",
            "Move left to approach the target",
            "Steer left to reach the basket",
            "Head left toward the object",
            "왼쪽으로 이동해서 바구니에 접근해",
            "좌측으로 방향을 잡아 목표로 이동해",
            "왼쪽 방향으로 틀어서 바구니 쪽으로 가",
            "보이는 바구니의 왼쪽 방향으로 조향해",
            "Go left",
            "Turn left",
        ],
        "right": [
            "Navigate to the right toward the gray basket",
            "Move right to approach the target",
            "Steer right to reach the basket",
            "Head right toward the object",
            "오른쪽으로 이동해서 바구니에 접근해",
            "우측으로 방향을 잡아 목표로 이동해",
            "오른쪽으로 꺾어서 바구니 쪽으로 전진해",
            "우측 방향으로 조향을 수정해서 가",
            "Go right",
            "Turn right",
        ],
        "straight": [
            "Navigate straight forward to the gray basket",
            "Go directly ahead to the target",
            "Proceed straight to the basket",
            "Move forward toward the object",
            "바구니를 향해 직진해",
            "앞으로 곧장 이동해",
            "방향 틀지 말고 정면으로 전진해",
            "Straight ahead",
            "Keep going straight",
        ],
        "default": [
            "Navigate until the gray basket is centered and fills the lower half of the frame.",
            "Find and approach the gray basket.",
            "Move toward the target object in front of you.",
        ],
    }

    def __init__(
        self,
        data_dir,
        episode_pattern='episode_*.h5',
        window_size=8,
        fwd_pred_next_n=5,
        image_size=224,
        discrete_action=False,
        use_bbox_target=False,
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
        counterfactual_steer_prob=0.0,
        stratified_split=False,
        exclude_path_types=None,
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
        # [Counterfactual] 학습 중 이 확률로 명령어 + 대응 액션으로 오버라이드
        self._counterfactual_stop_prob = counterfactual_stop_prob
        self._counterfactual_steer_prob = counterfactual_steer_prob
        self.stratified_split = stratified_split
        self.exclude_path_types = set(exclude_path_types) if exclude_path_types else set()
        self.train_split = train_split
        self.tokenizer = kwargs.get('tokenizer', None)
        self.grounding_prefix = kwargs.get('grounding_prefix', False)
        self.use_bbox_target = use_bbox_target
        # [BugFix/Track1] instruction_override 명시적 저장 및 반영
        self.instruction_override = kwargs.get('instruction_override', None)
        
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
                    # [V5/V4 auto-detect] V5: observations/images, V4: images
                    n = len(hf['observations']['images']) if 'observations' in hf else len(hf['images'])
                    if n >= self.min_episode_frames:
                        self.episode_files.append(f)
            except Exception as e:
                print(f"Error reading {f}: {e}")

        # exclude_path_types 필터 (예: ["straight"] → straight_path 에피소드 제거)
        if self.exclude_path_types:
            self.episode_files = [
                f for f in self.episode_files
                if not any(pt in f.stem for pt in self.exclude_path_types)
            ]

        # Split
        if self.stratified_split:
            # path 타입별로 그룹화 → 각 그룹에서 독립적으로 train/val split
            from collections import defaultdict
            groups = defaultdict(list)
            for f in self.episode_files:
                stem = f.stem
                if 'straight' in stem:
                    key = 'straight'
                elif 'left' in stem:
                    key = 'left'
                elif 'right' in stem:
                    key = 'right'
                else:
                    key = 'other'
                groups[key].append(f)

            train_files, val_files = [], []
            for key in sorted(groups.keys()):
                gfiles = groups[key]
                split_i = int(len(gfiles) * self.train_split)
                train_files.extend(gfiles[:split_i])
                val_files.extend(gfiles[split_i:])

            self.episode_files = val_files if self.is_validation else train_files
        else:
            split_idx = int(len(self.episode_files) * self.train_split)
            if self.is_validation:
                self.episode_files = self.episode_files[split_idx:]
            else:
                self.episode_files = self.episode_files[:split_idx]

        # Precompute frame indices for __len__ and __getitem__
        self.frame_indices = []
        filtered_files = []
        for ep_idx, f in enumerate(self.episode_files):
            with h5py.File(f, 'r') as hf:
                # [V5/V4 auto-detect]
                num_frames = len(hf['observations']['images']) if 'observations' in hf else len(hf['images'])
                
                # [Option B] Curvature Only Filtering
                if self.curvature_only:
                    if 'actions' not in hf:
                        print(f"⚠️ [NavH5Dataset] Skipping {f.name}: 'actions' key not found.")
                        continue
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
        100% Strict Action-Aware Prompting. No generic variations to prevent shortcut learning.
        """
        target_idx = min(self.window_size, len(actions) - 1)
        # actions shape handling — V5: [lx, ly, az], V4: [lx, az] (2D)
        if len(actions.shape) == 3:
            a = actions[target_idx][0]
        else:
            a = actions[target_idx]
        tx  = float(a[0])                          # linear_x
        ty  = float(a[1])                          # linear_y (strafe)
        taz = float(a[2]) if len(a) > 2 else 0.0  # angular_z (제자리 회전)

        curr_act_type = "forward"
        # 제자리 회전 (lx≈0, ly≈0, az≠0) — discrete label 변환과 동일
        if abs(tx) < 0.3 and abs(ty) < 0.3 and taz > 0.15:
            curr_act_type = "left"  # Positive az is Left (CCW)
        elif abs(tx) < 0.3 and abs(ty) < 0.3 and taz < -0.15:
            curr_act_type = "right" # Negative az is Right (CW)
        elif abs(tx) < 0.3 and abs(ty) < 0.3:
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
        

        return f"<grounding>Instruction: {random.choice(variations)}. Action:"

    def _get_path_type_instruction(self, ep_file_path):
        """에피소드 파일명의 path_type(left/right/straight)을 감지해 direction-specific instruction 반환."""
        stem = Path(ep_file_path).stem
        if "left_path" in stem:
            key = "left"
        elif "right_path" in stem:
            key = "right"
        elif "straight_path" in stem:
            key = "straight"
        else:
            key = "default"
            
        # [V5 BugFix] instruction_override 가 있으면 해당 값 사용, 없으면 하드코딩된 PATH_TYPE_INSTRUCTIONS 사용
        if self.instruction_override is not None and key in self.instruction_override:
            variations = self.instruction_override[key]
        else:
            variations = self.PATH_TYPE_INSTRUCTIONS[key]
            
        return f"<grounding>Instruction: {random.choice(variations)}. Action:"

    def __getitem__(self, idx):
        ep_idx, start_frame = self.frame_indices[idx]
        
        with h5py.File(self.episode_files[ep_idx], 'r') as f:
            # [V5/V4 auto-detect] V5: observations/images, V4: images
            images_src = f['observations']['images'] if 'observations' in f else f['images']
            total_len = len(images_src)
            total_frames_needed = self.window_size
            total_actions_needed = self.window_size + self.fwd_pred_next_n - 1

            # 이미지 로드 (window_size 만큼)
            images = []
            for t in range(start_frame, min(start_frame + total_frames_needed, total_len)):
                img_array = images_src[t]
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
                    actions.append(np.zeros(3))
            else:
                episode_actions = f['actions'][:]
                episode_len = episode_actions.shape[0]
                action_dim = episode_actions.shape[-1]

                for t in range(start_frame, min(start_frame + total_actions_needed, episode_len)):
                    a = episode_actions[t][:3].copy()
                    if action_dim < 3:
                        # V4: [lx, az] → [lx, az, 0] 으로 3D 패딩
                        a = np.pad(a, (0, 3 - len(a)))
                    actions.append(a)

                # 부족한 액션 패딩
                while len(actions) < total_actions_needed:
                    actions.append(np.zeros(3))
            
            actions = np.array(actions)
            # -------------------------------------------------------------------------
            
            # -------------------------------------------------------------------------
            # [Counterfactual Injection] 학습 중 명령어 감수성(Sensitivity) 강화를 위해 액션 오버라이드
            # -------------------------------------------------------------------------
            _apply_counterfactual_stop = (
                not self.is_validation
                and self._counterfactual_stop_prob > 0.0
                and random.random() < self._counterfactual_stop_prob
            )
            
            _apply_counterfactual_steer = (
                not self.is_validation
                and self._counterfactual_steer_prob > 0.0
                and random.random() < self._counterfactual_steer_prob
            )
            
            if _apply_counterfactual_stop:
                stop_variations = [
                    "Stop in front of the gray basket", "Halt immediately",
                    "Freeze and stay still", "Do not move", "정지해", "움직이지 마",
                    "Stop moving", "Wait here", "그 자리에서 멈춰",
                ]
                language_base = f"<grounding>Instruction: {random.choice(stop_variations)}. Action:"
                actions = np.zeros_like(actions)
                
            elif _apply_counterfactual_steer:
                # [V5 Update] 50% Strafe, 50% Turn-in-place 주입
                is_turn = random.random() < 0.5
                is_left = random.random() < 0.5

                if is_turn:
                    if is_left:
                        steer_vars = ["Rotate left", "Turn left in place", "왼쪽으로 회전해", "제자리에서 왼쪽으로 틀어"]
                        # [lx, ly, az] -> [0.0, 0.0, -0.2] (L-Angle)
                        actions = np.tile(np.array([0.0, 0.0, -0.2]), (actions.shape[0], 1))
                    else:
                        steer_vars = ["Rotate right", "Turn right in place", "오른쪽으로 회전해", "제자리에서 오른쪽으로 틀어"]
                        # [lx, ly, az] -> [0.0, 0.0, 0.2] (R-Angle)
                        actions = np.tile(np.array([0.0, 0.0, 0.2]), (actions.shape[0], 1))
                else:
                    if is_left:
                        steer_vars = ["Move left", "Steer to the left side", "왼쪽으로 가", "좌측으로 이동해"]
                        # [lx, ly, az] -> [0.0, 0.6, 0.0] (Left Strafe)
                        actions = np.tile(np.array([0.0, 0.6, 0.0]), (actions.shape[0], 1))
                    else:
                        steer_vars = ["Move right", "Steer to the right side", "오른쪽으로 가", "우측으로 이동해"]
                        # [lx, ly, az] -> [0.0, -0.6, 0.0] (Right Strafe)
                        actions = np.tile(np.array([0.0, -0.6, 0.0]), (actions.shape[0], 1))
                
                language_base = f"<grounding>Instruction: {random.choice(steer_vars)}. Action:"
                    
            else:
                # [Track 1] 100% Strict Action-Aware 강제 적용 ('action_aware_train' 이거나 'strict_action_aware' 인 경우)
                use_action_aware_train = (self.instruction_preset in ["action_aware_train", "strict_action_aware"])
                use_path_type_aware = (self.instruction_preset == "path_type_aware")
                
                if use_action_aware_train:
                    language_base = self._get_action_aware_instruction(actions)
                elif self.instruction_override is not None:
                    # BugFix: config의 instruction_override 로직 적용
                    # TODO: 이 부분은 path_type 기반 override. 추후 action 단위 override 원할 시 수정
                    language_base = self._get_path_type_instruction(self.episode_files[ep_idx]) 
                    # override dict에서 뽑아오는 로직이 원래 불량했음. 임시로 path_type_instruction로 연결
                elif use_path_type_aware:
                    language_base = self._get_path_type_instruction(self.episode_files[ep_idx])
                elif 'language_instruction' in f:
                    raw = f['language_instruction'][0]
                    language_base = raw.decode('utf-8') if isinstance(raw, bytes) else str(raw)
                    # [V5] Kosmos-2 LoRA는 <grounding> 접두사로 학습됨 → 일관성을 위해 추가
                    if self.grounding_prefix and not language_base.startswith('<grounding>'):
                        language_base = f"<grounding>{language_base}"
                else:
                    language_base = "Navigate to the gray basket"
                    
                # [Track 2] BBox 생성 (OpenCV 임시 활용)
                if self.use_bbox_target:
                    # 마지막 프레임 혹은 현재 프레임 영상 기반 bbox
                    target_img_np = images_src[min(start_frame + self.window_size - 1, total_len - 1)]
                    try:
                        import cv2
                        hsv = cv2.cvtColor(target_img_np, cv2.COLOR_RGB2HSV)
                        # 임시로 Grayish + Reddish 물체를 잡음 (넓은 임계값)
                        # 여기서는 화면 중앙 근처에 있는 컨투어를 우선하거나, 가장 큰 면적을 바구니로 가정
                        lower_bound = np.array([0, 0, 0])
                        upper_bound = np.array([180, 255, 200])
                        mask = cv2.inRange(hsv, lower_bound, upper_bound)
                        # 화면 아래쪽에 가중치(바구니는 바닥에 있음)
                        H, W = mask.shape
                        mask[0:H//3, :] = 0
                        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                        
                        xmin, ymin, xmax, ymax = W//3, H//3, 2*W//3, 2*H//3 # Default center bbox
                        if contours:
                            c = max(contours, key=cv2.contourArea)
                            if cv2.contourArea(c) > 100:
                                x, y, w, h = cv2.boundingRect(c)
                                xmin, ymin, xmax, ymax = x, y, x+w, y+h
                        
                        # BBox 토큰 계산 (Kosmos-2 32x32 Grid 매핑)
                        x1_idx = int((xmin / W) * 31)
                        y1_idx = int((ymin / H) * 31)
                        p1 = y1_idx * 32 + x1_idx
                        
                        x2_idx = int((xmax / W) * 31)
                        y2_idx = int((ymax / H) * 31)
                        p2 = y2_idx * 32 + x2_idx
                        
                        bbox_text = f"<box_2d><patch_index_{p1:04d}><patch_index_{p2:04d}></box_2d>"
                        # language_base 뒤에 Action 출력 대신 BBox를 정답으로 연결
                        if "Action:" in language_base:
                            language_base = language_base.split("Action:")[0] + f"Action: {bbox_text}"
                        else:
                            language_base = f"{language_base} Action: {bbox_text}"
                    except Exception as e:
                        # Fallback
                        bbox_text = f"<box_2d><patch_index_0528><patch_index_0656></box_2d>" # Center approx
                        language_base = f"{language_base} Action: {bbox_text}"

            # -------------------------------------------------------------------------
            # [LFS Update] Augmentation - Image Flip (좌우 반전)
            # -------------------------------------------------------------------------
            if self.augment:
                # 50% 확률로 좌우 반전
                if random.random() < 0.5:
                    # 1. 이미지 반전
                    images = [T.functional.hflip(img) for img in images]
                    
                    # 2. 액션/레이블 반전 (좌우가 바뀌면 LEFT ↔ RIGHT, FL ↔ FR 도 바뀌어야 함)
                    # 이 시점 actions는 raw (N,3) numpy [lx, ly, az]
                    # V5: ly(a[1])가 회전축, az(a[2])가 제자리회전축 → 둘 다 부호 반전
                    actions_tensor_aug = torch.from_numpy(np.array(actions)).float()
                    actions_tensor_aug[..., 1] = -actions_tensor_aug[..., 1]  # ly 반전
                    if actions_tensor_aug.shape[-1] > 2:
                        actions_tensor_aug[..., 2] = -actions_tensor_aug[..., 2]  # az 반전
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
                # a is (3,): [lx, ly, az]
                # V5: lx=linear_x, ly=linear_y(strafe), az=angular_z(turn)
                x  = float(a[0])
                y  = float(a[1])
                az = float(a[2])

                is_x = abs(x) > 0.3
                is_y = abs(y) > 0.3
                is_z = abs(az) > 0.1

                # 8-classes: 0:Stop, 1:F, 2:L, 3:R, 4:FL, 5:FR, 6:L-Angle, 7:R-Angle
                if not is_x and not is_y:
                    if az > 0.1:     # Left-Angle (CCW, positive)
                        label = 6
                    elif az < -0.1:  # Right-Angle (CW, negative)
                        label = 7
                    else:
                        label = 0
                elif x > 0.3:
                    if y > 0.3:     # FL (q)
                        label = 4
                    elif y < -0.3:  # FR (e)
                        label = 5
                    else:           # F (w)
                        label = 1
                elif abs(x) < 0.3:
                    if y > 0.3:     # L (a)
                        label = 2
                    elif y < -0.3:  # R (d)
                        label = 3
                    else:
                        label = 0
                else:
                    label = 0 # Default (includes backward)
                
                cls_labels.append(label)
            
            # [Backward Compatibility] 6-classes or other sizes
            if self.num_classes == 6:
                # 0:Stop, 1:F, 2:L, 3:R, 4:FL, 5:FR (omit 6,7)
                mapping = {0: 0, 1: 1, 2: 2, 4: 2, 3: 3, 5: 3, 6: 2, 7: 3} # Simplified mapping if needed
                cls_labels = [mapping.get(int(l), 0) for l in cls_labels]
            
            actions_tensor_full = torch.tensor(cls_labels, dtype=torch.long)
            
            # Create action_chunck (seq_len, chunk_size) for discrete
            action_chunks = []
            for t in range(self.window_size):
                chunk = actions_tensor_full[t : t + self.fwd_pred_next_n]
                if len(chunk) < self.fwd_pred_next_n:
                    pad_len = self.fwd_pred_next_n - len(chunk)
                    last_val = chunk[-1] if len(chunk) > 0 else torch.tensor(0, dtype=torch.long)
                    # use repeat to pad
                    padding = last_val.unsqueeze(0).repeat(pad_len)
                    chunk = torch.cat([chunk, padding], dim=0)
                action_chunks.extend(chunk)
            
            # Reshape into (seq_len, chunk_size)
            action_chunck = torch.stack(action_chunks).reshape(self.window_size, self.fwd_pred_next_n)
            actions_tensor = actions_tensor_full # (window_size + fwd_pred_next_n - 1,)
        else:
            # Continuous action: Predict next N actions for each frame in window
            # actions shape: (window_size + next_n - 1, 2 or 6 or higher)
            actions_tensor_full = torch.from_numpy(np.array(actions)).float()
            
            # [CRITICAL] Slice to 3D [lx, ly, az] for navigation (V5) / 2D [lx, az] for V4
            if actions_tensor_full.shape[-1] > 3:
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
            
            # Reshape into (seq_len, chunk_size, dims)
            action_chunck = torch.stack(action_chunks).reshape(self.window_size, self.fwd_pred_next_n, actions_tensor_full.shape[-1])
            actions_tensor = actions_tensor_full # (window_size + next_n - 1, dims)
        
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
