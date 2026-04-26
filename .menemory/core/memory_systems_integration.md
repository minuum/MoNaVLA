# Memory Systems Integration Map (Claude + Codex + Antigravity + Menemory)

**작성일**: 2026-04-20
**마지막 업데이트**: 2026-04-26
**목적**: 여러 AI 메모리 시스템을 같은 절차로 조회하기 위한 내부 맵

> 공용 계약 문서는 `docs/MEMORY_SYNC_MAP.md` 이다. 이 파일은 Menemory 내부 관점의
> 보조 설명이다.

---

## 1. 시스템 개요

| 시스템 | 위치 | 특징 | 상태 |
|--------|------|------|------|
| **Claude Code** | `~/.claude_MINU/projects/-home-billy-25-1kp-MoNaVLA/memory/` | 프로젝트 격리, 마크다운 기반 | ✅ 존재 |
| **Codex IDE** | `~/.codex/` | 로컬 IDE, history/logs/memories | ✅ 존재 |
| **Antigravity Recovery** | `~/.gemini/antigravity/` | 복구 가능한 원문 아티팩트 | ✅ 존재 |
| **Antigravity-Server** | `~/.antigravity-server/` | 런타임/로그 | ✅ 존재 |
| **Menemory** | `.menemory/` | 워크스페이스 장기 메모리 + 세션 요약 | ✅ 현재 허브 |

---

## 2. Claude Code 메모리 구조

```
~/.claude_MINU/projects/-home-billy-25-1kp-MoNaVLA/memory/
├── MEMORY.md                 (인덱스 — 시작점)
├── user_profile.md          (사용자 정보)
├── feedback_workflow.md      (작업 피드백/규칙)
└── project_monavla.md       (프로젝트 상태)
```

### 각 파일 의미
- **MEMORY.md**: menemory와의 차이점 명시 (이곳은 프로젝트별 격리)
- **user_profile.md**: 사용자 역할, 선호도, 도메인 지식
- **feedback_workflow.md**: "구현 전 계획 승인 필수", RoboVLMs 수정 금지 등
- **project_monavla.md**: Exp 상태, 현재 best 성능, 교수님 프로토콜 진행

**로드 방식**: 세션 시작 시 자동 포함 (시스템 프롬프트)

---

## 3. Codex IDE 메모리 구조

```
~/.codex/
├── memories/                 (로컬 IDE 메모리)
├── history.jsonl             (명령 히스토리, 303KB)
├── logs_2.sqlite             (상세 로그, 15MB)
├── state_5.sqlite            (현재 상태 DB)
├── sessions/                 (과거 세션)
├── plugins/                  (플러그인 데이터)
├── rules/                    (커스텀 규칙)
└── config.toml              (설정)
```

### 주요 항목
- **memories/**: Codex 로컬 메모리 (브라우저 확장처럼 동작)
- **history.jsonl**: 명령 입력 기록 (검색 용도)
- **logs_2.sqlite**: 구조화된 로그 (쿼리 가능)
- **sessions/**: 과거 대화 세션

**로드 방식**: Codex IDE에서만 로드 (Claude Code 세션과 격리)

---

## 4. Antigravity 시스템

```
~/.gemini/antigravity/
├── brain/<uuid>/            (복구 가능한 Markdown, media, metadata)
└── conversations/*.pb       (세션 인덱스)

~/.antigravity-server/
├── data/
├── extensions/
├── .log
└── .pid / .token
```

### 현황
- `.gemini/antigravity/brain/<uuid>/` 가 실질적인 복구 원본
- `.pb` 는 인덱스일 뿐이며 직접 읽을 본문이 아님
- `.antigravity-server` 는 시스템 런타임 확인용

---

## 5. 통합 조회 플로우 (추천)

### Case 1: 현재 MoNaVLA 세션에서 정보 필요
```
1. Claude Code (MEMORY.md) 읽기
   → project_monavla.md에서 현재 Exp, 최선 성능 확인
   → feedback_workflow.md에서 작업 규칙 확인

2. 필요시 Codex history.jsonl 검색
   → 과거 명령 추적
```

### Case 2: 다른 프로젝트/세션의 메모리 필요
```
1. ~/.claude_MINU/projects/ 내 다른 폴더 확인
   (예: .claude_YUBEEN 있음 → 다른 사용자 세션)

2. Codex sessions/ 폴더에서 과거 세션 로드

3. AntiGravity-server logs에서 시스템 레벨 정보
```

### Case 3: 장기 메모리/아키텍처 참고
```
1. .menemory/core/master_memory.md (프로젝트 핵심)
2. .menemory/longterm/ (장기 목표)
3. .menemory/sessions/ (세션별 기록)
```

---

## 6. 동기화 전략

### ✅ 현재 (격리 상태)
- Claude Code: 프로젝트 격리, MEMORY.md 인덱스
- Codex: 로컬 IDE 독립
- AntiGravity-Server: 시스템 런타임

### 📌 권장 동기화 (부분)
세션 시작 시:
```bash
1. docs/MEMORY_SYNC_MAP.md 읽기
2. .agent/skills/memory-sync-hub/SKILL.md 읽기
3. scripts/utils/collect_memory_context.sh 실행
4. ~/.claude_MINU/.../memory/MEMORY.md 읽기
5. .menemory/core/master_memory.md 읽기
6. 필요시 ~/.codex/history.jsonl 검색
7. Antigravity가 필요하면 ~/.gemini/antigravity/brain/<uuid>/ 확인
```

### ❌ 권장하지 않는 것
- 세 시스템 메모리를 일대일 복사
- AntiGravity 메모리를 Claude에 저장 (시스템 수준, 프로젝트 수준 분리 필요)

---

## 7. 파일 접근 권한 및 명령

### 읽기 (현재 권한)
```bash
# Claude memory 읽기
cat ~/.claude_MINU/projects/-home-billy-25-1kp-MoNaVLA/memory/MEMORY.md

# Codex 히스토리 검색
grep "exp17\|train" ~/.codex/history.jsonl

# Antigravity recovery source
find ~/.gemini/antigravity/brain -maxdepth 2 -type f | head
```

### 쓰기 (이 세션에서만)
```bash
# Claude memory 수정
vi ~/.claude_MINU/projects/-home-billy-25-1kp-MoNaVLA/memory/project_monavla.md

# menemory 코어 수정
vi .menemory/core/master_memory.md
```

---

## 8. 언제 어디에 쓸까?

| 정보 | 저장 위치 | 목적 |
|------|----------|------|
| 사용자 프로필 | Claude memory/user_profile.md | 이 프로젝트에서만 필요한 사용자 정보 |
| 작업 피드백/규칙 | Claude memory/feedback_workflow.md | 프로젝트별 작업 방식 |
| 실험 진행 상황 | Claude memory/project_monavla.md | MoNaVLA 현재 상태 |
| **장기 목표** | **.menemory/core/master_memory.md** | 프로젝트 전체 비전 (여러 세션 공유) |
| **명령 기록** | **~/.codex/history.jsonl** | 과거 실행 추적 (Codex IDE 용) |
| **시스템 로그** | **~/.antigravity-server/.log** | 런타임 상태 (서버 관리자용) |

---

## 9. 다음 단계 (추천)

1. **Claude memory 확장**: Exp17 완료 후 최신 결과 → project_monavla.md 업데이트
2. **menemory 동기화**: 장기 아키텍처 결정사항 → .menemory/core/ 에 추가
3. **Codex 활용**: CLI 작업 후 history.jsonl에서 명령 재사용 패턴 찾기
4. **AntiGravity-Server**: 서버 상태 변화 모니터링 (로그 주기적 확인)

---

## 부록: 각 시스템 접근 시 체크리스트

### Claude Code 세션 시작
- [ ] MEMORY.md 인덱스 읽기 (여기 → memory/*.md 자동 로드)
- [ ] project_monavla.md에서 현재 Exp 확인
- [ ] feedback_workflow.md에서 규칙 재확인

### Codex IDE 사용
- [ ] 명령 입력 후 history.jsonl에 기록됨
- [ ] 동일 명령 재사용 시 history 검색
- [ ] 로그 확인 시 logs_2.sqlite 쿼리 (SQLite 도구 필요)

### 프로젝트 장기 상태 확인
- [ ] .menemory/core/master_memory.md 읽기 (여러 세션 공유)
- [ ] .menemory/longterm/ 확인 (장기 목표)
