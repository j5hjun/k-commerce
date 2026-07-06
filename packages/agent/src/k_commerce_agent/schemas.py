from typing import Literal

from pydantic import BaseModel


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str


class ChatRequest(BaseModel):
    """Incoming websocket payload for a single chat turn.

    Either send a single ``message`` string, or the full ``messages`` history.
    """

    message: str | None = None
    messages: list[ChatMessage] | None = None
    session_id: str | None = None

    def to_lc_messages(self) -> list[dict[str, str]]:
        if self.messages:
            return [{"role": m.role, "content": m.content} for m in self.messages]
        if self.message:
            return [{"role": "user", "content": self.message}]
        return []


class ToolInfo(BaseModel):
    name: str
    description: str


class ToolsResponse(BaseModel):
    model_configured: bool
    tools: list[ToolInfo]
