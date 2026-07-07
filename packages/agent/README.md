# K-Commerce Agent

K-Commerce Agent is a LangChain-based backend that bridges a web frontend to the K-Commerce MCP
server.

Korean documentation is available in [README.ko.md](README.ko.md).

```text
Frontend (Next.js) -> WebSocket/HTTP -> agent (FastAPI) -> MCP stdio -> k-commerce-mcp -> Coupang automation
```

## How It Works

- `langchain-mcp-adapters` starts the MCP server (`k-commerce-mcp`) as a stdio subprocess and
  converts MCP tools such as `order_list`, `order_search`, `order_sync`, `cart_list`, `login`, and
  `cart_delete_item` into LangChain tools.
- `create_agent` and `init_chat_model` let the LLM call those tools.
- MCP tool calls are stateless. Login and session state are stored on disk by the CLI, so state
  survives even when each call uses a fresh server process.

## Setup

Install the workspace from the repository root:

```bash
uv sync
```

## LLM Configuration

The server can start without an LLM, and `/health` plus `/api/tools` still work. Configure a model
to use chat over `/ws/chat`.

### HuggingFace

The default provider is `huggingface`. It uses HuggingFace's OpenAI-compatible router with a model
that supports tool calling. Add this value to the repository-root `.env` file:

```bash
HF_TOKEN="..."
```

Set `AGENT_LLM_MODEL` to change the model. The default is `Qwen/Qwen2.5-72B-Instruct`. Choose a
model that supports tool calling.

- `Qwen/Qwen2.5-72B-Instruct` (recommended for Korean and tool use)
- `Qwen/Qwen2.5-32B-Instruct` (lighter)
- `openai/gpt-oss-120b`
- `meta-llama/Llama-3.3-70B-Instruct`

To force a specific backend, append the provider after the model, for example
`Qwen/Qwen2.5-72B-Instruct:together`.

### IBM watsonx.ai

```bash
export AGENT_LLM_PROVIDER="watsonx"
export AGENT_LLM_MODEL="meta-llama/llama-3-3-70b-instruct"
# .env: WATSONX_API_KEY / WATSONX_PROJECT_ID / WATSONX_URL
```

### Other Providers

Leave `AGENT_LLM_PROVIDER` empty and set `AGENT_LLM_MODEL` in `provider:model` format. Add the
provider's LangChain package, such as `langchain-anthropic`, to `pyproject.toml`.

```bash
export AGENT_LLM_PROVIDER=""
export AGENT_LLM_MODEL="anthropic:claude-sonnet-4-6"
export ANTHROPIC_API_KEY="..."
```

## Run

```bash
uv run k-commerce-agent
```

The default address is `http://127.0.0.1:8000`.

## Endpoints

| Method | Path | Description | Requires LLM |
| --- | --- | --- | --- |
| GET | `/health` | Health check | No |
| GET | `/api/tools` | MCP tool list | No |
| WS | `/ws/chat` | Streaming chat | Yes |

### `/ws/chat` Protocol

- Client to server: `{"message": "Show my cart"}` or `{"messages": [...]}`
- Server to client:
  - `{"type": "token", "content": "..."}` answer token
  - `{"type": "tool", "name": "...", "args": {...}}` tool-call notification
  - `{"type": "done"}` turn complete
  - `{"type": "error", "message": "..."}` error

## Configuration

Environment variables use the `AGENT_` prefix.

| Variable | Default | Description |
| --- | --- | --- |
| `AGENT_LLM_PROVIDER` | `huggingface` | `huggingface`, `watsonx`, or empty for generic |
| `AGENT_LLM_MODEL` | `Qwen/Qwen2.5-72B-Instruct` | HF/watsonx model ID or `provider:model` |
| `HF_TOKEN` | none | HuggingFace token |
| `WATSONX_URL` | none | watsonx service URL |
| `WATSONX_PROJECT_ID` | none | watsonx project ID |
| `WATSONX_API_KEY` | none | watsonx API key |
| `AGENT_CORS_ORIGINS` | `["http://localhost:3000"]` | Allowed origins |
| `AGENT_HOST` | `127.0.0.1` | Bind host |
| `AGENT_PORT` | `8000` | Port |

## Notes

- The `login` tool opens a Chrome window and waits for manual login when needed. Run it in an
  environment with a display. Login can block on headless servers.
