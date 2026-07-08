"use client";

import { useState } from "react";
import { MessageAvatar } from "@/components/MessageAvatar";
import { ToolResult } from "@/components/ToolResult";
import { CheckCircleIcon, ChevronRightIcon, XCircleIcon } from "@/components/icons";
import type { ChatMessage, ToolCall } from "@/lib/types";

export function ToolCallRow({
  call,
  content,
  priorMessages,
  source,
}: {
  call: ToolCall;
  content: string;
  priorMessages: ChatMessage[];
  source?: string;
}) {
  const [expanded, setExpanded] = useState(false);
  const running = call.status === "running";
  const failed = call.status === "failed";
  const hasResult = call.status !== "running" && content.length > 0;
  const statusLabel = running ? "실행 중..." : failed ? "실패" : "완료";

  return (
    <div className="flex animate-fade-up gap-3">
      <MessageAvatar />
      <div className="min-w-0 max-w-[85%] flex-1 space-y-2">
        <button
          type="button"
          disabled={!hasResult}
          aria-expanded={hasResult ? expanded : undefined}
          onClick={() => hasResult && setExpanded((value) => !value)}
          className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-medium transition-colors focus-visible:border-accent focus-visible:outline-none ${
            running
              ? "border-accent/20 bg-accent-soft text-accent"
              : failed
                ? "border-red-500/30 bg-red-500/10 text-red-500"
                : "border-line bg-panel text-muted hover:border-accent/40 hover:text-ink"
          } ${hasResult ? "cursor-pointer" : "cursor-default"}`}
        >
          <ToolStatusIcon failed={failed} running={running} />
          <span className="font-mono">{call.name}</span>
          <span className="text-[10px] text-faint">{statusLabel}</span>
          {source && <span className="font-mono text-[10px] text-faint">{source}</span>}
          {hasResult && (
            <>
              <span className="text-[10px] text-faint">{expanded ? "접기" : "결과 보기"}</span>
              <ChevronRightIcon
                className={`h-3 w-3 transition-transform duration-200 ${expanded ? "rotate-90" : ""}`}
              />
            </>
          )}
        </button>
        {call.time && <p className="pl-1 text-[11px] text-faint">{call.time}</p>}
        {hasResult && expanded && (
          <div className="rounded-2xl rounded-tl-md border border-line bg-panel px-4 py-3">
            <ToolResult
              content={content}
              toolName={call.name}
              priorMessages={priorMessages}
              toolArgs={call.args}
            />
          </div>
        )}
      </div>
    </div>
  );
}

function ToolStatusIcon({ failed, running }: { failed: boolean; running: boolean }) {
  if (running) {
    return (
      <span className="h-3 w-3 animate-spin rounded-full border-[1.5px] border-accent border-t-transparent" />
    );
  }
  if (failed) {
    return <XCircleIcon className="h-3.5 w-3.5" />;
  }
  return <CheckCircleIcon className="h-3.5 w-3.5 text-emerald-500" />;
}
