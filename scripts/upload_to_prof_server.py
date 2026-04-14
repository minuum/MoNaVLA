#!/usr/bin/env python3
import os
import argparse
import subprocess
from pathlib import Path

def load_env():
    """.env 파일에서 환경 변수를 로드합니다. 스크립트 실행 디렉토리를 기준으로 합니다."""
    script_dir = Path(__file__).parent.parent
    env_path = script_dir / ".env"
    
    env_vars = {}
    if not env_path.exists():
        print(f"[Warning] .env 파일을 찾을 수 없습니다: {env_path}")
        return env_vars
    
    with open(env_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, value = line.split("=", 1)
                env_vars[key.strip()] = value.strip()
    return env_vars

def main():
    parser = argparse.ArgumentParser(description="SCP를 사용하여 지정된 디렉토리를 교수님 서버로 전송합니다.")
    parser.add_argument("dir_path", type=str, help="전송할 로컬 디렉토리 경로 (예: ROS_action/mobile_vla_dataset_v5(Image))")
    parser.add_argument("--remote_subdir", type=str, default="", help="원격 서버의 기본 경로 내에 추가적인 하위 디렉토리")
    
    args = parser.parse_args()
    
    # 1. 환경 변수 로드
    env = load_env()
    
    ip = env.get("PROF_SERVER_IP")
    user = env.get("PROF_SERVER_USER")
    base_path = env.get("PROF_SERVER_PATH")
    port = env.get("PROF_SERVER_PORT", "22")
    
    # 필수 환경 변수 체크
    if not all([ip, user, base_path]):
        print("[Error] .env 파일에 PROF_SERVER_IP, PROF_SERVER_USER, PROF_SERVER_PATH가 설정되어 있는지 확인해주세요.")
        return

    # 2. 로컬 경로 유효성 검사
    local_path = Path(args.dir_path).resolve()
    if not local_path.exists():
        print(f"[Error] 로컬 경로가 존재하지 않습니다: {local_path}")
        return

    # 3. 원격 경로 설정
    remote_target = base_path
    if args.remote_subdir:
        remote_target = f"{base_path}/{args.remote_subdir}"

    # 4. rsync 명령 생성 및 실행
    # -a: archive mode, -h: human-readable, -P: --partial --progress (상태바 표시)
    # -z: 데이터 압축 전송 (네트워크 효율)
    # --info=progress2: 전체 전송 프로세스에 대한 진행률 표시
    rsync_command = [
        "rsync", "-ahz", "--info=progress2",
        "-e", f"ssh -p {port}",
        str(local_path),
        f"{user}@{ip}:{remote_target}"
    ]

    print(f"--- 전송 시작 (rsync) ---")
    print(f"Source: {local_path}")
    print(f"Target: {user}@{ip}:{remote_target}")
    print(f"Command: {' '.join(rsync_command)}")
    print("-" * 30)
    
    try:
        # rsync는 실시간 출력을 stdout으로 보냅니다.
        subprocess.run(rsync_command, check=True)
        print("\n" + "-" * 30)
        print("[Success] 전송이 성공적으로 완료되었습니다.")
    except subprocess.CalledProcessError as e:
        print(f"\n[Failure] rsync 전송 중 오류가 발생했습니다: {e}")
    except KeyboardInterrupt:
        print("\n[Stop] 사용자에 의해 전송이 중단되었습니다.")

if __name__ == "__main__":
    main()
