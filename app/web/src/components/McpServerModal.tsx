"use client";

import { useEffect, useState } from "react";
import { deleteMcpServer, registerMcpServers } from "@/lib/api";
import { MCP_PLACEHOLDER } from "@/lib/constants";
import type { McpServerInfo } from "@/lib/types";

interface Props {
  server?: McpServerInfo;
  onClose: () => void;
  onSaved: () => void;
}

export function McpServerModal({ server, onClose, onSaved }: Props) {
  const isEdit = Boolean(server);
  const [json, setJson] = useState(() =>
    server ? JSON.stringify({ mcpServers: { [server.name]: server.config } }, null, 2) : "",
  );
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  async function handleSave() {
    if (!json.trim()) return;
    setSaving(true);
    setError(null);
    try {
      await registerMcpServers(json);
      onSaved();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "저장에 실패했습니다.");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    if (!server) return;
    setDeleting(true);
    setError(null);
    try {
      await deleteMcpServer(server.name);
      onSaved();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "삭제에 실패했습니다.");
      setDeleting(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="w-full max-w-lg animate-fade-up rounded-2xl border border-line bg-panel p-6 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-1 flex items-center justify-between">
          <h3 className="font-mono text-base font-bold text-ink">
            {isEdit ? server!.name : "MCP 서버 연결"}
          </h3>
          <button
            onClick={onClose}
            aria-label="닫기"
            className="text-faint transition-colors hover:text-ink"
          >
            ✕
          </button>
        </div>
        <p className="mb-4 text-xs text-muted">
          {isEdit
            ? "설정을 수정하거나 서버를 삭제할 수 있어요."
            : "Cursor mcp.json 형식으로 서버를 붙여넣으세요. 여러 개도 한 번에 등록됩니다."}
        </p>

        {isEdit && server?.error && (
          <p className="mb-3 whitespace-pre-line rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs text-red-500">
            {server.error}
          </p>
        )}

        {isEdit && server && server.tools.length > 0 && (
          <div className="mb-3 flex flex-wrap gap-1.5">
            {server.tools.map((tool) => (
              <span
                key={tool}
                className="rounded-full bg-accent-soft px-2 py-1 font-mono text-[11px] font-medium text-accent"
              >
                {tool}
              </span>
            ))}
          </div>
        )}

        <textarea
          value={json}
          onChange={(e) => setJson(e.target.value)}
          placeholder={MCP_PLACEHOLDER}
          rows={11}
          spellCheck={false}
          className="w-full resize-none rounded-xl border border-line bg-panel-muted p-3 font-mono text-xs leading-relaxed text-ink placeholder-faint outline-none focus:border-accent/50"
        />

        {error && <p className="mt-2 whitespace-pre-line text-xs text-red-500">{error}</p>}

        <div className="mt-4 flex items-center justify-between gap-3">
          {isEdit ? (
            <button
              onClick={handleDelete}
              disabled={deleting || saving}
              className="rounded-xl px-4 py-2 text-sm font-medium text-red-500 transition-colors hover:bg-red-500/10 disabled:opacity-30"
            >
              {deleting ? "삭제 중..." : "삭제"}
            </button>
          ) : (
            <span />
          )}
          <button
            onClick={handleSave}
            disabled={saving || deleting || !json.trim()}
            className="rounded-xl bg-accent px-5 py-2 text-sm font-semibold text-accent-ink transition-colors hover:bg-accent-hover disabled:opacity-30"
          >
            {saving ? "저장 중..." : isEdit ? "저장" : "연결하기"}
          </button>
        </div>
      </div>
    </div>
  );
}
