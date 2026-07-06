# Contributing

## Development Setup

이 저장소는 `uv` 워크스페이스로 관리합니다.

- 워크스페이스 루트: `pyproject.toml`
- 워크스페이스 패키지:
  - `packages/cli`
  - `packages/mcp`

## Common Commands

별도 안내가 없으면 저장소 루트에서 실행합니다.

```bash
uv sync
uv build
uv run pytest
uv run k-commerce --help
uv run k-commerce-mcp
npx @modelcontextprotocol/inspector uv run k-commerce-mcp
```

Canonical CLI runner는 MCP와 같은 요청 스키마를 사용합니다.

```bash
uv run k-commerce <tool-name> '<json-request>'
uv run k-commerce <tool-name> --request-file ./request.json
```

사람이 직접 브라우저 흐름을 확인할 때는 `uv run k-commerce login coupang`,
`uv run k-commerce order list coupang`, `uv run k-commerce search coupang KEYWORD` 같은
호환 alias 명령을 사용할 수 있습니다. 이 명령들은 디버깅과 수동 확인용으로만 짧게
문서화하고, 자동화/연동 설명은 canonical tool 이름과 요청 JSON을 기준으로 작성합니다.

## Test Layout

테스트는 패키지별로 나뉘어 있습니다.

- `packages/cli/tests`
  - CLI 단위/통합 테스트
  - provider/browser/store 테스트
- `packages/cli/tests/e2e`
  - CLI 엔트리포인트를 통과하는 파일 기반 로그인 흐름 시나리오
  - `--root-dir` 또는 `--root_dir`로 임시 디렉터리 아래에 인증 정보와 세션 데이터를 격리합니다.
- `packages/cli/tests/smoke`
  - 실제 브라우저를 실행하거나 로컬 인증 정보/세션 상태에 의존하는 선택 실행 smoke 테스트
  - 명시적인 smoke 환경 변수가 없으면 기본적으로 건너뜁니다.
- `packages/mcp/tests`
  - MCP 서버와 도구 연결 테스트

전체 테스트는 저장소 루트에서 실행합니다.

```bash
uv run pytest
```

CLI e2e 스타일 시나리오만 실행합니다.

```bash
uv run pytest packages/cli/tests/e2e
```

CLI smoke 테스트를 명시적으로 실행합니다.

```bash
RUN_COUPANG_SMOKE=1 K_COMMERCE_BROWSER_SANDBOX=0 uv run pytest packages/cli/tests/smoke -m smoke
```

`K_COMMERCE_BROWSER_SANDBOX=0`은 Chrome sandbox가 막힌 로컬/에이전트 실행 환경에서
nodriver 브라우저 연결을 허용하기 위한 옵션입니다. 이 값을 지정하지 않으면 기본적으로
Chrome sandbox를 켠 상태로 실행합니다.

Smoke 입력은 케이스별로 다음과 같습니다.

- 기존 세션
  - 원본: `~/.k-commerce/coupang`
  - 복사되는 산출물: `chrome-profile/`, `cookies.dat`
- 인증 정보
  - 원본: `~/.k-commerce/coupang`
  - 복사되는 산출물: `credentials.json`
- 잘못된 인증 정보
  - 원본: 없음
  - 생성되는 산출물: 잘못된 `credentials.json`
- 인증 정보 없는 수동 로그인
  - 원본: 없음
  - 비어 있는 임시 루트 디렉터리에서 시작합니다.
  - smoke 실행 중 브라우저 로그인 흐름을 직접 완료해야 합니다.

## Agent Notes

- 디렉터리 구조나 주요 파일 역할이 바뀌면 관련 `AGENTS.md`의 파일 지도도 함께 갱신합니다.
- 개인 메모나 로컬 전용 지시는 Git에서 무시되는 `AGENTS.override.md`에 둡니다.
- 파일 지도를 크게 갱신할 때는 `.agents/skills/map-agents-files/` 스킬을 참고합니다.

## Branch Strategy

짧게 쓰는 브랜치를 만들고, `dev`를 주 통합 브랜치로 취급합니다.

- `main`
  - 검토와 검증이 끝난 안정 브랜치입니다.
  - 릴리스 준비가 된 변경 묶음은 `dev`에서 `main`으로 병합합니다.
- `dev`
  - 팀 개발을 위한 공유 통합 브랜치입니다.
  - 기능, 수정, 문서, 유지보수, 리팩터링 PR은 `dev`를 대상으로 엽니다.
- `feat/<topic>`
  - 새 기능 작업
  - 예: `feat/mcp-server-bootstrap`
- `fix/<topic>`
  - 버그 수정
  - 예: `fix/package-entrypoint`
- `chore/<topic>`
  - 유지보수, 도구, 저장소 설정
  - 예: `chore/add-pr-template`
- `docs/<topic>`
  - 문서 전용 변경
  - 예: `docs/add-contributing-guide`
- `refactor/<topic>`
  - 의도한 동작 변경이 없는 내부 구조 개선
  - 예: `refactor/server-layout`

권장 흐름은 다음과 같습니다.

1. `dev`에서 브랜치를 만듭니다.
2. PR은 `dev`로 엽니다.
3. 변경이 검토되고 안정적이라고 판단되면 `dev`를 `main`으로 병합합니다.

문서 전용 변경은 다음 기준을 따릅니다.

- 문서 업데이트 자체가 하나의 작업이면 `docs/<topic>`을 사용합니다.
- 문서 변경이 기능이나 수정에 딸린 내용이면 같은 브랜치에 포함합니다.
- 초기 설정 단계에서 `dev`의 저장소 설정이나 프로세스 문서를 직접 갱신하는 것은 허용할 수 있습니다.

## Commit Message Convention

커밋 메시지는 영어로 작성하고, 간단한 Conventional Commits 형식을 사용합니다.

```text
<type>: <summary>
```

권장 타입은 다음과 같습니다.

- `feat`: 새 기능
- `fix`: 버그 수정
- `chore`: 도구, 설정, 유지보수
- `docs`: 문서 변경
- `refactor`: 의도한 동작 변경이 없는 내부 구조 변경
- `test`: 테스트 추가 또는 수정

예시는 다음과 같습니다.

```text
feat: add MCP server entrypoint
fix: correct package script target
docs: add pull request template
chore: configure uv workspace
```

본문이 필요한 커밋을 작성할 때도 제목 줄은 영어로 유지합니다.

## Pull Request

이슈와 PR 제목은 영어로 작성합니다. 본문은 한국어로 작성하되, 템플릿의 원래 heading과
체크리스트 형태는 유지합니다.

PR을 열기 전에 다음을 확인합니다.

- `dev`에서 브랜치를 만듭니다. 단, `dev`에서 `main`으로 승격하는 PR은 예외입니다.
- 브랜치 이름이 변경 유형과 맞는지 확인합니다.
- 일반 개발 작업은 `dev`를 대상으로 합니다.
- `main`은 `dev`에서 검토가 끝나고 승격 준비가 된 변경만 대상으로 합니다.
- PR 템플릿의 `What`, `How To Test`, `Review Focus`, `Screenshots / Logs`, `Related` 섹션을 채웁니다.
- 하나의 계획된 기능 또는 명확히 범위가 잡힌 수정에 필요한 내용만 포함합니다.

권장 확인 항목이 적용되지 않는다면 PR에 이유를 적습니다.

## Issues

이슈 제목은 영어로 작성하고, 본문은 선택한 이슈 템플릿의 heading을 유지한 채 한국어로
작성합니다.

- Feature 이슈는 `Summary`, `Goal`, `Scope`, `Acceptance Criteria`를 채웁니다.
- Bug 이슈는 `Summary`, `Current Behavior`, `Expected Behavior`, `Steps To Reproduce`, `Acceptance Criteria`를 채웁니다.
