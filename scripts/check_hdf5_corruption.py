
import h5py
import glob
import os

data_dir = "/home/billy/25-1kp/MoNaVLA/ROS_action/basket_dataset_v2"
pattern = "episode_*.h5"

files = sorted(glob.glob(os.path.join(data_dir, pattern)))
print(f"Checking {len(files)} files...")

corrupted = []
for f_path in files:
    try:
        with h5py.File(f_path, 'r') as f:
            _ = list(f.keys())
    except Exception as e:
        print(f"❌ Corrupted: {os.path.basename(f_path)} - {e}")
        corrupted.append(f_path)

if corrupted:
    print(f"\nFound {len(corrupted)} corrupted files.")
else:
    print("\nNo corrupted files found with single open test.")
