# K-Commerce MCP

MCP server for Korean commerce workflows.

## Setup

Install the workspace from the repository root:

```bash
uv sync
```

Run the MCP server from the repository root:

```bash
uv run k-commerce-mcp
```

## Tools

- `login`: provider name을 받아 로그인 플로우를 실행합니다.
  - example: `provider="coupang"`
  - return: `LoginResult`

- `login_status`: 저장된 로컬 세션이 실제로 유효한 로그인 상태인지 확인합니다.
  - example: `provider="coupang"`
  - return: `StatusResult`

## Supported Providers

The MCP tools currently support:

- `coupang`
