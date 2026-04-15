# github-pages-reporter

이 스킬은 실험 결과나 분석 리포트를 `docs/reports/` 디렉토리로 동기화하고, GitHub Pages에 자동으로 푸시하여 팀원들과 공유할 수 있게 합니다.

## 사용 시점
- 새로운 모델 실험(V5 Train 등)이 시작되거나 종료되었을 때
- 논문 분석이나 데이터셋 검증 리포트를 작성했을 때
- 교수님 미팅 보고용 웹 페이지를 업데이트해야 할 때

## 주요 규칙
1. 모든 마크다운 리포트는 `docs/reports/` 폴더에 위치해야 `viewer.html`을 통해 웹에서 볼 수 있습니다.
2. `docs/index.html`에 새로운 리포트 링크를 추가하여 접근성을 확보해야 합니다.
3. 작업 완료 후에는 `git add docs/ && git commit -m "Update docs" && git push` 과정을 수행합니다.

## 자동화 스크립트 활용
`.agent/skills/github-pages-reporter/scripts/publish_report.py`를 사용하여 리포트를 게시할 수 있습니다.

### 사용법 예시:
```bash
python3 .agent/skills/github-pages-reporter/scripts/publish_report.py --report path/to/report.md --title "V5 Exp10 Status" --category "V5 Progress"
```

## 디렉토리 구조
- `docs/`: GitHub Pages 루트 (index.html 포함)
- `docs/reports/`: 마크다운 리포트 및 정적 분석 결과물
- `docs/reports/viewer.html`: 마크다운 파일을 웹 페이지로 렌더링하는 범용 뷰어
