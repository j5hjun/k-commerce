import { Terminal, Zap } from "lucide-react";
import { cn } from "@/lib/utils";
import type { ChatMessage } from "@/data/messages.mock";

function formatTime(date: Date) {
  return date.toLocaleTimeString("ko-KR", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}

export function MessageBubble({
  msg,
  onAction,
  busy = false,
}: {
  msg: ChatMessage;
  onAction?: (command: string) => void;
  busy?: boolean;
}) {
  if (msg.role === "system") {
    return (
      <div className="flex items-start gap-2 py-1">
        <Terminal size={11} className="text-primary mt-0.5 shrink-0" />
        <span className="font-mono text-xs text-primary/60 flex-1">
          {msg.content}
        </span>
        {msg.tool && (
          <span className="font-mono text-[10px] text-muted-foreground">
            {msg.tool}
          </span>
        )}
      </div>
    );
  }

  if (msg.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[72%]">
          <div className="bg-primary text-primary-foreground px-4 py-2.5 text-sm leading-relaxed">
            {msg.content}
          </div>
          <div className="text-right mt-1 font-mono text-[10px] text-muted-foreground">
            {formatTime(msg.timestamp)}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex gap-2">
      <div className="w-5 h-5 bg-primary shrink-0 mt-0.5 flex items-center justify-center">
        <Zap size={10} className="text-white" />
      </div>
      <div className="max-w-[80%]">
        <div className="bg-card border border-border px-4 py-2.5 text-sm leading-relaxed text-foreground">
          {msg.content.split("\n").map((line, index) => {
            const html = line
              .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
              .replace(
                /`(.+?)`/g,
                '<code style="font-family:monospace;color:var(--color-primary);background:rgba(37,99,235,0.08);padding:0 3px">$1</code>',
              );
            return (
              <p
                key={index}
                className={line === "" ? "h-2" : ""}
                dangerouslySetInnerHTML={{ __html: html }}
              />
            );
          })}
        </div>
        {msg.actions && msg.actions.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-2">
            {msg.actions.map((action) => (
              <button
                key={action.label}
                onClick={() => onAction?.(action.command)}
                disabled={busy}
                className={cn(
                  "bg-primary text-primary-foreground px-3 py-1.5 text-xs font-medium",
                  "hover:bg-blue-600 transition-colors",
                  "disabled:opacity-40 disabled:cursor-not-allowed",
                )}
              >
                {action.label}
              </button>
            ))}
          </div>
        )}
        <div className="mt-1 font-mono text-[10px] text-muted-foreground">
          {formatTime(msg.timestamp)}
        </div>
      </div>
    </div>
  );
}
