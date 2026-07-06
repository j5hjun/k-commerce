"use client";

import { useEffect, useRef, useState } from "react";
import { useChatContext } from "@/context/ChatContext";
import { MarkdownContent } from "@/components/MarkdownContent";
import { stamp } from "@/lib/format";
import type { ChatMessage, McpServerInfo, ToolCall } from "@/lib/types";
import { BoltIcon, SendIcon } from "@/components/icons";
import { ToolResult } from "@/components/ToolResult";

export function ChatPanel({ servers }: { servers: McpServerInfo[] }) {
  const { messages, thinking, busy, errorMessage, status, send } = useChatContext();
  const [input, setInput] = useState("");
  const [mountedTime, setMountedTime] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const isComposingRef = useRef(false);

  function toolSource(name: string): string | undefined {
    const owner = servers.find((s) => s.tools.includes(name))?.name;
    if (owner) return `mcp:${owner}`;
    if (name === "web_search") return "agent";
    return undefined;
  }

  const hasRunningTool = messages.some((m) => m.role === "tool" && m.toolCall?.status === "running");
  const hasMcpServer = servers.some((s) => !s.error && s.tools.length > 0);
  const canChat = status === "open" && hasMcpServer && !busy;

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- client-only timestamp, avoids SSR hydration mismatch
    setMountedTime(stamp());
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, thinking, hasRunningTool]);

  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  }, [input]);

  function submit(text: string) {
    const trimmed = text.trim();
    if (!trimmed || !canChat) return;
    send(trimmed);
    setInput("");
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      if (isComposingRef.current || e.nativeEvent.isComposing) return;
      e.preventDefault();
      submit(input);
    }
  }

  return (
    <div className="flex h-full flex-col bg-bg">
      <div className="border-b border-line bg-panel px-6">
        <div className="flex items-center gap-1 py-3">
          <span className="border-b-2 border-accent pb-3 -mb-3 text-sm font-semibold text-ink">
            채팅
          </span>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-8 py-6">
        <div className="space-y-5">
          <IntroBubble time={mountedTime} />
          {messages.map((m, index) => (
            <MessageRow
              key={m.id}
              message={m}
              priorMessages={messages.slice(0, index + 1)}
              toolSource={toolSource}
            />
          ))}
          {thinking && !hasRunningTool && <ThinkingRow />}
          <div ref={bottomRef} />
        </div>
      </div>

      <div className="border-t border-line bg-panel px-8 py-4">
        <div>
          {errorMessage && (
            <div className="mb-3 whitespace-pre-line rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-2 text-sm text-red-500">
              {errorMessage}
            </div>
          )}

          <div
            className={`flex items-end gap-2 rounded-2xl border border-line bg-panel-muted px-4 py-2.5 ${
              canChat ? "focus-within:border-accent/50" : "opacity-60"
            }`}
          >
            <span className="pb-1.5 font-mono text-sm text-faint">{">_"}</span>
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              onCompositionStart={() => (isComposingRef.current = true)}
              onCompositionEnd={() => (isComposingRef.current = false)}
              disabled={!canChat}
              placeholder={
                canChat
                  ? "명령 입력 또는 질문... (Shift+Enter로 줄바꿈)"
                  : busy
                    ? "응답 생성 중..."
                    : status !== "open"
                      ? "에이전트에 연결 중..."
                      : "MCP 서버 연결 후 대화할 수 있습니다"
              }
              rows={1}
              className="max-h-40 flex-1 resize-none bg-transparent py-1 text-sm text-ink placeholder-faint outline-none disabled:cursor-not-allowed"
            />
            <button
              type="submit"
              disabled={!canChat || !input.trim()}
              className="flex items-center gap-1.5 rounded-xl bg-accent px-4 py-2 text-sm font-semibold text-accent-ink transition-colors hover:bg-accent-hover disabled:opacity-30"
            >
              <SendIcon className="h-4 w-4" />
              실행
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function Spinner() {
  return (
    <span className="h-3 w-3 animate-spin rounded-full border-[1.5px] border-accent border-t-transparent" />
  );
}

function Avatar() {
  return (
    <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-accent text-accent-ink">
      <BoltIcon className="h-4 w-4" />
    </span>
  );
}

function IntroBubble({ time }: { time: string }) {
  return (
    <div className="flex gap-3">
      <Avatar />
      <div>
        <div className="rounded-2xl rounded-tl-md border border-line bg-panel px-4 py-3 text-sm leading-relaxed text-ink">
          <p>안녕하세요! Agent에 오신 걸 환영합니다.</p>
          <p className="mt-1 text-muted">
            왼쪽에서 MCP 서버를 연결하고, 아래 입력창에 명령을 입력해 시작하세요.
          </p>
        </div>
        {time && <p className="mt-1 pl-1 text-[11px] text-faint">{time}</p>}
      </div>
    </div>
  );
}

function MessageRow({
  message,
  priorMessages,
  toolSource,
}: {
  message: ChatMessage;
  priorMessages: ChatMessage[];
  toolSource: (name: string) => string | undefined;
}) {
  if (message.role === "tool" && message.toolCall) {
    if (message.toolCall.name === "web_search" && message.toolCall.status === "completed") {
      return null;
    }
    return (
      <ToolCallRow
        call={message.toolCall}
        priorMessages={priorMessages}
        source={toolSource(message.toolCall.name)}
      />
    );
  }

  if (message.role === "user") {
    return (
      <div className="flex animate-fade-up flex-col items-end">
        <div className="max-w-[75%] rounded-2xl rounded-tr-md bg-accent px-4 py-2.5 text-sm leading-relaxed text-accent-ink">
          <p className="whitespace-pre-wrap">{message.content}</p>
        </div>
        {message.time && <p className="mt-1 pr-1 text-[11px] text-faint">{message.time}</p>}
      </div>
    );
  }

  if (message.role === "assistant" && message.content) {
    return (
      <div className="flex animate-fade-up gap-3">
        <Avatar />
        <div className="min-w-0 max-w-[85%] flex-1">
          <div className="rounded-2xl rounded-tl-md border border-line bg-panel px-4 py-3 text-sm leading-relaxed text-ink">
            <MarkdownContent content={message.content} />
          </div>
          {message.time && <p className="mt-1 pl-1 text-[11px] text-faint">{message.time}</p>}
        </div>
      </div>
    );
  }

  return null;
}

function ToolCallRow({
  call,
  priorMessages,
  source,
}: {
  call: ToolCall;
  priorMessages: ChatMessage[];
  source?: string;
}) {
  const running = call.status === "running";
  const failed = call.status === "failed";

  return (
    <div className="flex animate-fade-up gap-3">
      <Avatar />
      <div className="min-w-0 max-w-[85%] flex-1 space-y-2">
        <div
          className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-medium ${
            running
              ? "border-accent/20 bg-accent-soft text-accent"
              : failed
                ? "border-red-500/30 bg-red-500/10 text-red-500"
                : "border-line bg-panel text-muted"
          }`}
        >
          {running ? (
            <Spinner />
          ) : failed ? (
            <span>✕</span>
          ) : (
            <span className="text-emerald-500">✓</span>
          )}
          <span className="font-mono">{call.name}</span>
          <span className="text-[10px] text-faint">
            {running ? "실행 중..." : failed ? "실패" : "완료"}
          </span>
          {source && <span className="font-mono text-[10px] text-faint">{source}</span>}
        </div>
        {call.result && (
          <ToolResult
            content={call.result}
            toolName={call.name}
            priorMessages={priorMessages}
            toolArgs={call.args}
          />
        )}
        {call.time && <p className="pl-1 text-[11px] text-faint">{call.time}</p>}
      </div>
    </div>
  );
}

function ThinkingRow() {
  return (
    <div className="flex gap-3">
      <Avatar />
      <div className="flex items-center gap-1 rounded-2xl rounded-tl-md border border-line bg-panel px-4 py-3.5">
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-faint [animation-delay:-0.3s]" />
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-faint [animation-delay:-0.15s]" />
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-faint" />
      </div>
    </div>
  );
}
