# Git LFS 이슈 보고서 및 관리 방안 제안

**작성일:** 2025-11-25
**작성자:** Antigravity Agent

## 1. 현재 상황 (Current Status)

### 1.1 발생한 문제
- `main` 브랜치와 동기화(`git reset --hard`) 시도 중 **Git LFS 대역폭 초과(Bandwidth Limit Exceeded)** 오류 발생.
- 오류 메시지: `This repository exceeded its LFS budget. The account responsible for the budget should increase it to restore access.`
- 임시 조치: `GIT_LFS_SKIP_SMUDGE=1` 환경 변수를 사용하여 LFS 파일 다운로드를 건너뛰고(포인터 파일만 유지) 소스 코드만 동기화함.

### 1.2 영향 범위
- **데이터셋 접근 불가**: 현재 로컬에서 LFS로 관리되는 대용량 파일(H5 데이터셋, 모델 가중치 등)을 새로 다운로드할 수 없음.
- **협업 제한**: 다른 팀원이 리포지토리를 클론하거나 풀(pull) 받을 때 동일한 오류가 발생하여 작업이 중단될 수 있음.
- **CI/CD 실패**: 자동화된 빌드나 테스트 과정에서 데이터셋이 필요한 경우 실패하게 됨.

---

## 2. LFS 관리 방안 제안 (Proposals)

### 2.1 단기적 해결 방안 (즉시 조치 필요)
1.  **GitHub Data Pack 구매 (권장)**
    - 가장 빠르고 확실한 해결책.
    - GitHub 계정 설정 > Billing > Git LFS Data에서 추가 대역폭 구매.
2.  **로컬 캐시 활용**
    - 이미 다운로드 받아둔 파일이 있다면 재다운로드하지 않도록 주의.
    - `git lfs fetch` 대신 필요한 파일만 선별적으로 다운로드 시도.

### 2.2 중장기적 관리 방안 (구조 개선)

#### A안: 외부 스토리지로 데이터 이관 (강력 추천)
Git 리포지토리는 코드 관리에 집중하고, 대용량 데이터는 전용 스토리지로 분리.
- **대상**: `.h5` 데이터셋, `.pt` 모델 가중치 파일 등.
- **방법**:
    1. 데이터를 **Hugging Face Hub**, **Google Drive**, **AWS S3** 등으로 업로드.
    2. 리포지토리에는 다운로드 스크립트(`scripts/utils/download_dataset.sh`)만 포함.
    3. `.gitignore`에 데이터 파일 확장자 추가하여 실수로 커밋되는 것 방지.
- **장점**: Git LFS 용량/대역폭 제한에서 완전히 해방. 다운로드 속도 개선.
- **단점**: 초기 이관 작업 필요.

#### B안: Git LFS 히스토리 정리 (BFG Repo-Cleaner)
불필요하게 LFS 용량을 차지하고 있는 과거의 파일들을 히스토리에서 완전히 삭제.
- **방법**: `BFG Repo-Cleaner` 또는 `git filter-repo`를 사용하여 특정 시점 이전의 대용량 파일 삭제.
- **주의**: 모든 팀원이 리포지토리를 다시 클론해야 할 수 있음 (Force Push 필요).

#### C안: LFS 추적 범위 축소
- 현재 모든 `.h5`, `.jpg` 등을 LFS로 추적 중일 수 있음.
- 테스트용 작은 파일은 LFS 해제하고, 실제 대용량 파일만 LFS로 관리하거나 외부로 뺌.

## 3. 결론 및 추천
현재 프로젝트의 확장성을 고려할 때, **A안(외부 스토리지 이관)**으로 전환하는 것을 강력히 추천합니다.
특히 **Hugging Face Hub**는 무료로 대용량 모델/데이터셋 호스팅을 제공하며, `huggingface_hub` 라이브러리를 통해 Python 코드에서 쉽게 연동할 수 있어 Mobile-VLA 프로젝트에 적합합니다.

### Action Item
1. [ ] 중요 데이터 백업 (로컬)
2. [ ] Hugging Face Hub 리포지토리 생성
3. [ ] 데이터 업로드 및 다운로드 스크립트 작성
4. [ ] Git LFS 추적 해제 및 리포지토리 경량화
