"use client";

import { useEffect, useState } from "react";
import { useChatContext } from "@/context/ChatContext";
import { ClockIcon, GearIcon, MoonIcon, SunIcon, TerminalIcon } from "@/components/icons";

const STATUS_LABEL: Record<string, string> = {
  connecting: "연결 중",
  open: "연결됨",
  closed: "미연결",
  error: "오류",
};

export function TopBar({
  theme,
  onToggleTheme,
}: {
  theme: "light" | "dark";
  onToggleTheme: () => void;
}) {
  const { status } = useChatContext();
  const [today, setToday] = useState("");

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- client-only date, avoids SSR hydration mismatch
    setToday(new Date().toLocaleDateString("ko-KR"));
  }, []);

  const connected = status === "open";

  return (
    <header className="flex items-center justify-between border-b border-line bg-panel px-5 py-3">
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2.5">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent text-accent-ink">
            <TerminalIcon className="h-4 w-4" />
          </span>
          <span className="font-mono text-[15px] font-bold tracking-tight text-ink">AGENT</span>
        </div>

        <span className="flex items-center gap-1.5 rounded-full border border-line bg-panel-muted px-2.5 py-1 text-xs text-muted">
          <span
            className={`h-1.5 w-1.5 rounded-full ${connected ? "bg-emerald-500" : "bg-faint"}`}
          />
          {STATUS_LABEL[status]}
          <GearIcon className="h-3 w-3 text-faint" />
        </span>

        <span className="hidden items-center gap-1.5 text-xs text-muted sm:flex">
          <ClockIcon className="h-3.5 w-3.5 text-faint" />
          {today}
        </span>
      </div>

      <div className="flex items-center gap-3">
        <span className="hidden font-mono text-xs text-faint sm:block">v0.1.0</span>
        <button
          onClick={onToggleTheme}
          className="flex items-center gap-1.5 rounded-lg border border-line bg-panel-muted px-3 py-1.5 text-xs font-medium text-ink transition-colors hover:border-accent/40"
        >
          {theme === "dark" ? (
            <>
              <SunIcon className="h-3.5 w-3.5" /> 라이트 모드
            </>
          ) : (
            <>
              <MoonIcon className="h-3.5 w-3.5" /> 다크 모드
            </>
          )}
        </button>
      </div>
    </header>
  );
}
