"use client";

import { useEffect, useState } from "react";
import {
  AlertCircle,
  Loader2,
  Settings,
  Wifi,
  WifiOff,
} from "lucide-react";
import { TaskIcon } from "@/components/ui/shared";
import { CONN_CFG, useApp } from "@/context/app-context";
import { fetchMemory, type MemorySummary } from "@/lib/agent";
import { cn } from "@/lib/utils";

const RECENT_EXEC = [
  { cmd: "getOrders()", ts: "14:23:01", ok: true },
  { cmd: "login()", ts: "14:22:48", ok: true },
  { cmd: "writeReview()", ts: "13:50:12", ok: true },
  { cmd: "trackDelivery()", ts: "13:41:07", ok: false },
];

export function AppRightPanel() {
  const { connStatus, mcpCfg, setShowMcp, sessionId, memoryRevision } = useApp();
  const connection = CONN_CFG[connStatus];
  const [memory, setMemory] = useState<MemorySummary | null>(null);

  useEffect(() => {
    if (connStatus !== "connected" || !sessionId) return;
    let cancelled = false;

    void fetchMemory(mcpCfg, sessionId)
      .then((result) => {
        if (!cancelled) {
          setMemory(result);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setMemory(null);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [connStatus, mcpCfg, sessionId, memoryRevision]);

  const systemStatus = [
    { label: "MCP 서버", value: connStatus === "connected" ? "정상" : "대기", ok: connStatus === "connected" },
    {
      label: "쇼핑 메모리",
      value: memory ? `${memory.preferred_categories.length + memory.recent_queries.length}개` : "미수집",
      ok: Boolean(memory),
    },
    {
      label: "가격 성향",
      value:
        memory?.price_preference === "lowest_price"
          ? "최저가"
          : memory?.price_preference === "value"
            ? "가성비"
            : memory?.price_preference === "premium"
              ? "프리미엄"
              : "미정",
      ok: Boolean(memory?.price_preference),
    },
    {
      label: "최근 의도",
      value: memory?.last_intent ?? "대기",
      ok: Boolean(memory?.last_intent && memory.last_intent !== "chat"),
    },
  ];

  return (
    <aside
      className="w-52 border-l border-border bg-card flex flex-col shrink-0 overflow-y-auto"
      style={{ scrollbarWidth: "none" }}
    >
      <div className="px-4 pt-5 pb-3">
        <span className="font-mono text-[10px] text-muted-foreground tracking-widest uppercase">
          연결 상태
        </span>
      </div>
      <div className="px-4 mb-5">
        <button
          onClick={() => setShowMcp(true)}
          className={cn(
            "w-full flex items-center gap-3 px-3 py-3 border text-left transition-colors hover:border-primary",
            connStatus === "connected" &&
              "border-blue-200 bg-blue-50 dark:border-blue-800/50 dark:bg-blue-950/20",
            connStatus === "error" &&
              "border-red-200 bg-red-50 dark:border-red-800/50 dark:bg-red-950/20",
            connStatus === "connecting" && "border-yellow-200 dark:border-yellow-800/50",
            connStatus === "disconnected" && "border-border bg-muted/30",
          )}
        >
          {connStatus === "connected" ? (
            <Wifi size={14} className="text-primary shrink-0" />
          ) : connStatus === "connecting" ? (
            <Loader2
              size={14}
              className="text-yellow-500 animate-spin shrink-0"
            />
          ) : connStatus === "error" ? (
            <AlertCircle size={14} className="text-red-500 shrink-0" />
          ) : (
            <WifiOff size={14} className="text-muted-foreground shrink-0" />
          )}
          <div className="flex-1 min-w-0">
            <div className={cn("font-mono text-[11px] font-semibold", connection.text)}>
              {connection.label}
            </div>
            <div className="font-mono text-[10px] text-muted-foreground truncate">
              {connStatus === "connected"
                ? `${mcpCfg.host}:${mcpCfg.port}`
                : "설정 클릭"}
            </div>
          </div>
          <Settings size={11} className="text-muted-foreground/50 shrink-0" />
        </button>
      </div>

      <div className="px-4 pb-3 border-t border-border pt-4">
        <span className="font-mono text-[10px] text-muted-foreground tracking-widest uppercase">
          시스템 상태
        </span>
      </div>
      <div className="px-4 flex flex-col gap-3">
        {systemStatus.map((item) => (
          <div key={item.label} className="flex items-center justify-between">
            <span className="font-mono text-[11px] text-muted-foreground">
              {item.label}
            </span>
            <div className="flex items-center gap-1.5">
              <span
                className={cn(
                  "w-1 h-1 rounded-full",
                  item.ok ? "bg-primary" : "bg-red-500",
                )}
              />
              <span
                className={cn(
                  "font-mono text-[11px]",
                  item.ok ? "text-primary" : "text-red-500",
                )}
              >
                {item.value}
              </span>
            </div>
          </div>
        ))}
      </div>

      <div className="px-4 mt-5 pt-4 border-t border-border">
        <span className="font-mono text-[10px] text-muted-foreground tracking-widest uppercase">
          쇼핑 메모리
        </span>
      </div>
      <div className="px-4 mt-3 flex flex-col gap-3">
        <div className="border border-border bg-secondary/50 px-3 py-2.5">
          <div className="font-mono text-[10px] text-muted-foreground mb-1">선호 카테고리</div>
          <div className="font-mono text-[11px] text-foreground">
            {memory?.preferred_categories.length
              ? memory.preferred_categories.slice(0, 3).join(", ")
              : "아직 없음"}
          </div>
        </div>
        <div className="border border-border bg-secondary/50 px-3 py-2.5">
          <div className="font-mono text-[10px] text-muted-foreground mb-1">최근 관심</div>
          <div className="font-mono text-[11px] text-foreground">
            {memory?.recent_queries.length
              ? memory.recent_queries.slice(-3).join(", ")
              : "아직 없음"}
          </div>
        </div>
        <div className="border border-border bg-secondary/50 px-3 py-2.5">
          <div className="font-mono text-[10px] text-muted-foreground mb-1">최근 추천</div>
          <div className="font-mono text-[11px] text-foreground">
            {memory?.recent_recommendations.length
              ? memory.recent_recommendations.slice(0, 2).join(", ")
              : "아직 없음"}
          </div>
        </div>
      </div>

      <div className="px-4 mt-5 pt-4 border-t border-border">
        <span className="font-mono text-[10px] text-muted-foreground tracking-widest uppercase">
          최근 실행
        </span>
      </div>
      <div className="px-4 mt-3 flex flex-col gap-2.5">
        {RECENT_EXEC.map((entry, index) => (
          <div key={index} className="flex items-start gap-2">
            <TaskIcon status={entry.ok ? "ok" : "err"} />
            <div>
              <div className="font-mono text-[11px] text-foreground">
                {entry.cmd}
              </div>
              <div className="font-mono text-[10px] text-muted-foreground">
                {entry.ts}
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-auto p-4 border-t border-border">
        <div className="bg-secondary border border-border px-3 py-2.5">
          <div className="font-mono text-[10px] text-muted-foreground mb-1">
            SESSION
          </div>
          <div className="font-mono text-[11px] text-primary truncate">
            {connStatus === "connected" && sessionId ? sessionId : "—"}
          </div>
          <div className="font-mono text-[10px] text-muted-foreground mt-0.5">
            {connStatus === "connected" ? "메모리 기반 추천 활성" : "미연결"}
          </div>
        </div>
      </div>
    </aside>
  );
}
