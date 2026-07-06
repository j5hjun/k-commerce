"use client";

import { createContext, useContext } from "react";
import type { TaskLog } from "@/data/taskHistory.mock";

export type ConnStatus = "disconnected" | "connecting" | "connected" | "error";

export interface McpConfig {
  host: string;
  port: string;
}

export interface AppContextValue {
  dark: boolean;
  setDark: (value: boolean) => void;
  tasks: TaskLog[];
  setTasks: (tasks: TaskLog[]) => void;
  running: boolean;
  setRunning: (running: boolean) => void;
  connStatus: ConnStatus;
  setConn: (status: ConnStatus) => void;
  mcpCfg: McpConfig;
  setMcpCfg: (config: McpConfig) => void;
  showMcp: boolean;
  setShowMcp: (show: boolean) => void;
  queuedCommand: string | null;
  queueCommand: (command: string | null) => void;
  sessionId: string;
  resetSession: () => string;
  memoryRevision: number;
  bumpMemoryRevision: () => void;
}

export const AppContext = createContext<AppContextValue | null>(null);

export function useApp() {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error("useApp must be used within AppProvider");
  }
  return context;
}

export const CONN_CFG: Record<
  ConnStatus,
  { label: string; dot: string; text: string }
> = {
  disconnected: {
    label: "미연결",
    dot: "bg-slate-400",
    text: "text-muted-foreground",
  },
  connecting: {
    label: "연결 중...",
    dot: "bg-yellow-400 animate-pulse",
    text: "text-yellow-500",
  },
  connected: {
    label: "연결됨",
    dot: "bg-blue-400",
    text: "text-primary",
  },
  error: {
    label: "오류",
    dot: "bg-red-500",
    text: "text-red-500",
  },
};
