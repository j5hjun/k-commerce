"use client";

import { useState, type ReactNode } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Clock,
  List,
  MessageSquare,
  Moon,
  Plug2,
  Settings,
  ShoppingBag,
  Star,
  Sun,
  Terminal,
} from "lucide-react";
import { AppContext, CONN_CFG } from "@/context/app-context";
import { AppRightPanel } from "@/components/layout/app-right-panel";
import { AppSidebar } from "@/components/layout/app-sidebar";
import { McpModal } from "@/components/layout/mcp-modal";
import { cn } from "@/lib/utils";

const TABS = [
  { to: "/", label: "채팅", icon: MessageSquare },
  { to: "/orders", label: "주문 목록", icon: ShoppingBag },
  { to: "/cart", label: "장바구니", icon: List },
  { to: "/reviews", label: "리뷰 작성", icon: Star },
] as const;
const SESSION_STORAGE_KEY = "k-commerce-agent-session";

function createSessionId() {
  return Math.random().toString(36).slice(2, 10);
}

function readSessionId() {
  if (typeof window === "undefined") {
    return "";
  }
  const existing = window.localStorage.getItem(SESSION_STORAGE_KEY);
  if (existing) {
    return existing;
  }
  const created = createSessionId();
  window.localStorage.setItem(SESSION_STORAGE_KEY, created);
  return created;
}

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const [dark, setDark] = useState(false);
  const [tasks, setTasks] = useState<
    import("@/data/taskHistory.mock").TaskLog[]
  >([]);
  const [running, setRunning] = useState(false);
  const [connStatus, setConn] = useState<
    import("@/context/app-context").ConnStatus
  >("disconnected");
  const [mcpCfg, setMcpCfg] = useState({ host: "localhost", port: "8000" });
  const [showMcp, setShowMcp] = useState(false);
  const [queuedCommand, setQueuedCommand] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState(readSessionId);
  const [memoryRevision, setMemoryRevision] = useState(0);

  const connection = CONN_CFG[connStatus];

  const resetSession = () => {
    const nextSessionId = createSessionId();
    if (typeof window !== "undefined") {
      window.localStorage.setItem(SESSION_STORAGE_KEY, nextSessionId);
    }
    setSessionId(nextSessionId);
    setQueuedCommand(null);
    setMemoryRevision(0);
    return nextSessionId;
  };

  return (
    <AppContext.Provider
      value={{
        dark,
        setDark,
        tasks,
        setTasks,
        running,
        setRunning,
        connStatus,
        setConn,
        mcpCfg,
        setMcpCfg,
        showMcp,
        setShowMcp,
        queuedCommand,
        queueCommand: setQueuedCommand,
        sessionId,
        resetSession,
        memoryRevision,
        bumpMemoryRevision: () => setMemoryRevision((value) => value + 1),
      }}
    >
      <div
        className={cn(
          "min-h-screen flex flex-col bg-background text-foreground",
          dark && "dark",
        )}
        style={{ fontFamily: "'Inter', sans-serif" }}
      >
        <header className="h-12 border-b border-border bg-card flex items-center px-5 gap-3 shrink-0">
          <h1>
            <Link href="/" className="flex items-center gap-2">
              <div className="w-5 h-5 bg-primary flex items-center justify-center">
                <Terminal size={11} className="text-white" />
              </div>
              <span className="text-sm font-semibold text-foreground font-mono tracking-tight">
                COUPANG<span className="text-primary">_</span>MCP
              </span>
            </Link>
          </h1>

          <button
            onClick={() => setShowMcp(true)}
            className={cn(
              "flex items-center gap-1.5 px-2.5 py-1 border text-[11px] font-mono font-medium transition-colors duration-150",
              connStatus === "connected" &&
                "border-blue-400 text-blue-600 bg-blue-50 dark:text-blue-400 dark:bg-blue-950/40",
              connStatus === "error" &&
                "border-red-400 text-red-500 bg-red-50 dark:text-red-400 dark:bg-red-950/40",
              connStatus === "connecting" &&
                "border-yellow-400 text-yellow-600 dark:text-yellow-400",
              connStatus === "disconnected" &&
                "border-border text-muted-foreground hover:border-primary hover:text-primary",
            )}
          >
            <span className={cn("w-1.5 h-1.5 rounded-full shrink-0", connection.dot)} />
            {connection.label}
            <Settings size={11} className="opacity-60" />
          </button>

          <div className="hidden sm:flex items-center gap-1 font-mono text-[11px] text-muted-foreground">
            <Clock size={10} />
            <span>{new Date().toLocaleDateString("ko-KR")}</span>
          </div>

          <div className="ml-auto flex items-center gap-3">
            <span className="hidden sm:inline font-mono text-[11px] text-muted-foreground">
              v0.4.2
            </span>
            <button
              onClick={() => setDark((value) => !value)}
              className={cn(
                "flex items-center gap-1.5 px-3 py-1.5 text-xs font-mono font-semibold border transition-colors duration-200",
                dark
                  ? "bg-white text-slate-900 border-slate-200 hover:bg-slate-100"
                  : "bg-slate-900 text-white border-slate-700 hover:bg-slate-800",
              )}
            >
              {dark ? (
                <>
                  <Sun size={12} />
                  라이트 모드
                </>
              ) : (
                <>
                  <Moon size={12} />
                  다크 모드
                </>
              )}
            </button>
          </div>
        </header>

        <div className="flex flex-1 min-h-0">
          <div className="hidden md:flex">
            <AppSidebar tasks={tasks} running={running} />
          </div>

          <main className="flex-1 flex flex-col min-w-0 bg-background">
            <div className="hidden md:flex border-b border-border items-center px-1 shrink-0 bg-card">
              {TABS.map((tab) => {
                const isActive =
                  tab.to === "/"
                    ? pathname === "/"
                    : pathname.startsWith(tab.to);
                const Icon = tab.icon;
                return (
                  <Link
                    key={tab.to}
                    href={tab.to}
                    className={cn(
                      "flex items-center gap-2 px-5 py-3 text-sm font-medium border-b-2 transition-colors duration-150",
                      isActive
                        ? "border-primary text-primary"
                        : "border-transparent text-muted-foreground hover:text-foreground",
                    )}
                  >
                    <Icon size={13} />
                    {tab.label}
                  </Link>
                );
              })}
            </div>

            <div className="flex-1 flex flex-col min-h-0">{children}</div>

            <nav className="md:hidden flex border-t border-border bg-card shrink-0">
              {TABS.map((tab) => {
                const isActive =
                  tab.to === "/"
                    ? pathname === "/"
                    : pathname.startsWith(tab.to);
                const Icon = tab.icon;
                return (
                  <Link
                    key={tab.to}
                    href={tab.to}
                    className={cn(
                      "flex-1 flex flex-col items-center gap-1 py-3 text-[10px] font-mono transition-colors duration-150",
                      isActive ? "text-primary" : "text-muted-foreground",
                    )}
                  >
                    <Icon size={18} />
                    {tab.label}
                  </Link>
                );
              })}
              <button
                onClick={() => setShowMcp(true)}
                className="flex-1 flex flex-col items-center gap-1 py-3 text-[10px] font-mono text-muted-foreground"
              >
                <Plug2 size={18} />
                MCP
              </button>
            </nav>
          </main>

          <div className="hidden lg:flex">
            <AppRightPanel />
          </div>
        </div>

        {showMcp && <McpModal />}
      </div>
    </AppContext.Provider>
  );
}
