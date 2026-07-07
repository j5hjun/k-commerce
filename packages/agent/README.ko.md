# K-Commerce Agent

LangChain 기반 에이전트 백엔드입니다. 웹 프론트엔드(Next.js 등)와 K-Commerce MCP 서버를
연결하는 다리 역할을 합니다.

English documentation is available in [README.md](README.md).

```text
프론트(Next.js) -> WebSocket/HTTP -> agent(FastAPI) -> MCP stdio -> k-commerce-mcp -> 쿠팡 자동화
```

## 동작 방식

- `langchain-mcp-adapters`가 MCP 서버(`k-commerce-mcp`)를 stdio subprocess로 띄우고,
  MCP 도구(`order_list`, `order_search`, `order_sync`, `cart_list`, `login`, `cart_delete_item` 등)를 LangChain 도구로 변환합니다.
- `create_agent`(LangChain) + `init_chat_model`로 LLM이 도구를 호출(tool calling)합니다.
- MCP 도구 호출은 stateless입니다. 로그인/세션 상태는 CLI가 디스크에 저장하므로
  매 호출이 새 세션이어도 상태가 유지됩니다.

## Setup

레포 루트에서 워크스페이스를 설치합니다.

```bash
uv sync
```

## LLM 설정

LLM 없이도 서버는 뜨고 `/health`, `/api/tools`는 동작합니다. 채팅(`/ws/chat`)을 쓰려면
모델을 설정하세요.

### HuggingFace

기본 provider는 `huggingface`입니다. HF의 OpenAI 호환 라우터를 통해 tool calling을
지원하는 모델을 사용합니다. `.env`(레포 루트)에 아래 값이 있으면 바로 동작합니다.

```bash
HF_TOKEN="..."
```

모델은 `AGENT_LLM_MODEL`로 바꿀 수 있습니다(기본: `Qwen/Qwen2.5-72B-Instruct`).
에이전트는 도구 호출을 사용하므로 tool calling을 지원하는 모델을 선택하세요.

- `Qwen/Qwen2.5-72B-Instruct` (추천, 한국어+도구 우수)
- `Qwen/Qwen2.5-32B-Instruct` (경량)
- `openai/gpt-oss-120b`
- `meta-llama/Llama-3.3-70B-Instruct`

특정 백엔드를 강제하려면 모델 뒤에 provider를 붙입니다(예: `Qwen/Qwen2.5-72B-Instruct:together`).

### IBM watsonx.ai

```bash
export AGENT_LLM_PROVIDER="watsonx"
export AGENT_LLM_MODEL="meta-llama/llama-3-3-70b-instruct"
# .env: WATSONX_API_KEY / WATSONX_PROJECT_ID / WATSONX_URL
```

### 그 외 provider

`AGENT_LLM_PROVIDER`를 비우고 `AGENT_LLM_MODEL`을 `provider:model` 형식으로 지정하면
됩니다. 해당 provider의 LangChain 패키지(`langchain-anthropic` 등)를 `pyproject.toml`에
추가하세요.

```bash
export AGENT_LLM_PROVIDER=""
export AGENT_LLM_MODEL="anthropic:claude-sonnet-4-6"
export ANTHROPIC_API_KEY="..."
```

## 실행

```bash
uv run k-commerce-agent
```

기본 주소는 `http://127.0.0.1:8000` 입니다.

## 엔드포인트

| 메서드 | 경로 | 설명 | LLM 필요 |
| --- | --- | --- | --- |
| GET | `/health` | 헬스 체크 | 아니오 |
| GET | `/api/tools` | MCP 도구 목록 | 아니오 |
| WS | `/ws/chat` | 채팅 스트리밍 | 예 |

### `/ws/chat` 프로토콜

- 클라이언트 -> 서버: `{"message": "장바구니 보여줘"}` 또는 `{"messages": [...]}`
- 서버 -> 클라이언트:
  - `{"type": "token", "content": "..."}` 답변 토큰
  - `{"type": "tool", "name": "...", "args": {...}}` 도구 호출 알림
  - `{"type": "done"}` 턴 종료
  - `{"type": "error", "message": "..."}` 오류

## 설정

환경변수는 `AGENT_` 접두사를 사용합니다.

| 변수 | 기본값 | 설명 |
| --- | --- | --- |
| `AGENT_LLM_PROVIDER` | `huggingface` | `huggingface` / `watsonx` / 비우면 generic |
| `AGENT_LLM_MODEL` | `Qwen/Qwen2.5-72B-Instruct` | HF·watsonx model_id 또는 `provider:model` |
| `HF_TOKEN` | 없음 | HuggingFace 토큰 |
| `WATSONX_URL` | 없음 | watsonx 서비스 URL |
| `WATSONX_PROJECT_ID` | 없음 | watsonx 프로젝트 ID |
| `WATSONX_API_KEY` | 없음 | watsonx API 키 |
| `AGENT_CORS_ORIGINS` | `["http://localhost:3000"]` | 허용 오리진 |
| `AGENT_HOST` | `127.0.0.1` | 바인드 호스트 |
| `AGENT_PORT` | `8000` | 포트 |

## 주의

- `login` 도구는 서버에서 Chrome 창을 띄워 수동 로그인을 기다립니다. 화면(디스플레이)이
  있는 환경에서 실행해야 합니다. 헤드리스 서버에서는 로그인 단계가 막힐 수 있습니다.
