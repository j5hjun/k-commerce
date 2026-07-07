"use client";

import { useChatContext } from "@/context/ChatContext";
import type { McpServerInfo } from "@/lib/types";
import {
  CheckCircleIcon,
  GearIcon,
  PlugIcon,
  PlugOffIcon,
  XCircleIcon,
} from "@/components/icons";

const STATUS_LABEL: Record<string, string> = {
  connecting: "연결 중",
  open: "연결됨",
  closed: "미연결",
  error: "오류",
};

export function StatusPanel({ servers }: { servers: McpServerInfo[] }) {
  const { status, toolLog } = useChatContext();
  const connected = status === "open";
  const totalTools = servers.reduce((sum, s) => sum + s.tools.length, 0);
  const anyError = servers.some((s) => s.error);

  return (
    <aside className="flex h-full w-72 shrink-0 flex-col gap-5 overflow-y-auto border-l border-line bg-panel px-4 py-5">
      <Section title="연결 상태">
        <div className="flex items-center gap-3 rounded-xl border border-line bg-panel-muted p-3">
          <span
            className={`flex h-10 w-10 items-center justify-center rounded-lg ${
              connected ? "bg-emerald-500/10 text-emerald-500" : "bg-faint/15 text-faint"
            }`}
          >
            {connected ? <PlugIcon className="h-5 w-5" /> : <PlugOffIcon className="h-5 w-5" />}
          </span>
          <div className="min-w-0 flex-1">
            <p className="text-sm font-semibold text-ink">{STATUS_LABEL[status]}</p>
            <p className="text-xs text-muted">에이전트 소켓</p>
          </div>
          <GearIcon className="h-4 w-4 text-faint" />
        </div>
      </Section>

      <Section title="시스템 상태">
        <div className="space-y-2.5">
          <StatRow label="MCP 서버" value={anyError ? "오류" : "정상"} tone={anyError ? "red" : "green"} />
          <StatRow label="등록 서버" value={`${servers.length}개`} tone="accent" />
          <StatRow label="사용 도구" value={`${totalTools}개`} tone="accent" />
          <StatRow
            label="연결"
            value={STATUS_LABEL[status]}
            tone={connected ? "green" : "muted"}
          />
        </div>
      </Section>

      <Section title="최근 실행">
        {toolLog.length === 0 ? (
          <p className="px-1 text-xs text-faint">아직 실행된 도구가 없어요</p>
        ) : (
          <div className="space-y-2.5">
            {toolLog.map((entry) => (
              <div key={entry.id} className="flex items-center gap-2.5">
                {entry.ok ? (
                  <CheckCircleIcon className="h-4 w-4 shrink-0 text-accent" />
                ) : (
                  <XCircleIcon className="h-4 w-4 shrink-0 text-red-500" />
                )}
                <span className="min-w-0 flex-1">
                  <span className="block truncate font-mono text-xs text-ink">{entry.name}()</span>
                  <span className="block text-[11px] text-faint">{entry.time}</span>
                </span>
              </div>
            ))}
          </div>
        )}
      </Section>

      <div className="mt-auto rounded-xl border border-line bg-panel-muted p-3">
        <p className="text-[11px] font-semibold uppercase tracking-wider text-faint">SESSION</p>
        <p className="mt-1 font-mono text-sm text-ink">—</p>
        <p className="text-xs text-muted">{STATUS_LABEL[status]}</p>
      </div>
    </aside>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <p className="mb-2.5 text-[11px] font-semibold uppercase tracking-wider text-faint">{title}</p>
      {children}
    </div>
  );
}

function StatRow({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone: "green" | "red" | "accent" | "muted";
}) {
  const dot = {
    green: "bg-emerald-500",
    red: "bg-red-500",
    accent: "bg-accent",
    muted: "bg-faint",
  }[tone];

  return (
    <div className="flex items-center justify-between">
      <span className="text-sm text-muted">{label}</span>
      <span className="flex items-center gap-1.5 text-sm font-medium text-ink">
        <span className={`h-1.5 w-1.5 rounded-full ${dot}`} />
        {value}
      </span>
    </div>
  );
}
