# MeNemory: V5 실험 문서화 및 대시보드 업그레이드 (2026-04-15)

## 1. 개요
- **목표**: V5 실험 결과의 시각적 가독성 개선 및 기술적 기입 오류 수정.
- **주요 작업**:
    - `docs/v5/index.html` 프리미엄 대시보드 (Bulma 기반) 구축.
    - Exp 01 메타데이터 수정 (9-class -> 6-class).
    - Exp 05-08 개별 상세 리포트 생성 및 연결.
    - GitHub Pages 배포 브랜치(`inference-integration`) 동기화 및 404 에러 해결.

## 2. 주요 기술적 고찰
- **GitHub Pages 구조**: 현재 프로젝트는 `docs/` 폴더를 루트로 서빙함. 따라서 URL에는 `docs/` 경로가 포함되지 않아야 함 (예: `.../MoNaVLA/v5/index.html`).
- **배포 워크플로우**: `main` 브랜치가 아닌 `inference-integration` 브랜치를 기준으로 Pages 빌드가 수행됨. 모든 문서 수정 후 해당 브랜치에 푸시 필수.
- **데이터 일관성**: Exp 01은 V4의 6-class 체계를 계승하며, Exp 09에 이르러서야 8-class (3DOF) 통합 체계로 전환됨을 명시함.

## 3. 결과물 위치
- **대시보드**: [v5/index.html](https://minuum.github.io/MoNaVLA/v5/index.html)
- **개별 리포트**:
    - `docs/v5/exp05/report.md`
    - `docs/v5/exp06/report.md`
    - `docs/v5/exp07/report.md`
    - `docs/v5/exp08/report.md`

## 4. 향후 과제
- Exp 09 학습 완료 시 정량적 지표(PM, DM 등) 업데이트 필요.
- 대시보드의 "최신 학습 현황" 버튼을 TensorBoard 데이터와 수동/자동 동기화 고려.
