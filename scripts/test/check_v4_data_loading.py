import json
from pathlib import Path
import sys

import torch

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from robovlm_nav.datasets.nav_h5_dataset_impl import MobileVLAH5Dataset

def test_v4_dataset():
    project_root = PROJECT_ROOT
    config_path = project_root / "configs" / "mobile_vla_v4_exp01.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    train_cfg = config["train_dataset"]

    data_dir = train_cfg["data_dir"]
    window_size = train_cfg["window_size"]
    action_chunk_size = train_cfg["fwd_pred_next_n"]
    min_episode_frames = train_cfg["min_episode_frames"]
    instruction_preset = train_cfg["instruction_preset"]

    print(f"Testing dataset config: {config_path}")
    print(f"Testing dataset at: {data_dir}")

    dataset = MobileVLAH5Dataset(
        data_dir=data_dir,
        episode_pattern=train_cfg["episode_pattern"],
        window_size=window_size,
        action_chunk_size=action_chunk_size,
        discrete_action=True,
        min_episode_frames=min_episode_frames,
        instruction_preset=instruction_preset,
        is_validation=False
    )

    print(f"Total valid samples: {len(dataset)}")

    # 첫 번째 샘플 로드 테스트
    sample = dataset[0]
    print("\nSample check:")
    expected_frames = window_size + action_chunk_size
    print(f"RGB Shape: {sample['rgb'].shape}")  # Expected: ({expected_frames}, 3, 224, 224)
    print(f"Actions Shape: {sample['actions'].shape}")
    print(f"Action: {sample['actions']}")
    print(f"Instruction: {sample['lang']}")

    # 마지막 샘플 로드 테스트 (가변 길이 대응 확인)
    last_sample = dataset[len(dataset)-1]
    print("\nLast sample check:")
    print(f"RGB Shape: {last_sample['rgb'].shape}")
    print(f"Instruction: {last_sample['lang']}")

if __name__ == "__main__":
    test_v4_dataset()
