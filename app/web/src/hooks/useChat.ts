"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { WS_BASE } from "@/lib/api";
import { stamp } from "@/lib/format";
import { toHistoryPayload } from "@/lib/chatHistory";
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
  status: ToolCallStatus;
}

interface DoneEvent {
  type: "done";
}

interface ErrorEvent {
  type: "error";
  message: string;
}

type ServerEvent = TokenEvent | ToolEvent | ToolResultEvent | DoneEvent | ErrorEvent;

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

  const syncMessages = useCallback((next: ChatMessage[]) => {
    messagesRef.current = next;
    setMessages(next);
  }, []);

  const appendToken = useCallback((chunk: string) => {
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

  const appendToolResult = useCallback((name: string, status: ToolCallStatus, callId?: string) => {
    setToolLog((prev) =>
      prev.map((entry) =>
        callId
          ? entry.id === callId
            ? { ...entry, time: nowTime(), ok: status !== "failed" }
            : entry
          : entry.name === name && entry.ok
            ? { ...entry, time: nowTime(), ok: status !== "failed" }
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
          ? { ...m, toolCall: { ...m.toolCall, status } }
          : m,
      );
      messagesRef.current = next;
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
        appendToolResult(payload.name, payload.status, payload.id);
      } else if (payload.type === "done") {
        setThinking(false);
        setActiveTool(null);
        sendingRef.current = false;
        assistantIdRef.current = null;
        seenToolIdsRef.current.clear();
      } else if (payload.type === "error") {
        setThinking(false);
        setActiveTool(null);
        sendingRef.current = false;
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
