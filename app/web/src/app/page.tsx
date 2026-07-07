"use client";

import { useEffect, useState } from "react";
import { ChatProvider } from "@/context/ChatContext";
import { useMcpServers } from "@/hooks/useMcpServers";
import { TopBar } from "@/components/TopBar";
import { McpPanel } from "@/components/McpPanel";
import { ChatPanel } from "@/components/ChatPanel";
import { StatusPanel } from "@/components/StatusPanel";

type Theme = "light" | "dark";

export default function Home() {
  const { servers, error, refresh } = useMcpServers();
  const [theme, setTheme] = useState<Theme>("light");

  useEffect(() => {
    const saved = localStorage.getItem("theme") as Theme | null;
    // eslint-disable-next-line react-hooks/set-state-in-effect -- read persisted theme on mount
    if (saved === "dark") setTheme("dark");
  }, []);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark");
    localStorage.setItem("theme", theme);
  }, [theme]);

  return (
    <ChatProvider>
      <div className="flex h-screen flex-col overflow-hidden">
        <TopBar theme={theme} onToggleTheme={() => setTheme((t) => (t === "dark" ? "light" : "dark"))} />
        <div className="flex flex-1 overflow-hidden">
          <McpPanel servers={servers} error={error} onRefresh={refresh} />
          <main className="min-w-0 flex-1">
            <ChatPanel servers={servers} />
          </main>
          <StatusPanel servers={servers} />
        </div>
      </div>
    </ChatProvider>
  );
}
