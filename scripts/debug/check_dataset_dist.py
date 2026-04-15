import h5py
import glob
import os
import numpy as np
from tqdm import tqdm

DATA_DIR = "/home/billy/25-1kp/MoNaVLA/ROS_action/mobile_vla_dataset_v5"
files = glob.glob(os.path.join(DATA_DIR, "episode_*.h5"))

counts = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
labels = ["Stop", "Forward", "Left", "Right", "Diag FL", "Diag FR"]

for fpath in tqdm(files):
    with h5py.File(fpath, 'r') as f:
        actions = f['action'][:] # (L, 2)
        for a in actions:
            x, y = a[0], a[1]
            if abs(x) < 0.5 and abs(y) < 0.5: label = 0
            elif x > 0.5 and abs(y) < 0.1: label = 1
            elif abs(x) < 0.1 and y > 0.5: label = 2
            elif abs(x) < 0.1 and y < -0.5: label = 3
            elif x > 0.5 and y > 0.5: label = 4
            elif x > 0.5 and y < -0.5: label = 5
            else: label = 0
            counts[label] += 1

print("\nDataset Label Distribution (Discrete Mapping):")
for i, count in counts.items():
    print(f"{labels[i]}: {count} ({count/sum(counts.values())*100:.2f}%)")
