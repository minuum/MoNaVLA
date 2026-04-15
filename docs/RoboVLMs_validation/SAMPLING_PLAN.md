# Context Vector Sampling Plan

## Objective
Design an efficient and representative sampling strategy to extract context vectors from ~500 mobile navigation episodes without overwhelming computational resources.

## Dataset Overview

### Total Available Data
- **Total episodes**: ~500
- **Episode types**: Based on filename pattern
  - Direction: left, right
  - Orientation: horizontal, vertical
  - Difficulty: easy, medium, hard
  - Mode: core, extended

### Episode Structure
- **Images per episode**: Variable (typically 30-200 frames)
- **Actions per episode**: Same as images
- **Episode duration**: ~10-60 seconds
- **Image size**: 640x480x3 (ResNet input: 224x224x3)

## Sampling Strategy

### Approach: Stratified Sampling

**Rationale**: Ensure representation across different task types, directions, and difficulty levels.

### Strata Definition

1. **Primary Stratum: Task Type** (Direction × Orientation)
   - Horizontal + Left
   - Horizontal + Right
   - Vertical + Left
   - Vertical + Right

2. **Secondary Stratum: Difficulty**
   - Easy
   - Medium
   - Hard

3. **Tertiary: Mode**
   - Core
   - Extended

### Sample Size Calculation

**Target**: 100 episodes (manageable for initial analysis)

**Distribution**:
```
For each task type:
  - Proportional allocation based on dataset composition
  - Minimum 10 episodes per stratum (if available)
  - Maximum 30 episodes per stratum (to avoid over-representation)

For each episode:
  - Extract 5 context vectors
  - Total: 100 episodes × 5 = 500 context vectors
```

### Frame Selection Within Episode

For each selected episode, extract context vectors from:

1. **First frame** (t=0): Initial observation
2. **25% progress** (t=0.25*T): Early phase
3. **50% progress** (t=0.5*T): Middle phase
4. **75% progress** (t=0.75*T): Late phase
5. **Last frame** (t=T): Final observation

**Rationale**: Captures temporal progression of the task.

## Sampling Algorithm

### Step 1: Episode Stratification
```python
episodes = load_all_episodes()

# Group by task type
task_groups = {}
for ep in episodes:
    task_type = extract_task_type(ep.filename)
    if task_type not in task_groups:
        task_groups[task_type] = []
    task_groups[task_type].append(ep)

# Print distribution
for task_type, eps in task_groups.items():
    print(f"{task_type}: {len(eps)} episodes")
```

### Step 2: Proportional Allocation
```python
total_samples = 100
sampled_episodes = {}

for task_type, eps in task_groups.items():
    # Proportional allocation
    proportion = len(eps) / len(episodes)
    n_samples = max(10, min(30, int(total_samples * proportion)))
    
    # Random sampling
    sampled = random.sample(eps, min(n_samples, len(eps)))
    sampled_episodes[task_type] = sampled
    
    print(f"{task_type}: sampled {len(sampled)} / {len(eps)}")
```

### Step 3: Frame Extraction
```python
context_vectors = []

for task_type, eps in sampled_episodes.items():
    for ep in eps:
        # Load episode
        images = load_episode_images(ep)
        T = len(images)
        
        # Select frames
        frame_indices = [
            0,                # Start
            int(0.25 * T),    # 25%
            int(0.50 * T),    # 50%
            int(0.75 * T),    # 75%
            T - 1             # End
        ]
        
        for idx in frame_indices:
            # Extract context vector
            img = images[idx]
            context = extract_context_vector(model, img)
            context_vectors.append({
                'episode': ep.filename,
                'task_type': task_type,
                'frame_idx': idx,
                'progress': idx / T,
                'vector': context
            })

# Save
np.save('context_vectors_sampled.npy', 
        np.array([cv['vector'] for cv in context_vectors]))
```

## Expected Output

### Data Structure
```python
{
    'metadata': {
        'total_episodes': 100,
        'total_vectors': 500,
        'sampling_strategy': 'stratified',
        'timestamp': '2025-12-04T15:00:00'
    },
    
    'vectors': np.array((500, 2048), dtype=np.float32),
    
    'annotations': [
        {
            'episode': 'episode_20251204_113519_1box_hori_left_core_medium.h5',
            'task_type': 'horizontal_left',
            'difficulty': 'medium',
            'frame_idx': 0,
            'progress': 0.0,
            'vector_idx': 0
        },
        # ... 499 more
    ]
}
```

### File Organization
```
docs/RoboVLMs_validation/
├── sampled_data/
│   ├── kosmos2/
│   │   ├── context_vectors.npy          # (500, 2048)
│   │   ├── metadata.json
│   │   └── episode_list.txt
│   │
│   └── robovlms/
│       ├── context_vectors.npy          # (500, 2048)
│       ├── metadata.json
│       └── episode_list.txt
```

## Validation Checks

### 1. Coverage Check
```python
# Ensure all task types are represented
task_types = set(cv['task_type'] for cv in context_vectors)
assert len(task_types) >= 3, "Insufficient task type coverage"

# Ensure temporal coverage
for ep in unique_episodes:
    progress_points = [cv['progress'] for cv in context_vectors 
                       if cv['episode'] == ep]
    assert min(progress_points) < 0.1, f"{ep}: Missing start"
    assert max(progress_points) > 0.9, f"{ep}: Missing end"
```

### 2. Balance Check
```python
# Check distribution
task_counts = Counter(cv['task_type'] for cv in context_vectors)
min_count = min(task_counts.values())
max_count = max(task_counts.values())

balance_ratio = min_count / max_count
assert balance_ratio > 0.3, f"Imbalanced sampling: {balance_ratio:.2f}"
```

### 3. Quality Check
```python
# Check for NaN or Inf
vectors = np.array([cv['vector'] for cv in context_vectors])
assert not np.any(np.isnan(vectors)), "NaN detected"
assert not np.any(np.isinf(vectors)), "Inf detected"

# Check reasonable range
assert np.abs(vectors.mean()) < 1.0, "Mean too large"
assert 0.5 < vectors.std() < 2.0, "Std out of range"
```

## Alternative Strategies

### Option 1: Random Sampling (Baseline)
- **Pros**: Simple, unbiased
- **Cons**: May miss rare task types

### Option 2: Cluster-Based Sampling
- **Approach**: Cluster episodes by trajectory similarity, sample from each cluster
- **Pros**: Ensures diversity
- **Cons**: Requires pre-processing (DTW or trajectory embeddings)

### Option 3: Active Learning Style
- **Approach**: Sample uncertain or diverse examples
- **Pros**: Maximizes information
- **Cons**: Requires initial model and multiple passes

**Chosen**: Stratified (Option 1) for simplicity and interpretability.

## Implementation Timeline

### Phase 1: Preparation (Non-GPU) - 30 min
1. ✅ Run `analyze_dataset_stats.py`
2. ✅ Review dataset distribution
3. ✅ Define strata and allocation
4. ✅ Create episode selection list

### Phase 2: Extraction (GPU Required) - 1-2 hours
1. ⏳ Load model checkpoints (Kosmos-2 and RoboVLMs)
2. ⏳ Extract context vectors with hooks
3. ⏳ Save to .npy files with metadata

### Phase 3: Validation (Non-GPU) - 15 min
1. ⏳ Run coverage checks
2. ⏳ Run balance checks
3. ⏳ Run quality checks
4. ⏳ Generate summary report

### Phase 4: Comparison (Non-GPU) - 30 min
1. ⏳ Run `compare_vectors_metrics.py`
2. ⏳ Generate visualizations
3. ⏳ Write analysis report

## Success Criteria

✅ **Sampling is successful if**:
1. All task types have ≥10 samples
2. Temporal coverage: 0%, 25%, 50%, 75%, 100% for each episode
3. Total samples: 500 ± 50
4. No NaN or Inf values
5. Distribution is well-behaved (mean ≈ 0, std ≈ 1)

## Next Steps

1. ⬜ Run `analyze_dataset_stats.py` to get exact distribution
2. ⬜ Adjust allocation based on actual data
3. ⬜ Create `selected_episodes.json` with episode list
4. ⬜ Implement extraction script
5. ⬜ Run extraction (GPU required)
6. ⬜ Validate and compare

---

**Last Updated**: 2025-12-04  
**Author**: Mobile-VLA Validation Team  
**Status**: Planning Complete, Ready for Execution
