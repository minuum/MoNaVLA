import h5py
import numpy as np
import os
import glob
from collections import Counter
from tqdm import tqdm

# --- Configuration ---
DATASET_DIR = "/home/billy/25-1kp/MoNaVLA/ROS_action/mobile_vla_dataset_v5"

# 8-Class Mapping & Instructions
# 0: Stop, 1: F, 2: L, 3: R, 4: FL, 5: FR, 6: L-Angle, 7: R-Angle
INSTRUCTION_MAP = {
    0: "<grounding>Halt in front of the gray basket. 바구니 앞에서 정지해.",
    1: "<grounding>Navigate straight forward to the gray basket. 바구니를 향해 직진해.",
    2: "<grounding>Steer toward the left side to approach the basket. 왼쪽으로 이동해서 바구니에 접근해.",
    3: "<grounding>Steer toward the right side to approach the basket. 오른쪽으로 이동해서 바구니에 접근해.",
    4: "<grounding>Angle toward left-front side to reach the target. 왼쪽 대각선 방향으로 비스듬히 접근해.",
    5: "<grounding>Angle toward right-front side to reach the target. 오른쪽 대각선 방향으로 비스듬히 접근해.",
    6: "<grounding>Rotate left toward the basket. 왼쪽으로 회전해서 바구니 방향을 맞춰.",
    7: "<grounding>Rotate right toward the basket. 오른쪽으로 회전해서 바구니 방향을 맞춰."
}

def get_8_class_label(lx, ly, az):
    """ triplet [linear_x, linear_y, angular_z] -> 8-class label """
    is_x = abs(lx) > 0.3
    is_y = abs(ly) > 0.3
    is_z = abs(az) > 0.1
    
    # 1. 제자리 회전 (Center row in logic)
    if not is_x and not is_y and is_z:
        return 6 if az < 0 else 7 # t: -0.2 (L), r: 0.2 (R)
        
    # 2. 정지
    if not is_x and not is_y and not is_z:
        return 0
        
    # 3. 전진/대각선 (Top row in logic)
    if lx > 0.3:
        if ly > 0.3:  return 4 # FL (q)
        if ly < -0.3: return 5 # FR (e)
        return 1 # F (w)
        
    # 4. 좌우 이동 (Side movements)
    if abs(lx) < 0.3:
        if ly > 0.3:  return 2 # L (a)
        if ly < -0.3: return 3 # R (d)
        
    return 0 # Default to Stop (includes backward cases if any)

def process_h5_files():
    h5_files = glob.glob(os.path.join(DATASET_DIR, "*.h5"))
    print(f"Found {len(h5_files)} files in {DATASET_DIR}")
    
    updated_count = 0
    
    for f_path in tqdm(h5_files, desc="Updating Instructions"):
        try:
            with h5py.File(f_path, 'a') as f:
                if 'actions' not in f:
                    continue
                
                actions = f['actions'][:]
                # 전체 에피소드에서 가장 빈번한 액션 판별
                labels = [get_8_class_label(a[0], a[1], a[2] if len(a)>2 else 0) for a in actions]
                
                # 'Stop'이 아닌 액션이 있다면 그 중 가장 많은 것 선택, 없다면 Stop
                non_stop_labels = [l for l in labels if l != 0]
                if non_stop_labels:
                    final_label = Counter(non_stop_labels).most_common(1)[0][0]
                else:
                    final_label = 0
                
                new_instr = INSTRUCTION_MAP[final_label]
                
                # H5 데이터셋 업데이트
                if 'language_instruction' in f:
                    del f['language_instruction']
                
                f.create_dataset('language_instruction', data=[new_instr.encode('utf-8')])
                updated_count += 1
                
        except Exception as e:
            print(f"\nError processing {os.path.basename(f_path)}: {e}")
            
    print(f"\nFinished! Total {updated_count} files updated to 8-class aware instructions.")

if __name__ == "__main__":
    process_h5_files()
