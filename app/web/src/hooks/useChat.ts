"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { WS_BASE } from "@/lib/api";
import { stamp } from "@/lib/format";
import { toHistoryPayload } from "@/lib/chatHistory";
import { extractRequestedLimit, trimOrderListResult } from "@/lib/orderSummary";
import { trimSearchListResult } from "@/lib/searchSummary";
import { CART_ACTION_TOOLS } from "@/lib/cartSummary";
import { AUTH_ACTION_TOOLS } from "@/lib/authSummary";
import { REVIEW_ACTION_TOOLS } from "@/lib/reviewSummary";
import type { ChatMessage, ToolCallStatus } from "@/lib/types";

export type ConnectionStatus = "connecting" | "open" | "closed" | "error";

export interface ToolLogEntry {
  id: string;
  name: string;
  time: string;
  ok: boolean;
}

let nextId = 0;
function newId(): string {
  nextId += 1;
  return `m${nextId}`;
}

function nowTime(): string {
  return new Date().toLocaleTimeString("ko-KR", { hour12: false });
}

interface TokenEvent {
  type: "token";
  content: string;
}

interface ToolEvent {
  type: "tool";
  id?: string;
  name: string;
  args: Record<string, unknown>;
}

interface ToolResultEvent {
  type: "tool_result";
  id?: string;
  name: string;
  content: string;
}

interface DoneEvent {
  type: "done";
}

interface ErrorEvent {
  type: "error";
  message: string;
}

type ServerEvent = TokenEvent | ToolEvent | ToolResultEvent | DoneEvent | ErrorEvent;

const LIST_TOOLS = new Set([
  "review_list_reviewable",
  "review_list_editable",
  "search_products",
  "order_list",
  "cart_list",
]);

const CARD_RESULT_TOOLS = new Set([
  ...LIST_TOOLS,
  ...CART_ACTION_TOOLS,
  ...AUTH_ACTION_TOOLS,
  ...REVIEW_ACTION_TOOLS,
]);

function toolResultStatus(content: string): ToolCallStatus {
  try {
    const parsed = JSON.parse(content) as { error?: unknown };
    if (parsed.error) return "failed";
  } catch {
    // keep completed
  }
  return "completed";
}

function itemNamesFromToolResult(result: string): string[] {
  try {
    const parsed = JSON.parse(result) as { items?: unknown[] };
    if (!Array.isArray(parsed.items)) return [];
    return parsed.items
      .map((item) => {
        if (typeof item !== "object" || item === null) return "";
        const record = item as Record<string, unknown>;
        return typeof record.product_name === "string" ? record.product_name : "";
      })
      .filter(Boolean);
  } catch {
    return [];
  }
}

function hasListToolItems(result: string): boolean {
  try {
    const parsed = JSON.parse(result) as { error?: unknown; items?: unknown[]; payload?: unknown };
    if (parsed.error) return false;
    if (Array.isArray(parsed.items) && parsed.items.length > 0) return true;
    const payload = parsed.payload as { orders?: unknown[] } | undefined;
    return Array.isArray(payload?.orders) && payload.orders.length > 0;
  } catch {
    return false;
  }
}

function shouldKeepAssistantAfterListTool(result: string, assistantContent: string): boolean {
  if (!hasListToolItems(result)) return true;

  const trimmed = assistantContent.trim();
  if (!trimmed) return false;

  // 평점·본문·삭제 확인 등 추가 입력만 물을 때만 말풍선 유지
  const asksFollowUp =
    /(평점|몇 점|점수|리뷰 내용|어떤 내용|무엇을 쓸|삭제하시겠|정말 삭제|확인하시겠)/.test(trimmed);
  if (!asksFollowUp) return false;

  const names = itemNamesFromToolResult(result);
  let hits = 0;
  for (const name of names) {
    const head = name.slice(0, Math.min(16, name.length));
    if (head.length >= 4 && trimmed.includes(head)) hits += 1;
  }
  return hits < 2;
}

/** 카드형 도구 결과 직후 assistant 말풍선 제거 (카드만 표시). */
function dropRedundantAssistantAfterToolCard(messages: ChatMessage[]): ChatMessage[] {
  let assistantIdx = -1;
  for (let i = messages.length - 1; i >= 0; i -= 1) {
    if (messages[i].role === "assistant" && messages[i].content.trim()) {
      assistantIdx = i;
      break;
    }
  }
  if (assistantIdx === -1) return messages;

  let toolName: string | null = null;
  let toolResult: string | null = null;
  for (let i = assistantIdx - 1; i >= 0; i -= 1) {
    const m = messages[i];
    if (m.role === "user") break;
    if (
      m.role === "tool" &&
      m.toolCall?.status === "completed" &&
      m.toolCall.result &&
      CARD_RESULT_TOOLS.has(m.toolCall.name)
    ) {
      toolName = m.toolCall.name;
      toolResult = m.toolCall.result;
      break;
    }
  }
  if (!toolName || !toolResult) return messages;

  if (LIST_TOOLS.has(toolName) && shouldKeepAssistantAfterListTool(toolResult, messages[assistantIdx].content)) {
    return messages;
  }

  return messages.filter((_, i) => i !== assistantIdx);
}

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [toolLog, setToolLog] = useState<ToolLogEntry[]>([]);
  const [status, setStatus] = useState<ConnectionStatus>("connecting");
  const [thinking, setThinking] = useState(false);
  const [activeTool, setActiveTool] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [epoch, setEpoch] = useState(0);
  const socketRef = useRef<WebSocket | null>(null);
  const messagesRef = useRef<ChatMessage[]>([]);
  const assistantIdRef = useRef<string | null>(null);
  const seenToolIdsRef = useRef<Set<string>>(new Set());
  const sendingRef = useRef(false);
  const suppressAssistantRef = useRef(false);

  const syncMessages = useCallback((next: ChatMessage[]) => {
    messagesRef.current = next;
    setMessages(next);
  }, []);

  const appendToken = useCallback((chunk: string) => {
    if (suppressAssistantRef.current) return;

    const prev = messagesRef.current;
    let next: ChatMessage[];
    if (assistantIdRef.current) {
      next = prev.map((m) =>
        m.id === assistantIdRef.current ? { ...m, content: m.content + chunk } : m,
      );
    } else {
      const id = newId();
      assistantIdRef.current = id;
      next = [...prev, { id, role: "assistant", content: chunk, time: stamp() }];
    }
    syncMessages(next);
  }, [syncMessages]);

  const appendToolCall = useCallback(
    (name: string, args: Record<string, unknown>, callId?: string) => {
      if (!callId || seenToolIdsRef.current.has(callId)) return;
      seenToolIdsRef.current.add(callId);

      setToolLog((prev) => [{ id: callId, name, time: nowTime(), ok: true }, ...prev].slice(0, 30));
      const call = { id: callId, name, args, status: "running" as const, time: stamp() };
      syncMessages([...messagesRef.current, { id: newId(), role: "tool", content: "", toolCall: call }]);
    },
    [syncMessages],
  );

  const appendToolResult = useCallback((name: string, content: string, callId?: string) => {
    const finalStatus = toolResultStatus(content);
    let resultContent = content;
    if (name === "order_list" && finalStatus === "completed") {
      const lastUser = [...messagesRef.current].reverse().find((m) => m.role === "user");
      const limit = lastUser ? extractRequestedLimit(lastUser.content) : null;
      resultContent = trimOrderListResult(content, limit);
    } else if (name === "search_products" && finalStatus === "completed") {
      const lastUser = [...messagesRef.current].reverse().find((m) => m.role === "user");
      const limit = lastUser ? extractRequestedLimit(lastUser.content) : null;
      if (limit) resultContent = trimSearchListResult(content, limit);
    }
    setToolLog((prev) =>
      prev.map((entry) =>
        callId
          ? entry.id === callId
            ? { ...entry, time: nowTime(), ok: finalStatus !== "failed" }
            : entry
          : entry.name === name && entry.ok
            ? { ...entry, time: nowTime(), ok: finalStatus !== "failed" }
            : entry,
      ),
    );
    setMessages((prev) => {
      const idx = [...prev].reverse().findIndex((m) => {
        if (m.role !== "tool" || !m.toolCall || m.toolCall.status !== "running") return false;
        if (callId) return m.toolCall.id === callId;
        return m.toolCall.name === name;
      });
      if (idx === -1) {
        messagesRef.current = prev;
        return prev;
      }
      const targetIndex = prev.length - 1 - idx;
      const next = prev.map((m, i) =>
        i === targetIndex && m.toolCall
          ? { ...m, toolCall: { ...m.toolCall, result: resultContent, status: finalStatus } }
          : m,
      );
      messagesRef.current = next;
      if (LIST_TOOLS.has(name) && finalStatus === "completed" && hasListToolItems(resultContent)) {
        suppressAssistantRef.current = true;
        assistantIdRef.current = null;
      } else if (CART_ACTION_TOOLS.has(name) && finalStatus === "completed") {
        suppressAssistantRef.current = true;
        assistantIdRef.current = null;
      } else if (AUTH_ACTION_TOOLS.has(name) && finalStatus === "completed") {
        suppressAssistantRef.current = true;
        assistantIdRef.current = null;
      } else if (REVIEW_ACTION_TOOLS.has(name) && finalStatus === "completed") {
        suppressAssistantRef.current = true;
        assistantIdRef.current = null;
      }
      return next;
    });
  }, []);

  useEffect(() => {
    let closedForCleanup = false;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;

    const socket = new WebSocket(`${WS_BASE}/ws/chat`);
    socketRef.current = socket;

    socket.onopen = () => setStatus("open");
    socket.onclose = () => {
      setStatus("closed");
      if (!closedForCleanup) {
        reconnectTimer = setTimeout(() => setEpoch((e) => e + 1), 1500);
      }
    };
    socket.onerror = () => setStatus("error");
    socket.onmessage = (event) => {
      const payload = JSON.parse(event.data) as ServerEvent;

      if (payload.type === "token") {
        setThinking(false);
        setActiveTool(null);
        appendToken(payload.content);
      } else if (payload.type === "tool") {
        setThinking(false);
        setActiveTool(payload.name);
        appendToolCall(payload.name, payload.args, payload.id);
      } else if (payload.type === "tool_result") {
        setActiveTool(null);
        appendToolResult(payload.name, payload.content, payload.id);
      } else if (payload.type === "done") {
        setThinking(false);
        setActiveTool(null);
        sendingRef.current = false;
        suppressAssistantRef.current = false;
        assistantIdRef.current = null;
        seenToolIdsRef.current.clear();
        syncMessages(dropRedundantAssistantAfterToolCard(messagesRef.current));
      } else if (payload.type === "error") {
        setThinking(false);
        setActiveTool(null);
        sendingRef.current = false;
        suppressAssistantRef.current = false;
        setErrorMessage(payload.message);
        assistantIdRef.current = null;
        seenToolIdsRef.current.clear();
      }
    };

    return () => {
      closedForCleanup = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      socket.close();
    };
  }, [appendToken, appendToolCall, appendToolResult, epoch, syncMessages]);

  const reconnect = useCallback(() => {
    setStatus("connecting");
    setEpoch((e) => e + 1);
  }, []);

  const send = useCallback((text: string) => {
    const socket = socketRef.current;
    if (!socket || socket.readyState !== WebSocket.OPEN || sendingRef.current) return;

    sendingRef.current = true;
    setErrorMessage(null);
    setActiveTool(null);
    setThinking(true);
    assistantIdRef.current = null;
    seenToolIdsRef.current.clear();
    suppressAssistantRef.current = false;

    const userMsg: ChatMessage = {
      id: newId(),
      role: "user",
      content: text,
      time: stamp(),
    };
    const history = [...messagesRef.current, userMsg];
    syncMessages(history);
    socket.send(JSON.stringify({ messages: toHistoryPayload(history) }));
  }, [syncMessages]);

  const busy =
    thinking || messages.some((m) => m.role === "tool" && m.toolCall?.status === "running");

  return { messages, toolLog, status, thinking, busy, activeTool, errorMessage, send, reconnect };
}

export type ChatController = ReturnType<typeof useChat>;
