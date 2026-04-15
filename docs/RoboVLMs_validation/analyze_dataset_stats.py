#!/usr/bin/env python3
"""
Dataset Statistics Analysis (Non-GPU)
======================================
Analyzes all H5 files in the dataset to extract metadata and generate
comprehensive statistics without requiring GPU resources.

Output: dataset_statistics.json with episode counts, task types, 
        and sampling recommendations.
"""

import h5py
import json
import glob
import os
from pathlib import Path
from collections import defaultdict, Counter
import numpy as np
from tqdm import tqdm
from datetime import datetime


def parse_episode_filename(filename):
    """
    Extract metadata from episode filename.
    
    Example: episode_20251204_113519_1box_hori_left_core_medium.h5
    Returns: {
        'date': '20251204',
        'time': '113519',
        'n_boxes': 1,
        'orientation': 'hori',
        'direction': 'left',
        'mode': 'core',
        'difficulty': 'medium'
    }
    """
    parts = Path(filename).stem.split('_')
    
    metadata = {
        'filename': Path(filename).name,
        'date': None,
        'time': None,
        'n_boxes': None,
        'orientation': None,
        'direction': None,
        'mode': None,
        'difficulty': None
    }
    
    # Try to parse based on expected format
    if len(parts) >= 5:
        try:
            metadata['date'] = parts[1] if parts[1].isdigit() else None
            metadata['time'] = parts[2] if parts[2].isdigit() else None
            
            # Parse task components
            for part in parts[3:]:
                if 'box' in part:
                    metadata['n_boxes'] = int(part.replace('box', ''))
                elif part in ['hori', 'horizontal', 'vert', 'vertical']:
                    metadata['orientation'] = 'horizontal' if part.startswith('hori') else 'vertical'
                elif part in ['left', 'right']:
                    metadata['direction'] = part
                elif part in ['core', 'extended', 'basic']:
                    metadata['mode'] = part
                elif part in ['easy', 'medium', 'hard']:
                    metadata['difficulty'] = part
        except Exception as e:
            print(f"Warning: Could not fully parse {filename}: {e}")
    
    return metadata


def analyze_h5_file(filepath):
    """
    Analyze a single H5 file without loading heavy data.
    
    Returns: {
        'filepath': str,
        'metadata': dict,
        'n_frames': int,
        'n_actions': int,
        'image_shape': tuple,
        'action_shape': tuple,
        'file_size_mb': float,
        'has_action_events': bool,
        'trajectory_length': int,
        'action_stats': dict
    }
    """
    info = {
        'filepath': filepath,
        'metadata': parse_episode_filename(filepath),
        'n_frames': 0,
        'n_actions': 0,
        'image_shape': None,
        'action_shape': None,
        'file_size_mb': 0,
        'has_action_events': False,
        'trajectory_length': 0,
        'action_stats': {}
    }
    
    try:
        # Get file size
        info['file_size_mb'] = os.path.getsize(filepath) / (1024 * 1024)
        
        # Open and analyze H5
        with h5py.File(filepath, 'r') as f:
            # Check available keys
            keys = list(f.keys())
            
            # Analyze images
            if 'images' in f:
                images = f['images']
                info['n_frames'] = len(images)
                if len(images) > 0:
                    info['image_shape'] = images[0].shape
            
            # Analyze actions
            if 'actions' in f:
                actions = f['actions']
                info['n_actions'] = len(actions)
                if len(actions) > 0:
                    info['action_shape'] = actions[0].shape
                    
                    # Compute action statistics (without loading all)
                    sample_size = min(100, len(actions))
                    sample_actions = actions[:sample_size]
                    
                    info['action_stats'] = {
                        'mean': float(np.mean(sample_actions)),
                        'std': float(np.std(sample_actions)),
                        'min': float(np.min(sample_actions)),
                        'max': float(np.max(sample_actions))
                    }
            
            # Check action events
            if 'action_event_types' in f:
                info['has_action_events'] = True
                
            # Trajectory length
            info['trajectory_length'] = max(info['n_frames'], info['n_actions'])
            
    except Exception as e:
        print(f"Error analyzing {filepath}: {e}")
        info['error'] = str(e)
    
    return info


def generate_statistics(dataset_dir):
    """
    Generate comprehensive dataset statistics.
    """
    print("=" * 70)
    print("Dataset Statistics Analysis (Non-GPU)")
    print("=" * 70)
    print(f"Dataset directory: {dataset_dir}\n")
    
    # Find all H5 files
    h5_files = glob.glob(os.path.join(dataset_dir, "*.h5"))
    print(f"Found {len(h5_files)} H5 files\n")
    
    if not h5_files:
        print("No H5 files found!")
        return None
    
    # Analyze all files
    print("Analyzing files...")
    all_episodes = []
    for filepath in tqdm(h5_files):
        episode_info = analyze_h5_file(filepath)
        all_episodes.append(episode_info)
    
    # Aggregate statistics
    stats = {
        'timestamp': datetime.now().isoformat(),
        'dataset_dir': dataset_dir,
        'total_episodes': len(all_episodes),
        'total_size_mb': sum(ep['file_size_mb'] for ep in all_episodes),
        'episodes': all_episodes,
        'summary': {}
    }
    
    # Task type distribution
    task_types = defaultdict(int)
    directions = Counter()
    orientations = Counter()
    difficulties = Counter()
    n_boxes_dist = Counter()
    
    total_frames = 0
    trajectory_lengths = []
    
    for ep in all_episodes:
        meta = ep['metadata']
        
        # Count task components
        if meta['direction']:
            directions[meta['direction']] += 1
        if meta['orientation']:
            orientations[meta['orientation']] += 1
        if meta['difficulty']:
            difficulties[meta['difficulty']] += 1
        if meta['n_boxes']:
            n_boxes_dist[meta['n_boxes']] += 1
        
        # Build task type key
        task_key = f"{meta.get('orientation', 'unknown')}_{meta.get('direction', 'unknown')}"
        task_types[task_key] += 1
        
        # Trajectory info
        total_frames += ep['n_frames']
        trajectory_lengths.append(ep['trajectory_length'])
    
    # Summary statistics
    stats['summary'] = {
        'total_frames': total_frames,
        'avg_trajectory_length': float(np.mean(trajectory_lengths)) if trajectory_lengths else 0,
        'median_trajectory_length': float(np.median(trajectory_lengths)) if trajectory_lengths else 0,
        'min_trajectory_length': int(np.min(trajectory_lengths)) if trajectory_lengths else 0,
        'max_trajectory_length': int(np.max(trajectory_lengths)) if trajectory_lengths else 0,
        
        'task_types': dict(task_types),
        'directions': dict(directions),
        'orientations': dict(orientations),
        'difficulties': dict(difficulties),
        'n_boxes_distribution': dict(n_boxes_dist),
        
        'avg_file_size_mb': stats['total_size_mb'] / len(all_episodes) if all_episodes else 0
    }
    
    # Sampling recommendations
    stats['sampling_recommendations'] = generate_sampling_plan(all_episodes, stats['summary'])
    
    return stats


def generate_sampling_plan(episodes, summary):
    """
    Generate stratified sampling recommendations.
    """
    recommendations = {
        'total_episodes': len(episodes),
        'recommended_sample_size': min(100, len(episodes)),
        'sampling_strategy': 'stratified',
        'strata': {}
    }
    
    # Group by task type
    task_groups = defaultdict(list)
    for ep in episodes:
        meta = ep['metadata']
        task_key = f"{meta.get('orientation', 'unknown')}_{meta.get('direction', 'unknown')}"
        task_groups[task_key].append(ep['filepath'])
    
    # Calculate samples per stratum
    total = recommendations['recommended_sample_size']
    for task_type, files in task_groups.items():
        proportion = len(files) / len(episodes)
        n_samples = max(1, int(total * proportion))
        
        recommendations['strata'][task_type] = {
            'total_episodes': len(files),
            'proportion': proportion,
            'recommended_samples': n_samples,
            'example_files': files[:3]
        }
    
    return recommendations


def print_report(stats):
    """
    Print a human-readable report.
    """
    print("\n" + "=" * 70)
    print("ANALYSIS REPORT")
    print("=" * 70)
    
    print(f"\n📊 Dataset Overview:")
    print(f"  Total Episodes: {stats['total_episodes']}")
    print(f"  Total Frames: {stats['summary']['total_frames']:,}")
    print(f"  Total Size: {stats['total_size_mb']:.2f} MB")
    print(f"  Avg File Size: {stats['summary']['avg_file_size_mb']:.2f} MB")
    
    print(f"\n🎯 Task Distribution:")
    for task_type, count in stats['summary']['task_types'].items():
        pct = (count / stats['total_episodes']) * 100
        print(f"  {task_type:30s}: {count:3d} ({pct:5.1f}%)")
    
    print(f"\n🧭 Direction Distribution:")
    for direction, count in stats['summary']['directions'].items():
        pct = (count / stats['total_episodes']) * 100
        print(f"  {direction:10s}: {count:3d} ({pct:5.1f}%)")
    
    print(f"\n📐 Orientation Distribution:")
    for orientation, count in stats['summary']['orientations'].items():
        pct = (count / stats['total_episodes']) * 100
        print(f"  {orientation:15s}: {count:3d} ({pct:5.1f}%)")
    
    print(f"\n📦 Trajectory Statistics:")
    print(f"  Average Length: {stats['summary']['avg_trajectory_length']:.1f} frames")
    print(f"  Median Length: {stats['summary']['median_trajectory_length']:.1f} frames")
    print(f"  Range: [{stats['summary']['min_trajectory_length']}, {stats['summary']['max_trajectory_length']}]")
    
    print(f"\n🎲 Sampling Recommendations:")
    rec = stats['sampling_recommendations']
    print(f"  Strategy: {rec['sampling_strategy'].upper()}")
    print(f"  Total Sample Size: {rec['recommended_sample_size']}")
    print(f"  Strata: {len(rec['strata'])}")
    
    for stratum, info in rec['strata'].items():
        print(f"\n    {stratum}:")
        print(f"      Episodes: {info['total_episodes']}")
        print(f"      Proportion: {info['proportion']:.1%}")
        print(f"      Samples: {info['recommended_samples']}")
    
    print("\n" + "=" * 70)


def main():
    # Dataset directory
    dataset_dir = "/home/billy/25-1kp/vla/ROS_action/mobile_vla_dataset"
    
    # Generate statistics
    stats = generate_statistics(dataset_dir)
    
    if stats:
        # Print report
        print_report(stats)
        
        # Save to JSON
        output_file = "dataset_statistics.json"
        with open(output_file, 'w') as f:
            json.dump(stats, f, indent=2)
        
        print(f"\n✅ Saved to: {output_file}")
        print(f"   Size: {os.path.getsize(output_file) / 1024:.1f} KB")
    else:
        print("❌ Failed to generate statistics")


if __name__ == "__main__":
    main()
