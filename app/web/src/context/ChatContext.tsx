"use client";

import { createContext, useContext } from "react";
import { useChat, type ChatController } from "@/hooks/useChat";

const ChatContext = createContext<ChatController | null>(null);

export function ChatProvider({ children }: { children: React.ReactNode }) {
  const chat = useChat();
  return <ChatContext.Provider value={chat}>{children}</ChatContext.Provider>;
}

export function useChatContext(): ChatController {
  const ctx = useContext(ChatContext);
  if (!ctx) {
    throw new Error("useChatContext must be used within a ChatProvider");
  }
  return ctx;
}
