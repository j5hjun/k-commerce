"use client";

import { useState } from "react";
import {
  AlertCircle,
  Loader2,
  Plug2,
  Wifi,
  WifiOff,
  X,
} from "lucide-react";
import { CONN_CFG, useApp, type McpConfig } from "@/context/app-context";
import { fetchTools } from "@/lib/agent";
import { cn } from "@/lib/utils";

export function McpModal() {
  const { connStatus, setConn, mcpCfg, setMcpCfg, setShowMcp } = useApp();
  const [local, setLocal] = useState<McpConfig>(mcpCfg);
  const [notice, setNotice] = useState<string | null>(null);
  const connection = CONN_CFG[connStatus];

  async function handleConnect() {
    setMcpCfg(local);
    setConn("connecting");
    setNotice(null);
    try {
      const info = await fetchTools(local);
      setConn("connected");
      if (!info.model_configured) {
        setNotice(
          "연결됨. 단, 백엔드에 LLM 모델이 아직 설정되지 않아 채팅은 동작하지 않습니다.",
        );
      } else {
        setNotice(`연결됨. 도구 ${info.tools.length}개 사용 가능.`);
      }
    } catch {
      setConn("error");
      setNotice(
        "연결 실패: 에이전트 서버에 접근할 수 없습니다. 서버 실행 여부와 Host/Port를 확인하세요.",
      );
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      onClick={(event) =>
        event.target === event.currentTarget && setShowMcp(false)
      }
    >
      <div className="w-[460px] bg-card border border-border shadow-2xl flex flex-col">
        <div className="flex items-center justify-between px-5 py-4 border-b border-border">
          <div className="flex items-center gap-2">
            <Plug2 size={14} className="text-primary" />
            <span className="font-mono text-sm font-semibold text-foreground">
              MCP 서버 연결
            </span>
          </div>
          <button
            onClick={() => setShowMcp(false)}
            className="text-muted-foreground hover:text-foreground transition-colors"
          >
            <X size={16} />
          </button>
        </div>

        <div
          className={cn(
            "mx-5 mt-4 flex items-center gap-3 px-4 py-3 border",
            connStatus === "connected" &&
              "border-blue-200 bg-blue-50 dark:border-blue-800/50 dark:bg-blue-950/30",
            connStatus === "error" &&
              "border-red-200 bg-red-50 dark:border-red-800/50 dark:bg-red-950/30",
            connStatus === "connecting" &&
              "border-yellow-200 bg-yellow-50 dark:border-yellow-800/50 dark:bg-yellow-950/20",
            connStatus === "disconnected" && "border-border bg-muted/40",
          )}
        >
          {connStatus === "connected" ? (
            <Wifi size={15} className="text-primary shrink-0" />
          ) : connStatus === "connecting" ? (
            <Loader2
              size={15}
              className="text-yellow-500 animate-spin shrink-0"
            />
          ) : connStatus === "error" ? (
            <AlertCircle size={15} className="text-red-500 shrink-0" />
          ) : (
            <WifiOff size={15} className="text-muted-foreground shrink-0" />
          )}
          <div className="flex-1">
            <div className={cn("font-mono text-xs font-semibold", connection.text)}>
              {connection.label}
            </div>
            <div className="font-mono text-[10px] text-muted-foreground mt-0.5">
              {connStatus === "connected"
                ? `http://${local.host}:${local.port} · 세션 활성`
                : "서버 정보를 입력 후 연결하세요"}
            </div>
          </div>
          <span className={cn("w-2 h-2 rounded-full shrink-0", connection.dot)} />
        </div>

        {notice && (
          <div
            className={cn(
              "mx-5 mt-3 px-4 py-2.5 border font-mono text-[11px]",
              connStatus === "error"
                ? "border-red-200 bg-red-50 text-red-600 dark:border-red-800/50 dark:bg-red-950/30 dark:text-red-400"
                : "border-border bg-muted/40 text-muted-foreground",
            )}
          >
            {notice}
          </div>
        )}

        <div className="px-5 py-4 flex flex-col gap-4">
          <div className="flex gap-3">
            <div className="flex-1 flex flex-col gap-1.5">
              <label className="font-mono text-[11px] text-muted-foreground uppercase tracking-wider">
                Host
              </label>
              <input
                value={local.host}
                onChange={(event) =>
                  setLocal((prev) => ({ ...prev, host: event.target.value }))
                }
                placeholder="localhost"
                className="bg-background border border-border text-foreground placeholder:text-muted-foreground px-3 py-2 text-sm font-mono focus:outline-none focus:border-primary transition-colors"
              />
            </div>
            <div className="w-24 flex flex-col gap-1.5">
              <label className="font-mono text-[11px] text-muted-foreground uppercase tracking-wider">
                Port
              </label>
              <input
                value={local.port}
                onChange={(event) =>
                  setLocal((prev) => ({ ...prev, port: event.target.value }))
                }
                placeholder="8000"
                className="bg-background border border-border text-foreground placeholder:text-muted-foreground px-3 py-2 text-sm font-mono focus:outline-none focus:border-primary transition-colors"
              />
            </div>
          </div>
          <div className="bg-muted border border-border px-3 py-2 font-mono text-[11px]">
            <span className="text-muted-foreground">endpoint </span>
            <span className="text-primary">
              http://{local.host || "localhost"}:{local.port || "8000"}
            </span>
          </div>
        </div>

        <div className="flex items-center justify-between px-5 py-4 border-t border-border">
          <button
            onClick={() => setShowMcp(false)}
            className="px-4 py-2 text-sm font-medium border border-border text-muted-foreground hover:text-foreground hover:border-primary transition-colors"
          >
            닫기
          </button>
          <div className="flex gap-2">
            {connStatus === "connected" ? (
              <button
                onClick={() => setConn("disconnected")}
                className="px-4 py-2 text-sm font-medium border border-red-300 text-red-500 dark:border-red-700 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-950/30 transition-colors"
              >
                연결 해제
              </button>
            ) : (
              <>
                <button
                  onClick={() => setMcpCfg(local)}
                  className="px-4 py-2 text-sm font-medium border border-border text-muted-foreground hover:text-foreground transition-colors"
                >
                  저장
                </button>
                <button
                  onClick={handleConnect}
                  disabled={connStatus === "connecting"}
                  className="px-4 py-2 text-sm font-medium bg-primary text-primary-foreground flex items-center gap-2 hover:bg-blue-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {connStatus === "connecting" ? (
                    <>
                      <Loader2 size={13} className="animate-spin" />
                      연결 중...
                    </>
                  ) : (
                    <>
                      <Plug2 size={13} />
                      연결
                    </>
                  )}
                </button>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
