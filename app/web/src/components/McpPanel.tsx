"use client";

import { useState } from "react";
import { useChatContext } from "@/context/ChatContext";
import type { McpServerInfo } from "@/lib/types";
import { McpServerModal } from "@/components/McpServerModal";
import { ChevronRightIcon, PlusIcon, ServerIcon } from "@/components/icons";

type ModalState = { mode: "create" } | { mode: "edit"; server: McpServerInfo } | null;

export function McpPanel({
  servers,
  error,
  onRefresh,
}: {
  servers: McpServerInfo[];
  error: string | null;
  onRefresh: () => void;
}) {
  const { reconnect } = useChatContext();
  const [modal, setModal] = useState<ModalState>(null);

  function handleSaved() {
    onRefresh();
    reconnect();
  }

  return (
    <aside className="flex h-full w-72 shrink-0 flex-col border-r border-line bg-panel">
      <div className="px-5 pb-2 pt-5">
        <p className="text-[11px] font-semibold uppercase tracking-wider text-faint">MCP 서버</p>
      </div>

      <div className="flex-1 space-y-1.5 overflow-y-auto px-3 pb-3">
        {error && <p className="px-2 text-xs text-red-500">{error}</p>}

        {servers.length === 0 && !error && (
          <div className="mx-2 mt-2 rounded-xl border border-dashed border-line px-4 py-6 text-center">
            <p className="text-xs text-muted">연결된 서버가 없어요</p>
            <p className="mt-1 text-[11px] text-faint">아래 버튼으로 JSON을 입력해 연결하세요</p>
          </div>
        )}

        {servers.map((server) => (
          <button
            key={server.name}
            onClick={() => setModal({ mode: "edit", server })}
            className="group flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left transition-colors hover:bg-panel-muted"
          >
            <span
              className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg ${
                server.error ? "bg-red-500/10 text-red-500" : "bg-accent-soft text-accent"
              }`}
            >
              <ServerIcon className="h-4 w-4" />
            </span>
            <span className="min-w-0 flex-1">
              <span className="flex items-center gap-1.5">
                <span className="truncate text-sm font-semibold text-ink">{server.name}</span>
                <span
                  className={`h-1.5 w-1.5 shrink-0 rounded-full ${
                    server.error ? "bg-red-500" : "bg-emerald-500"
                  }`}
                />
              </span>
              <span className="truncate text-xs text-muted">
                {server.error ? "연결 오류" : `${server.tools.length}개 도구 · ${server.transport}`}
              </span>
            </span>
            <ChevronRightIcon className="h-4 w-4 shrink-0 text-faint transition-transform group-hover:translate-x-0.5" />
          </button>
        ))}
      </div>

      <div className="border-t border-line p-3">
        <button
          onClick={() => setModal({ mode: "create" })}
          className="flex w-full items-center justify-center gap-1.5 rounded-xl bg-accent py-2.5 text-sm font-semibold text-accent-ink transition-colors hover:bg-accent-hover"
        >
          <PlusIcon className="h-4 w-4" />
          MCP 서버 연결
        </button>
      </div>

      {modal && (
        <McpServerModal
          server={modal.mode === "edit" ? modal.server : undefined}
          onClose={() => setModal(null)}
          onSaved={handleSaved}
        />
      )}
    </aside>
  );
}
