import h5py
import os
import glob
import numpy as np
from collections import Counter

# V5 데이터셋 경로
DATASET_PATH = "/home/billy/25-1kp/MoNaVLA/ROS_action/mobile_vla_dataset_v5"

# nav_h5_dataset_impl.py의 6-class 매핑과 동일하게 설정
ACTION_NAMES = {
    0: "STOP",
    1: "FORWARD",
    2: "LEFT",
    3: "RIGHT",
    4: "FORWARD_LEFT",
    5: "FORWARD_RIGHT"
}

def discretize(x, y):
    is_x_pos = x > 0.3
    is_x_neg = x < -0.3
    is_y_pos = y > 0.3
    is_y_neg = y < -0.3
    
    # 9-classes: 0:Stop, 1:F, 2:B, 3:L, 4:R, 5:FL, 6:FR, 7:BL, 8:BR
    if not is_x_pos and not is_x_neg and not is_y_pos and not is_y_neg:
        label = 0
    elif is_x_pos and not (is_y_pos or is_y_neg):
        label = 1
    elif is_x_neg and not (is_y_pos or is_y_neg):
        label = 2
    elif not (is_x_pos or is_x_neg) and is_y_pos:
        label = 3
    elif not (is_x_pos or is_x_neg) and is_y_neg:
        label = 4
    elif is_x_pos and is_y_pos:
        label = 5
    elif is_x_pos and is_y_neg:
        label = 6
    elif is_x_neg and is_y_pos:
        label = 7
    elif is_x_neg and is_y_neg:
        label = 8
    else:
        label = 0
        
    # 9 to 6 mapping
    # 0:Stop, 1:F, 2:B(Stop), 3:L, 4:R, 5:FL, 6:FR
    mapping = {0: 0, 1: 1, 2: 0, 3: 2, 4: 3, 5: 4, 6: 5, 7: 2, 8: 3}
    return mapping.get(label, 0)

def analyze_v5():
    h5_files = sorted(glob.glob(os.path.join(DATASET_PATH, "*.h5")))
    print(f"Total H5 files found: {len(h5_files)}")
    
    global_action_counts = Counter()
    path_type_stats = {}
    
    for f in h5_files:
        filename = os.path.basename(f)
        try:
            # 파일명 파싱: episode_TIMESTAMP_PATH_TYPE__core__fixed_center.h5
            parts = filename.split("__")
            path_type = parts[0].replace("episode_", "")
            # 앞의 TIMESTAMP (e.g. 260408_123008) 제거
            path_parts = path_type.split("_")
            path_type = "_".join(path_parts[2:]) 
            
            if path_type not in path_type_stats:
                path_type_stats[path_type] = {"episodes": 0, "actions": Counter()}
            
            path_type_stats[path_type]["episodes"] += 1
            
            with h5py.File(f, 'r') as hf:
                # V5 수집기는 'actions' 키를 사용함
                action_data = hf['actions'][:]
                
                for act in action_data:
                    # [v, w, z]
                    v, w = float(act[0]), float(act[1])
                    cls = discretize(v, w)
                    
                    global_action_counts[cls] += 1
                    path_type_stats[path_type]["actions"][cls] += 1
                    
        except Exception as e:
            # print(f"Error reading {filename}: {e}")
            pass

    print("\n" + "="*60)
    print(f"{'ACTION DISTRIBUTION REPORT (V5)':^60}")
    print("="*60)
    
    total_samples = sum(global_action_counts.values())
    print(f"Total Valid Action Frames: {total_samples}")
    print("-" * 60)
    for i in range(6):
        count = global_action_counts[i]
        perc = (count / total_samples * 100) if total_samples > 0 else 0
        name = ACTION_NAMES.get(i, f"UNKNOWN({i})")
        print(f"{name:20}: {count:10} ({perc:8.2f}%)")
    
    print("\n" + "="*60)
    print(f"{'DISTRIBUTION BY PATH TYPE':^60}")
    print("="*60)
    
    # 정렬하여 출력
    for pt in sorted(path_type_stats.keys()):
        stats = path_type_stats[pt]
        print(f"\n▶ [{pt}] ({stats['episodes']} episodes)")
        pt_total = sum(stats['actions'].values())
        for i in range(6):
            c = stats['actions'][i]
            p = (c / pt_total * 100) if pt_total > 0 else 0
            if c > 0:
                print(f"   - {ACTION_NAMES[i]:20}: {c:6} ({p:6.1f}%)")

if __name__ == "__main__":
    analyze_v5()
