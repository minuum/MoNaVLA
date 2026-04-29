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
import atexit
import datetime
from pathlib import Path

# ── MPI hang 방지: mpi4py가 설치된 환경에서 Lightning이 orted 데몬을 spawn해 블로킹됨
# MPI.COMM_WORLD.Get_size() 호출 시 hang → _MPI4PY_AVAILABLE=False로 패치해 detect() 스킵
import lightning.fabric.plugins.environments.mpi as _mpi_env_mod
_mpi_env_mod._MPI4PY_AVAILABLE = False

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

# Backbone — 'RoboVLM-Nav' / 'RoboKosMos' → NavRoboKosMos 주입
# NavRoboKosMos는 RoboKosMos의 subclass로 instruction conditioning 지원
from robovlms.model.backbone.robokosmos import RoboKosMos
from robovlm_nav.models.nav_robokosmos import NavRoboKosMos
setattr(robovlms.model.backbone, "RoboVLM-Nav", NavRoboKosMos)
setattr(robovlms.model.backbone, "RoboKosMos", NavRoboKosMos)

# Trainer
import robovlms.train.base_trainer as base_trainer_mod
base_trainer_mod.BaseTrainer = NavTrainer
setattr(robovlms.train, "NavTrainer", NavTrainer)
setattr(robovlms.train, "BaseTrainer", NavTrainer)

# main 모듈의 BaseTrainer 교체
import main
main.BaseTrainer = NavTrainer


class TeeStream:
    def __init__(self, stream, file_handle):
        self._stream = stream
        self._file_handle = file_handle
        self.encoding = getattr(stream, "encoding", "utf-8")

    def write(self, data):
        self._stream.write(data)
        self._file_handle.write(data)
        if "\n" in data:
            self.flush()
        return len(data)

    def flush(self):
        self._stream.flush()
        self._file_handle.flush()

    def isatty(self):
        return self._stream.isatty()

    def fileno(self):
        return self._stream.fileno()


def setup_stdio_logging(configs):
    rank = int(os.environ.get("RANK", "0"))
    log_dir_value = configs.get("log_dir")
    if log_dir_value is None:
        # Bootstrap a deterministic log dir before main.experiment() expands log_root/output_root.
        log_root = Path(configs["log_root"])
        log_dir_value = log_root / datetime.date.today().isoformat() / configs["exp_name"]
        configs["log_dir"] = str(log_dir_value)
    log_dir = Path(log_dir_value)
    log_dir.mkdir(parents=True, exist_ok=True)
    log_name = "train.log" if rank == 0 else f"train.rank{rank}.log"
    log_path = log_dir / log_name
    file_handle = open(log_path, "a", buffering=1, encoding="utf-8")

    original_stdout = sys.stdout
    original_stderr = sys.stderr
    sys.stdout = TeeStream(original_stdout, file_handle)
    sys.stderr = TeeStream(original_stderr, file_handle)

    def _cleanup():
        try:
            sys.stdout.flush()
            sys.stderr.flush()
        finally:
            file_handle.close()

    atexit.register(_cleanup)
    print(f"[train.py] stdout/stderr tee -> {log_path}", flush=True)


def configure_cuda_memory_limit(configs):
    if not os.environ.get("CUDA_VISIBLE_DEVICES", "") and not configs.get("gpus"):
        return

    fraction = configs.get("gpu_memory_fraction", None)
    if fraction is None:
        fraction = os.environ.get("MONAVLA_CUDA_MEMORY_FRACTION", None)
    if fraction is None:
        return

    try:
        fraction = float(fraction)
    except (TypeError, ValueError):
        print(f"[train.py] invalid gpu_memory_fraction={fraction!r}; ignoring", flush=True)
        return

    if not (0.0 < fraction <= 1.0):
        print(f"[train.py] gpu_memory_fraction must be in (0, 1], got {fraction}; ignoring", flush=True)
        return

    import torch

    if not torch.cuda.is_available():
        print("[train.py] gpu_memory_fraction requested but CUDA is unavailable; ignoring", flush=True)
        return

    device_count = torch.cuda.device_count()
    for device_idx in range(device_count):
        torch.cuda.set_per_process_memory_fraction(fraction, device=device_idx)
    print(f"[train.py] set_per_process_memory_fraction({fraction}) on {device_count} CUDA device(s)", flush=True)

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
    setup_stdio_logging(configs)
    configure_cuda_memory_limit(configs)

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
