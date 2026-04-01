#!/usr/bin/env python3
"""
RoboVLM-Nav Training Entry Point

아키텍처:
- third_party/RoboVLMs : 원본 그대로 유지 (수정 금지)
- robovlm_nav/         : 우리의 모든 커스텀 코드 (datasets, models, trainer 등)

이 스크립트는 robovlm_nav의 커스텀 컴포넌트들을 robovlms 네임스페이스에
동적 주입하여 third_party/RoboVLMs의 main.py가 그대로 작동하게 합니다.
"""

import sys
import os
from pathlib import Path

# ── Path 설정 ─────────────────────────────────────────────────
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(ROOT_DIR / "third_party" / "RoboVLMs"))

import robovlms.data
import robovlms.model.policy_head
import robovlms.model.backbone
import robovlms.train

# ── 커스텀 컴포넌트 import ─────────────────────────────────────
# Dataset
from robovlm_nav.datasets.nav_dataset import NavDataset
from robovlm_nav.datasets.nav_h5_dataset_impl import MobileVLAH5Dataset as NavH5DatasetImpl

# Policy Heads
from robovlm_nav.models.policy_head.nav_policy_impl import (
    MobileVLALSTMDecoder as NavLSTMDecoder,
    MobileVLAClassificationDecoder as NavClassificationDecoder,
)
from robovlm_nav.models.policy_head.hybrid_action_head import HybridActionHead

# Trainer
from robovlm_nav.trainer.nav_trainer import NavTrainer

# ── robovlms 네임스페이스에 동적 주입 ──────────────────────────
# Datasets (configs에서 type으로 참조하는 이름들)
setattr(robovlms.data, "NavDataset", NavDataset)
setattr(robovlms.data, "MobileVLAH5Dataset", NavH5DatasetImpl)   # upstream과 동일 인터페이스 유지

# Policy Heads
setattr(robovlms.model.policy_head, "NavPolicy", NavClassificationDecoder)
setattr(robovlms.model.policy_head, "NavPolicyRegression", NavLSTMDecoder)
setattr(robovlms.model.policy_head, "MobileVLAClassificationDecoder", NavClassificationDecoder)
setattr(robovlms.model.policy_head, "MobileVLALSTMDecoder", NavLSTMDecoder)
setattr(robovlms.model.policy_head, "HybridActionHead", HybridActionHead)

# Backbone — 'RoboVLM-Nav' → RoboKosMos 주입
# base_trainer.py L26: self.model_fn = getattr(RoboVLM_Backbone, configs["robovlm_name"])
from robovlms.model.backbone.robokosmos import RoboKosMos
setattr(robovlms.model.backbone, "RoboVLM-Nav", RoboKosMos)

# Trainer
import robovlms.train.base_trainer as base_trainer_mod
base_trainer_mod.BaseTrainer = NavTrainer
setattr(robovlms.train, "NavTrainer", NavTrainer)
setattr(robovlms.train, "BaseTrainer", NavTrainer)

# main 모듈의 BaseTrainer 교체
import main
main.BaseTrainer = NavTrainer

if __name__ == "__main__":
    # third_party/RoboVLMs/main.py의 함수들을 직접 import해서 사용.
    # chdir을 PROJECT_ROOT로 유지: parent 상대 경로가 configs/ 기준으로 resolve됨.
    # EXP-07과 동일한 방식: python3 robovlm_nav/train.py <config> 실행 시 cwd=PROJECT_ROOT
    os.chdir(ROOT_DIR)  # cwd = /home/billy/25-1kp/vla (configs/가 있는 위치)
    from main import parse_args, load_config, update_configs, experiment, dist, DDPStrategy
    import torch
    args = parse_args()
    configs = load_config(args.get("config"))
    configs = update_configs(configs, args)

    # DDP 초기화 (main.py의 __main__ 블록과 동일)
    is_ddp_strategy = False
    trainer_strategy_conf = configs.get("trainer", {}).get("strategy")
    if isinstance(trainer_strategy_conf, str) and "ddp" in trainer_strategy_conf.lower():
        is_ddp_strategy = True
    elif isinstance(trainer_strategy_conf, DDPStrategy):
        is_ddp_strategy = True
    config_strategy_conf = configs.get("strategy")
    if isinstance(config_strategy_conf, str) and "ddp" in config_strategy_conf.lower():
        is_ddp_strategy = True

    if configs.get("accelerator") != "mps" and is_ddp_strategy:
        if dist.is_available() and not dist.is_initialized():
            backend = 'nccl' if torch.cuda.is_available() else 'gloo'
            dist.init_process_group(backend=backend)

    experiment(variant=configs)
