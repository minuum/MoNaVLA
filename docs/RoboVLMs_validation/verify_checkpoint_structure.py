#!/usr/bin/env python3
"""
Checkpoint Structure Analysis (Non-GPU)
========================================
Analyzes PyTorch checkpoint files to understand their structure without loading to GPU.
Compares Kosmos-2 and RoboVLMs checkpoints.

Usage:
    python3 verify_checkpoint_structure.py
"""

import torch
import json
from pathlib import Path
from collections import defaultdict
import numpy as np


def analyze_checkpoint_structure(ckpt_path, load_to_cpu=True):
    """
    Analyze checkpoint structure without loading to GPU.
    
    Returns detailed information about:
    - State dict keys
    - Parameter shapes and types
    - Model architecture insights
    - Memory requirements
    """
    print(f"\n{'='*70}")
    print(f"Analyzing: {Path(ckpt_path).name}")
    print(f"{'='*70}")
    
    if not Path(ckpt_path).exists():
        print(f"❌ File not found: {ckpt_path}")
        return None
    
    file_size_gb = Path(ckpt_path).stat().st_size / (1024**3)
    print(f"File size: {file_size_gb:.2f} GB")
    
    try:
        # Load checkpoint to CPU only
        print("Loading checkpoint to CPU...")
        if load_to_cpu:
            checkpoint = torch.load(ckpt_path, map_location='cpu')
        else:
            # Just inspect without fully loading
            checkpoint = torch.load(ckpt_path, map_location='cpu', weights_only=False)
        
        print("✅ Checkpoint loaded\n")
        
        # Analyze structure
        analysis = {
            'file_path': str(ckpt_path),
            'file_size_gb': file_size_gb,
            'checkpoint_type': None,
            'keys': list(checkpoint.keys()),
            'state_dict': {},
            'model_config': {},
            'statistics': {}
        }
        
        # Determine checkpoint type
        if 'state_dict' in checkpoint:
            analysis['checkpoint_type'] = 'lightning'
            state_dict = checkpoint['state_dict']
            print("📦 Checkpoint Type: PyTorch Lightning")
        elif isinstance(checkpoint, dict) and 'model' in checkpoint:
            analysis['checkpoint_type'] = 'standard'
            state_dict = checkpoint['model']
            print("📦 Checkpoint Type: Standard PyTorch")
        else:
            # Assume the checkpoint itself is the state_dict
            analysis['checkpoint_type'] = 'state_dict_only'
            state_dict = checkpoint
            print("📦 Checkpoint Type: State Dict Only")
        
        # Analyze state dict
        print(f"\n🔍 State Dict Analysis:")
        print(f"  Total parameters: {len(state_dict)}")
        
        # Group parameters by module
        module_groups = defaultdict(list)
        param_shapes = {}
        param_dtypes = {}
        total_params = 0
        
        for key, value in state_dict.items():
            # Group by top-level module
            module_name = key.split('.')[0] if '.' in key else 'root'
            module_groups[module_name].append(key)
            
            # Store shape and dtype
            if isinstance(value, torch.Tensor):
                param_shapes[key] = tuple(value.shape)
                param_dtypes[key] = str(value.dtype)
                total_params += value.numel()
            else:
                param_shapes[key] = 'non-tensor'
                param_dtypes[key] = type(value).__name__
        
        print(f"  Total parameter count: {total_params:,}")
        print(f"  Estimated memory: {total_params * 4 / (1024**3):.2f} GB (fp32)")
        
        # Print module groups
        print(f"\n📊 Parameter Groups:")
        for module, params in sorted(module_groups.items()):
            print(f"  {module:30s}: {len(params):4d} params")
        
        # Identify model components
        print(f"\n🧩 Model Components:")
        components = {
            'vlm': [],
            'action_head': [],
            'other': []
        }
        
        for key in state_dict.keys():
            key_lower = key.lower()
            if 'act_head' in key_lower or 'action_head' in key_lower or 'policy_head' in key_lower:
                components['action_head'].append(key)
            elif 'vision' in key_lower or 'text' in key_lower or 'backbone' in key_lower or 'model.model' in key:
                components['vlm'].append(key)
            else:
                components['other'].append(key)
        
        for comp_name, comp_keys in components.items():
            if comp_keys:
                print(f"  {comp_name:15s}: {len(comp_keys):4d} parameters")
                # Show first few keys as examples
                if len(comp_keys) <= 3:
                    for k in comp_keys:
                        shape = param_shapes.get(k, 'unknown')
                        print(f"    - {k}: {shape}")
                else:
                    for k in comp_keys[:2]:
                        shape = param_shapes.get(k, 'unknown')
                        print(f"    - {k}: {shape}")
                    print(f"    ... ({len(comp_keys) - 2} more)")
        
        # Store in analysis
        analysis['state_dict'] = {
            'total_params': len(state_dict),
            'total_param_count': total_params,
            'estimated_memory_gb': total_params * 4 / (1024**3),
            'module_groups': {k: len(v) for k, v in module_groups.items()},
            'components': {k: len(v) for k, v in components.items()},
            'sample_keys': {
                'vlm': components['vlm'][:5],
                'action_head': components['action_head'][:5],
                'other': components['other'][:3]
            }
        }
        
        # Check for additional metadata
        if analysis['checkpoint_type'] == 'lightning':
            print(f"\n⚙️  Lightning Metadata:")
            for key in ['epoch', 'global_step', 'pytorch-lightning_version', 'hyper_parameters']:
                if key in checkpoint:
                    value = checkpoint[key]
                    if isinstance(value, dict):
                        print(f"  {key}: {len(value)} items")
                    else:
                        print(f"  {key}: {value}")
        
        # Action head specific analysis
        if components['action_head']:
            print(f"\n🎯 Action Head Details:")
            action_head_params = 0
            for key in components['action_head']:
                value = state_dict[key]
                if isinstance(value, torch.Tensor):
                    action_head_params += value.numel()
                    if 'lstm' in key.lower():
                        print(f"  LSTM layer: {key}")
                        print(f"    Shape: {value.shape}")
            
            print(f"  Total action head params: {action_head_params:,}")
            analysis['statistics']['action_head_params'] = action_head_params
        
        return analysis
        
    except Exception as e:
        print(f"❌ Error loading checkpoint: {e}")
        import traceback
        traceback.print_exc()
        return None


def compare_checkpoints(ckpt1_path, ckpt2_path):
    """
    Compare two checkpoints side by side.
    """
    print("\n" + "="*70)
    print("CHECKPOINT COMPARISON")
    print("="*70)
    
    analysis1 = analyze_checkpoint_structure(ckpt1_path)
    analysis2 = analyze_checkpoint_structure(ckpt2_path)
    
    if analysis1 and analysis2:
        print("\n" + "="*70)
        print("COMPARISON SUMMARY")
        print("="*70)
        
        print(f"\n📁 File Sizes:")
        print(f"  Checkpoint 1: {analysis1['file_size_gb']:.2f} GB")
        print(f"  Checkpoint 2: {analysis2['file_size_gb']:.2f} GB")
        print(f"  Difference: {abs(analysis1['file_size_gb'] - analysis2['file_size_gb']):.2f} GB")
        
        print(f"\n🔢 Parameter Counts:")
        count1 = analysis1['state_dict']['total_param_count']
        count2 = analysis2['state_dict']['total_param_count']
        print(f"  Checkpoint 1: {count1:,}")
        print(f"  Checkpoint 2: {count2:,}")
        print(f"  Difference: {abs(count1 - count2):,}")
        
        print(f"\n🧩 Components:")
        for comp in ['vlm', 'action_head', 'other']:
            c1 = analysis1['state_dict']['components'].get(comp, 0)
            c2 = analysis2['state_dict']['components'].get(comp, 0)
            print(f"  {comp:15s}: {c1:4d} vs {c2:4d}")
        
        return {'checkpoint1': analysis1, 'checkpoint2': analysis2}
    
    return None


def main():
    """
    Main analysis routine.
    """
    print("="*70)
    print("Checkpoint Structure Analysis (Non-GPU)")
    print("="*70)
    
    # Define checkpoint paths (relative to /home/billy/25-1kp/vla)
    import os
    base_dir = "/home/billy/25-1kp/vla"
    checkpoints = {
        'kosmos2_finetuned': os.path.join(base_dir, "RoboVLMs_upstream/runs/mobile_vla_lora_20251203/kosmos/mobile_vla_finetune/2025-12-03/mobile_vla_lora_20251203/epoch_epoch=09-val_loss=val_loss=0.013.ckpt"),
        'robovlms_finetuned': os.path.join(base_dir, "best_robovlms_mobile_model_epoch_1.pt"),
    }
    
    analyses = {}
    
    # Analyze each checkpoint
    for name, path in checkpoints.items():
        print(f"\n{'#'*70}")
        print(f"# Analyzing: {name}")
        print(f"{'#'*70}")
        
        analysis = analyze_checkpoint_structure(path)
        if analysis:
            analyses[name] = analysis
    
    # Save results
    if analyses:
        output_file = "checkpoint_structure_analysis.json"
        
        # Convert to JSON-serializable format
        json_analyses = {}
        for name, analysis in analyses.items():
            json_analyses[name] = analysis
        
        with open(output_file, 'w') as f:
            json.dump(json_analyses, f, indent=2)
        
        print(f"\n✅ Analysis saved to: {output_file}")
    
    # Try comparison if we have two checkpoints
    if len(analyses) >= 2:
        print("\n" + "#"*70)
        print("# Comparing checkpoints")
        print("#"*70)
        
        names = list(analyses.keys())
        compare_checkpoints(checkpoints[names[0]], checkpoints[names[1]])


if __name__ == "__main__":
    main()
