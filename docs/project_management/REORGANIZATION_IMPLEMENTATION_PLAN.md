# Project Reorganization & Compatibility Implementation Plan

## 🎯 Goal
Clean up the root directory and ensure all configuration files and scripts are compatible with the new structured layout.

## 📁 Proposed Structure
- `scripts/`: All bash entry points for training and setup.
- `tools/`: Python utilities for data analysis and debugging.
- `docs/`: All documentation (already mostly structured).
- `logs/`: Active and historical log files.
- `Mobile_VLA/configs/`: Canonical location for experiment configurations.

## 🛠️ Actions

### 1. Create Directories
```bash
mkdir -p tools logs/training_history
```

### 2. Move Scripts to `scripts/`
- `train_v3_exp*.sh`
- `train_v2_*.sh`
- `setup_*.sh`
- `billy_*.sh`
- `FINAL_SUMMARY.sh`
- `run_inference_test_poetry.sh`
- `wait_and_test.sh`
- `jetson_setup_template.sh`

### 3. Move Tools to `tools/`
- `analyze_logs.py`
- `check_h5*.py`
- `check_keys.py`
- `compare_datasets.py`
- `inspect_h5.py`
- `overfitting_analysis.py`
- `scan_*.py`
- `summarize_v3.py`
- `verify_normalization.py`

### 4. Move Logs to `logs/`
- `*.log`
- `*.txt` (except READMEs)
- `*.pid`

### 5. Compatibility Fixes
- [ ] **Config Files**: Global replace `/home/soda/vla` -> `/home/billy/25-1kp/vla` in all JSONs.
- [ ] **Script Paths**: Update `scripts/train_*.sh` to `cd` to root or use correct relative paths.

## ⚠️ Risks
- Breaking the `PYTHONPATH` for utility scripts.
- Breaking the `parent` config inheritance in `main.py`.
- Breaking the automated training monitor if it expects logs in certain places.
