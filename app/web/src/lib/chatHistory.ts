import type { ChatMessage } from "@/lib/types";

type HistoryEntry = { role: "user" | "assistant"; content: string };

export function toHistoryPayload(messages: ChatMessage[]): HistoryEntry[] {
  const out: HistoryEntry[] = [];

  for (const m of messages) {
    if (m.role === "user") {
      out.push({ role: "user", content: m.content });
      continue;
    }
    if (m.role === "assistant" && m.content) {
      out.push({ role: "assistant", content: m.content });
      continue;
    }
  }

  return out;
}
