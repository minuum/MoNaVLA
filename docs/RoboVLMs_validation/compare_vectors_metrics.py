#!/usr/bin/env python3
"""
Context Vector Comparison Metrics (Non-GPU)
============================================
Compares context vectors from different models using statistical metrics.
This script works with pre-extracted .npy files and doesn't require GPU.

Usage:
    python3 compare_vectors_metrics.py \\
        --kosmos context_vectors_kosmos.npy \\
        --robovlms context_vectors_robovlms.npy

Output: Detailed statistical comparison report and visualizations.
"""

import numpy as np
import argparse
import json
from pathlib import Path
from scipy import stats
from scipy.spatial.distance import cosine
import matplotlib.pyplot as plt
import seaborn as sns


def load_context_vectors(filepath):
    """
    Load context vectors from .npy file.
    
    Expected shape: (n_samples, feature_dim) or (n_samples, 1, feature_dim)
    Returns: (n_samples, feature_dim)
    """
    print(f"Loading: {filepath}")
    
    if not Path(filepath).exists():
        raise FileNotFoundError(f"File not found: {filepath}")
    
    vectors = np.load(filepath)
    print(f"  Original shape: {vectors.shape}")
    
    # Reshape if needed
    if vectors.ndim == 3:
        vectors = vectors.reshape(vectors.shape[0], -1)
    elif vectors.ndim == 2:
        pass  # Already correct shape
    else:
        raise ValueError(f"Unexpected shape: {vectors.shape}")
    
    print(f"  Final shape: {vectors.shape}")
    print(f"  N samples: {vectors.shape[0]}")
    print(f"  Feature dim: {vectors.shape[1]}")
    
    return vectors


def compute_distribution_metrics(vectors, name="Model"):
    """
    Compute distribution statistics for context vectors.
    """
    metrics = {
        'name': name,
        'n_samples': vectors.shape[0],
        'feature_dim': vectors.shape[1],
        
        # Global statistics
        'mean': float(np.mean(vectors)),
        'std': float(np.std(vectors)),
        'min': float(np.min(vectors)),
        'max': float(np.max(vectors)),
        'median': float(np.median(vectors)),
        
        # Per-feature statistics
        'feature_means': {
            'mean': float(np.mean(vectors.mean(axis=0))),
            'std': float(np.std(vectors.mean(axis=0))),
            'min': float(np.min(vectors.mean(axis=0))),
            'max': float(np.max(vectors.mean(axis=0)))
        },
        
        'feature_stds': {
            'mean': float(np.mean(vectors.std(axis=0))),
            'std': float(np.std(vectors.std(axis=0))),
            'min': float(np.min(vectors.std(axis=0))),
            'max': float(np.max(vectors.std(axis=0)))
        },
        
        # Dead/constant neuron analysis
        'dead_neurons': int(np.sum(np.all(vectors == 0, axis=0))),
        'constant_neurons': int(np.sum(np.var(vectors, axis=0) < 1e-6)),
        'saturated_neurons_pos': int(np.sum(np.mean(vectors, axis=0) > 10)),
        'saturated_neurons_neg': int(np.sum(np.mean(vectors, axis=0) < -10)),
        
        # Sparsity
        'sparsity': float(np.mean(np.abs(vectors) < 0.01)),
        
        # Kurtosis and skewness
        'kurtosis': float(stats.kurtosis(vectors.flatten())),
        'skewness': float(stats.skew(vectors.flatten()))
    }
    
    return metrics


def compare_distributions(vectors1, vectors2, name1="Model 1", name2="Model 2"):
    """
    Compare two sets of context vectors.
    """
    print("\n" + "="*70)
    print("DISTRIBUTION COMPARISON")
    print("="*70)
    
    comparison = {
        'model1': name1,
        'model2': name2,
        'metrics': {}
    }
    
    # Ensure same shape or compatible shapes
    if vectors1.shape[1] != vectors2.shape[1]:
        print(f"⚠️  Warning: Different feature dimensions:")
        print(f"  {name1}: {vectors1.shape[1]}")
        print(f"  {name2}: {vectors2.shape[1]}")
        return None
    
    # Sample-wise comparison (if same number of samples)
    if vectors1.shape[0] == vectors2.shape[0]:
        print(f"\n📊 Sample-wise Comparison ({vectors1.shape[0]} samples):")
        
        # Cosine similarity per sample
        cosine_sims = []
        for i in range(vectors1.shape[0]):
            sim = 1 - cosine(vectors1[i], vectors2[i])
            cosine_sims.append(sim)
        
        cosine_sims = np.array(cosine_sims)
        
        print(f"  Cosine Similarity:")
        print(f"    Mean: {np.mean(cosine_sims):.4f}")
        print(f"    Std: {np.std(cosine_sims):.4f}")
        print(f"    Min: {np.min(cosine_sims):.4f}")
        print(f"    Max: {np.max(cosine_sims):.4f}")
        
        comparison['metrics']['cosine_similarity'] = {
            'mean': float(np.mean(cosine_sims)),
            'std': float(np.std(cosine_sims)),
            'min': float(np.min(cosine_sims)),
            'max': float(np.max(cosine_sims))
        }
        
        # L2 distance
        l2_distances = np.linalg.norm(vectors1 - vectors2, axis=1)
        
        print(f"  L2 Distance:")
        print(f"    Mean: {np.mean(l2_distances):.4f}")
        print(f"    Std: {np.std(l2_distances):.4f}")
        print(f"    Min: {np.min(l2_distances):.4f}")
        print(f"    Max: {np.max(l2_distances):.4f}")
        
        comparison['metrics']['l2_distance'] = {
            'mean': float(np.mean(l2_distances)),
            'std': float(np.std(l2_distances)),
            'min': float(np.min(l2_distances)),
            'max': float(np.max(l2_distances))
        }
    
    # Feature-wise comparison (always possible)
    print(f"\n🔬 Feature-wise Comparison ({vectors1.shape[1]} features):")
    
    # Mean activation per feature
    mean1 = vectors1.mean(axis=0)
    mean2 = vectors2.mean(axis=0)
    
    mean_correlation = np.corrcoef(mean1, mean2)[0, 1]
    print(f"  Mean activation correlation: {mean_correlation:.4f}")
    
    comparison['metrics']['mean_feature_correlation'] = float(mean_correlation)
    
    # Std per feature
    std1 = vectors1.std(axis=0)
    std2 = vectors2.std(axis=0)
    
    std_correlation = np.corrcoef(std1, std2)[0, 1]
    print(f"  Std correlation: {std_correlation:.4f}")
    
    comparison['metrics']['std_feature_correlation'] = float(std_correlation)
    
    # Distribution comparison (KS test on flattened distributions)
    ks_statistic, ks_pvalue = stats.ks_2samp(vectors1.flatten(), vectors2.flatten())
    
    print(f"\n📈 Kolmogorov-Smirnov Test:")
    print(f"  Statistic: {ks_statistic:.4f}")
    print(f"  P-value: {ks_pvalue:.4e}")
    
    comparison['metrics']['ks_test'] = {
        'statistic': float(ks_statistic),
        'p_value': float(ks_pvalue)
    }
    
    # Wasserstein distance
    wasserstein_dist = stats.wasserstein_distance(vectors1.flatten(), vectors2.flatten())
    print(f"  Wasserstein Distance: {wasserstein_dist:.4f}")
    
    comparison['metrics']['wasserstein_distance'] = float(wasserstein_dist)
    
    return comparison


def generate_report(metrics1, metrics2, comparison):
    """
    Generate a comprehensive comparison report.
    """
    print("\n" + "="*70)
    print("COMPREHENSIVE COMPARISON REPORT")
    print("="*70)
    
    print(f"\n🎯 Model 1: {metrics1['name']}")
    print(f"  Samples: {metrics1['n_samples']}")
    print(f"  Features: {metrics1['feature_dim']}")
    print(f"  Mean ± Std: {metrics1['mean']:.4f} ± {metrics1['std']:.4f}")
    print(f"  Range: [{metrics1['min']:.4f}, {metrics1['max']:.4f}]")
    print(f"  Dead neurons: {metrics1['dead_neurons']}")
    print(f"  Constant neurons: {metrics1['constant_neurons']}")
    print(f"  Sparsity: {metrics1['sparsity']:.2%}")
    
    print(f"\n🎯 Model 2: {metrics2['name']}")
    print(f"  Samples: {metrics2['n_samples']}")
    print(f"  Features: {metrics2['feature_dim']}")
    print(f"  Mean ± Std: {metrics2['mean']:.4f} ± {metrics2['std']:.4f}")
    print(f"  Range: [{metrics2['min']:.4f}, {metrics2['max']:.4f}]")
    print(f"  Dead neurons: {metrics2['dead_neurons']}")
    print(f"  Constant neurons: {metrics2['constant_neurons']}")
    print(f"  Sparsity: {metrics2['sparsity']:.2%}")
    
    if comparison:
        print(f"\n🔍 Similarity Metrics:")
        if 'cosine_similarity' in comparison['metrics']:
            cs = comparison['metrics']['cosine_similarity']
            print(f"  Cosine Similarity: {cs['mean']:.4f} ± {cs['std']:.4f}")
        
        if 'mean_feature_correlation' in comparison['metrics']:
            print(f"  Feature Correlation: {comparison['metrics']['mean_feature_correlation']:.4f}")
        
        if 'wasserstein_distance' in comparison['metrics']:
            print(f"  Wasserstein Distance: {comparison['metrics']['wasserstein_distance']:.4f}")
        
        if 'ks_test' in comparison['metrics']:
            ks = comparison['metrics']['ks_test']
            print(f"  KS Test p-value: {ks['p_value']:.4e}")
    
    print("\n" + "="*70)


def create_visualizations(vectors1, vectors2, name1, name2, output_dir="."):
    """
    Create comparison visualizations.
    """
    print("\n📊 Generating visualizations...")
    
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)
    
    # 1. Distribution comparison (histogram)
    plt.figure(figsize=(12, 5))
    
    plt.subplot(1, 2, 1)
    plt.hist(vectors1.flatten(), bins=100, alpha=0.6, label=name1, density=True)
    plt.hist(vectors2.flatten(), bins=100, alpha=0.6, label=name2, density=True)
    plt.xlabel('Activation Value')
    plt.ylabel('Density')
    plt.title('Context Vector Distribution')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    # 2. Per-feature mean comparison
    plt.subplot(1, 2, 2)
    mean1 = vectors1.mean(axis=0)
    mean2 = vectors2.mean(axis=0)
    plt.scatter(mean1, mean2, alpha=0.3, s=1)
    plt.xlabel(f'{name1} Mean Activation')
    plt.ylabel(f'{name2} Mean Activation')
    plt.title('Per-Feature Mean Comparison')
    
    # Add diagonal line
    min_val = min(mean1.min(), mean2.min())
    max_val = max(mean1.max(), mean2.max())
    plt.plot([min_val, max_val], [min_val, max_val], 'r--', alpha=0.5, label='y=x')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    plt.tight_layout()
    output_path = output_dir / 'context_vector_comparison.png'
    plt.savefig(output_path, dpi=150)
    print(f"  ✅ Saved: {output_path}")
    plt.close()


def main():
    parser = argparse.ArgumentParser(description='Compare context vectors from different models')
    parser.add_argument('--kosmos', type=str, help='Path to Kosmos-2 context vectors (.npy)')
    parser.add_argument('--robovlms', type=str, help='Path to RoboVLMs context vectors (.npy)')
    parser.add_argument('--output', type=str, default='.', help='Output directory for results')
    
    args = parser.parse_args()
    
    # Use defaults if not provided
    kosmos_path = args.kosmos or "context_vectors_sampled.npy"
    robovlms_path = args.robovlms or "context_vectors_robovlms_sampled.npy"
    
    print("="*70)
    print("Context Vector Comparison Metrics (Non-GPU)")
    print("="*70)
    
    # Check if files exist
    if not Path(kosmos_path).exists():
        print(f"⚠️  Kosmos-2 vectors not found: {kosmos_path}")
        print("   Using existing sampled vectors as example...")
        kosmos_path = "context_vectors_sampled.npy"
    
    if not Path(robovlms_path).exists():
        print(f"⚠️  RoboVLMs vectors not found: {robovlms_path}")
        print("   This file needs to be generated with GPU inference.")
        print("   Creating analysis template for when available...")
        
        # Create template analysis
        template = {
            'status': 'template',
            'kosmos_ready': Path(kosmos_path).exists(),
            'robovlms_ready': False,
            'next_steps': [
                'Run context vector extraction with RoboVLMs checkpoint (GPU required)',
                'Save RoboVLMs context vectors to .npy file',
                'Re-run this script with both files available'
            ]
        }
        
        with open(Path(args.output) / 'comparison_template.json', 'w') as f:
            json.dump(template, f, indent=2)
        
        print("\n✅ Template saved: comparison_template.json")
        return
    
    # Load vectors
    try:
        vectors_kosmos = load_context_vectors(kosmos_path)
        vectors_robovlms = load_context_vectors(robovlms_path)
    except Exception as e:
        print(f"❌ Error loading vectors: {e}")
        return
    
    # Compute metrics
    print("\n" + "="*70)
    print("COMPUTING METRICS")
    print("="*70)
    
    metrics_kosmos = compute_distribution_metrics(vectors_kosmos, "Kosmos-2")
    metrics_robovlms = compute_distribution_metrics(vectors_robovlms, "RoboVLMs")
    
    # Compare
    comparison = compare_distributions(
        vectors_kosmos, vectors_robovlms,
        "Kosmos-2", "RoboVLMs"
    )
    
    # Generate report
    generate_report(metrics_kosmos, metrics_robovlms, comparison)
    
    # Create visualizations
    create_visualizations(
        vectors_kosmos, vectors_robovlms,
        "Kosmos-2", "RoboVLMs",
        args.output
    )
    
    # Save results
    results = {
        'kosmos2_metrics': metrics_kosmos,
        'robovlms_metrics': metrics_robovlms,
        'comparison': comparison
    }
    
    output_path = Path(args.output) / 'comparison_results.json'
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✅ Results saved: {output_path}")


if __name__ == "__main__":
    main()
