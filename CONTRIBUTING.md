# Contributing

## Development Setup

이 저장소는 `uv` 워크스페이스로 관리합니다.

- 워크스페이스 루트: `pyproject.toml`
- 워크스페이스 패키지:
  - `packages/mcp`

## Common Commands

별도 안내가 없으면 저장소 루트에서 실행합니다.

```bash
uv sync
uv build
uv run pytest
uv run k-commerce-mcp
```

## Test Layout

테스트는 패키지별로 나뉘어 있습니다.

- `packages/mcp`
  - MCP 서버 패키지와 관련 테스트를 둡니다.

전체 테스트는 저장소 루트에서 실행합니다.

```bash
uv run pytest
```

## MCP Manual Testing

MCP 서버 실행 자체는 저장소 루트에서 확인합니다.

```bash
uv run k-commerce-mcp
```

MCP 도구 호출은 MCP Inspector로 수동 확인합니다.

```bash
npx @modelcontextprotocol/inspector uv run k-commerce-mcp
```

Inspector에서 확인할 항목은 다음과 같습니다.

- 서버가 stdio로 정상 실행되는지 확인합니다.
- 등록된 tools 목록이 의도한 이름과 설명으로 노출되는지 확인합니다.
- 각 tool의 input schema와 응답 payload를 확인합니다.
- 실패 케이스가 사용자에게 이해 가능한 에러로 반환되는지 확인합니다.

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

간단한 Conventional Commits 형식을 사용합니다.

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

## Pull Request

PR을 열기 전에 다음을 확인합니다.

- `dev`에서 브랜치를 만듭니다. 단, `dev`에서 `main`으로 승격하는 PR은 예외입니다.
- 브랜치 이름이 변경 유형과 맞는지 확인합니다.
- 일반 개발 작업은 `dev`를 대상으로 합니다.
- `main`은 `dev`에서 검토가 끝나고 승격 준비가 된 변경만 대상으로 합니다.
- PR 템플릿에 생성한 파일, 수정한 파일, 테스트 절차를 채웁니다.
- 하나의 계획된 기능 또는 명확히 범위가 잡힌 수정에 필요한 내용만 포함합니다.

권장 확인 항목이 적용되지 않는다면 PR에 이유를 적습니다.
