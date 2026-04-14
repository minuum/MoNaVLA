import os
import re
import glob

def cleanup_v4_checkpoints(root_dir, dry_run=True):
    print(f"Cleanup root: {root_dir}")
    ckpt_files = glob.glob(os.path.join(root_dir, "**/*.ckpt"), recursive=True)
    
    # Group by directory
    dir_to_ckpts = {}
    for f in ckpt_files:
        d = os.path.dirname(f)
        if d not in dir_to_ckpts:
            dir_to_ckpts[d] = []
        dir_to_ckpts[d].append(f)
    
    total_freed = 0
    
    for d, files in dir_to_ckpts.items():
        print(f"\nProcessing: {d}")
        if len(files) <= 2:
            print("  - 2개 이하의 체크포인트가 있으므로 건너뜁니다.")
            continue
            
        last_ckpt = None
        epoch_ckpts = []
        
        for f in files:
            basename = os.path.basename(f)
            if basename == "last.ckpt":
                last_ckpt = f
            else:
                # val_loss 파싱 시도 (숫자와 점만 추출)
                match = re.search(r"val_loss=([0-9\.]+)", basename)
                val_loss_str = match.group(1) if match else "inf"
                # 끝에 붙은 점 제거 (예: '1.979.')
                val_loss_str = val_loss_str.rstrip('.')
                try:
                    val_loss = float(val_loss_str)
                except ValueError:
                    val_loss = float('inf')
                
                # epoch 파싱 시도 (백업용)
                epoch_match = re.search(r"epoch=(\d+)", basename)
                epoch = int(epoch_match.group(1)) if epoch_match else -1
                
                epoch_ckpts.append({
                    'path': f,
                    'val_loss': val_loss,
                    'epoch': epoch,
                    'basename': basename
                })
        
        # val_loss 기준 오름차순 정렬 (낮은 게 좋음)
        epoch_ckpts.sort(key=lambda x: x['val_loss'])
        
        # 보관할 파일들
        keep = []
        if last_ckpt:
            keep.append(last_ckpt)
        
        if epoch_ckpts:
            best_ckpt = epoch_ckpts[0]
            keep.append(best_ckpt['path'])
            print(f"  - Keep (Best): {best_ckpt['basename']} (val_loss: {best_ckpt['val_loss']})")
        
        if last_ckpt:
            print(f"  - Keep (Last): last.ckpt")
            
        # 삭제할 파일들
        for item in epoch_ckpts[1:]:
            f_path = item['path']
            if f_path in keep:
                continue
            
            size = os.path.getsize(f_path)
            total_freed += size
            
            if dry_run:
                print(f"  [DRY RUN] Delete: {item['basename']} ({size / 1024**3:.2f} GB)")
            else:
                try:
                    os.remove(f_path)
                    print(f"  [DELETE] {item['basename']} ({size / 1024**3:.2f} GB)")
                except Exception as e:
                    print(f"  [ERROR] Failed to delete {f_path}: {e}")
                    
    print(f"\nTotal expected freed space: {total_freed / 1024**3:.2f} GB")

if __name__ == "__main__":
    # V4 kosmos 디렉토리 경로
    v4_root = "runs/v4_nav/kosmos"
    # 실제 삭제를 원하시면 dry_run=False로 변경하여 실행
    cleanup_v4_checkpoints(v4_root, dry_run=False)
