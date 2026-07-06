"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Loader2, RotateCcw, Send, Terminal } from "lucide-react";
import { useRouter } from "next/navigation";
import { MessageBubble } from "@/components/chat/message-bubble";
import { type ConnStatus, useApp } from "@/context/app-context";
import {
  type ChatMessage,
  type MessageAction,
} from "@/data/messages.mock";
import type { TaskLog } from "@/data/taskHistory.mock";
import {
  fetchCachedOrders,
  fetchProviderLoginStatus,
  searchProducts,
  streamChat,
  triggerProviderLogin,
  type OrderGroupSummary,
  type ProductSearchItemSummary,
  type AgentChatMessage,
} from "@/lib/agent";
import { cn } from "@/lib/utils";

const CHAT_HINTS = [
  "로그인 상태 확인",
  "주문목록 가져와줘",
  "장바구니 보여줘",
  "지원 쇼핑몰 알려줘",
];
const OPEN_MCP_MODAL_COMMAND = "__open_mcp_modal__";
const CHAT_STORAGE_PREFIX = "k-commerce-chat";
const PROVIDER = "coupang";
const LOGIN_ACTIONS: MessageAction[] = [
  { label: "로그인하기", command: "로그인 진행해줘" },
  { label: "로그인 상태 확인하기", command: "로그인 상태 확인" },
];
const LOGGED_IN_ACTIONS: MessageAction[] = [
  { label: "주문목록", command: "주문목록 가져와줘" },
  { label: "장바구니 목록", command: "장바구니 목록 가져와줘" },
  { label: "리뷰 작성", command: "리뷰 작성해줘" },
];

function uid() {
  return Math.random().toString(36).slice(2, 9);
}

function storageKey(sessionId: string) {
  return `${CHAT_STORAGE_PREFIX}:${sessionId}`;
}

type ConnectionMessageStatus = Exclude<ConnStatus, "connecting">;

function toConnectionMessageStatus(status: ConnStatus): ConnectionMessageStatus {
  return status === "connecting" ? "disconnected" : status;
}

const LOGIN_PROMPT_MARKERS = [
  "로그인하지 않",
  "로그인되어 있지 않",
  "로그인 후",
  "로그인이 필요",
  "로그인을 진행",
  "로그인 진행",
  "로그인하시겠",
];
const LOGGED_IN_MARKERS = [
  "현재 쿠팡에 로그인되어 있습니다",
  "현재 쿠팡에 로그인된 상태입니다",
  "이미 쿠팡 로그인 상태",
  "쿠팡 로그인 상태예요",
  "쿠팡 로그인이 완료됐어요",
  "로그인에 성공했어요",
];

function detectActions(content: string): MessageAction[] | undefined {
  const isLoggedIn = LOGGED_IN_MARKERS.some((marker) =>
    content.includes(marker),
  );
  if (isLoggedIn) {
    return LOGGED_IN_ACTIONS;
  }
  const needsLogin = LOGIN_PROMPT_MARKERS.some((marker) =>
    content.includes(marker),
  );
  if (needsLogin) {
    return LOGIN_ACTIONS;
  }
  return undefined;
}

function normalizeCommand(command: string) {
  return command.replace(/\s+/g, "").toLowerCase();
}

function isLoginStatusCommand(command: string) {
  const normalized = normalizeCommand(command);
  return normalized.includes("로그인상태확인");
}

function isLoginCommand(command: string) {
  const normalized = normalizeCommand(command);
  return (
    normalized === "로그인진행해줘" ||
    normalized === "로그인하기" ||
    normalized === "자동로그인" ||
    normalized === "쿠팡로그인"
  );
}

function isOrdersCommand(command: string) {
  const normalized = normalizeCommand(command);
  return normalized.includes("주문목록") || normalized.includes("주문내역");
}

function parseOrderDateQuestion(command: string) {
  const normalized = command.replace(/\s+/g, " ");
  const match = normalized.match(
    /(?:(\d{4})\s*년\s*)?(\d{1,2})\s*월\s*(\d{1,2})\s*일.*?(?:산|구매|주문|물건|상품)/,
  );
  if (!match) return null;
  const year = Number(match[1] || new Date().getFullYear());
  const month = Number(match[2]);
  const day = Number(match[3]);
  if (month < 1 || month > 12 || day < 1 || day > 31) return null;
  return `${year}.${String(month).padStart(2, "0")}.${String(day).padStart(2, "0")}`;
}

function formatOrderDateAnswer(date: string, groups: OrderGroupSummary[]) {
  const matched = groups.filter((group) => group.date === date);
  if (matched.length === 0) {
    return `${date}에 저장된 주문 목록에서 찾은 상품이 없습니다.`;
  }
  const lines = matched.flatMap((group) =>
    group.items.map((item) => `- ${item.product} (${item.price} · ${item.quantity}개)`),
  );
  return `${date}에 구매한 상품입니다.\n\n${lines.slice(0, 12).join("\n")}${
    lines.length > 12 ? `\n외 ${lines.length - 12}개` : ""
  }`;
}

function parseProductSearchRequest(command: string) {
  const normalized = command.replace(/\s+/g, " ").trim();
  const isSearchIntent = /(최저가|가장\s*싼|저렴|싸게|검색|찾아줘|찾아|사야|살래|사려고)/.test(
    normalized,
  );
  if (!isSearchIntent) return null;
  if (isOrdersCommand(command) || isCartCommand(command) || isReviewCommand(command)) {
    return null;
  }
  if (/또띠/.test(normalized)) {
    return "또띠아";
  }
  const keyword = normalized
    .replace(/그러면|그럼|나|좀|제발|쿠팡에서|쿠팡|상품|최저가로|최저가|가장\s*싼|저렴한|저렴하게/g, " ")
    .replace(/찾아줘|찾아|검색해줘|검색|사야하는데|사야\s*하는데|사야|살래|사려고|추천해줘|추천/g, " ")
    .replace(/[?!.,~]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
  return keyword || null;
}

function formatProductSearchAnswer(
  keyword: string,
  items: ProductSearchItemSummary[],
) {
  if (items.length === 0) {
    return `${keyword} 검색 결과가 없습니다.`;
  }
  const lines = items
    .slice(0, 5)
    .map((item, index) => {
      const rating = item.rating ? ` · ${item.rating}` : "";
      const price = item.price
        ? `${Number(item.price.replace(/\D/g, "")).toLocaleString("ko-KR")}원`
        : "-";
      return `${index + 1}. ${item.product_name}\n   ${price}${rating}`;
    });
  return `${keyword} 최저가 기준으로 찾은 상품입니다.\n\n${lines.join("\n")}`;
}

function isCartCommand(command: string) {
  const normalized = normalizeCommand(command);
  return normalized.includes("장바구니") && normalized.includes("목록");
}

function isReviewCommand(command: string) {
  const normalized = normalizeCommand(command);
  return normalized.includes("리뷰작성") || normalized.includes("리뷰작성할상품");
}

function isDirectCommerceCommand(command: string) {
  return (
    isLoginStatusCommand(command) ||
    isLoginCommand(command) ||
    parseProductSearchRequest(command) !== null ||
    parseOrderDateQuestion(command) !== null ||
    isOrdersCommand(command) ||
    isCartCommand(command) ||
    isReviewCommand(command)
  );
}

function buildInitialMessages(): ChatMessage[] {
  return [
    {
      id: "init-001",
      role: "assistant",
      content: "안녕하세요. 쿠팡 자동화 도우미입니다.\n\n아직 MCP 연결이 되어 있지 않아요. 먼저 연결할까요?",
      timestamp: new Date(),
      actions: [{ label: "MCP 연결하기", command: OPEN_MCP_MODAL_COMMAND }],
    },
  ];
}

function parseStoredMessages(raw: string | null): ChatMessage[] | null {
  if (!raw) {
    return null;
  }
  try {
    const parsed = JSON.parse(raw) as Array<
      Omit<ChatMessage, "timestamp"> & { timestamp: string }
    >;
    if (!Array.isArray(parsed) || parsed.length === 0) {
      return null;
    }
    return parsed.map((message) => ({
      ...message,
      timestamp: new Date(message.timestamp),
    }));
  } catch {
    return null;
  }
}

function ensureStatusPrompt(
  messages: ChatMessage[],
  status: ConnectionMessageStatus,
) {
  if (status === "connected" || messages.length === 0) {
    return messages;
  }
  const prompt = buildConnectionMessage(status);
  const lastMessage = messages[messages.length - 1];
  if (
    lastMessage?.role === "assistant" &&
    lastMessage.content === prompt.content
  ) {
    return messages;
  }
  return [...messages, prompt];
}

function buildMessagesForStatus(status: ConnectionMessageStatus) {
  if (status === "connected") {
    return [buildConnectionMessage("connected")];
  }
  if (status === "error") {
    return [buildConnectionMessage("error")];
  }
  return buildInitialMessages();
}

function buildConnectionMessage(status: ConnectionMessageStatus): ChatMessage {
  if (status === "connected") {
    return {
      id: uid(),
      role: "assistant",
      content: "MCP 연결이 완료됐어요.\n\n로그인을 먼저 진행할까요?",
      timestamp: new Date(),
      actions: LOGIN_ACTIONS,
    };
  }
  if (status === "error") {
    return {
      id: uid(),
      role: "assistant",
      content: "지금 MCP 연결에 문제가 있어요.\n\n설정을 다시 확인해 볼까요?",
      timestamp: new Date(),
      actions: [{ label: "MCP 연결하기", command: OPEN_MCP_MODAL_COMMAND }],
    };
  }
  return {
    id: uid(),
    role: "assistant",
    content: "아직 MCP 연결이 되어 있지 않아요.\n\n먼저 연결할까요?",
    timestamp: new Date(),
    actions: [{ label: "MCP 연결하기", command: OPEN_MCP_MODAL_COMMAND }],
  };
}

export function DashboardPage() {
  const router = useRouter();
  const {
    setTasks,
    setRunning,
    setConn,
    mcpCfg,
    sessionId,
    bumpMemoryRevision,
    queuedCommand,
    queueCommand,
    connStatus,
    setShowMcp,
    resetSession,
  } = useApp();
  const [messages, setMessages] = useState<ChatMessage[]>(() => {
    if (typeof window === "undefined" || !sessionId) {
      return buildInitialMessages();
    }
    const stored =
      parseStoredMessages(window.localStorage.getItem(storageKey(sessionId))) ??
      buildInitialMessages();
    return ensureStatusPrompt(stored, toConnectionMessageStatus(connStatus));
  });
  const [input, setInput] = useState("");
  const [running, setLocalRunning] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const previousConnStatusRef = useRef(connStatus);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    if (!sessionId || typeof window === "undefined") {
      return;
    }
    window.localStorage.setItem(storageKey(sessionId), JSON.stringify(messages));
  }, [messages, sessionId]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      const previous = previousConnStatusRef.current;
      if (previous === connStatus) {
        return;
      }
      previousConnStatusRef.current = connStatus;
      if (connStatus === "connecting") {
        return;
      }
      setMessages((prev) => [
        ...prev,
        buildConnectionMessage(toConnectionMessageStatus(connStatus)),
      ]);
    }, 0);
    return () => window.clearTimeout(timer);
  }, [connStatus]);

  const resetConversation = useCallback(() => {
    const nextSessionId = resetSession();
    const nextMessages = buildMessagesForStatus(toConnectionMessageStatus(connStatus));
    setMessages(nextMessages);
    setInput("");
    setTasks([]);
    setLocalRunning(false);
    setRunning(false);
    bumpMemoryRevision();
    if (typeof window !== "undefined") {
      window.localStorage.removeItem(storageKey(sessionId));
      window.localStorage.setItem(storageKey(nextSessionId), JSON.stringify(nextMessages));
    }
  }, [
    bumpMemoryRevision,
    connStatus,
    resetSession,
    sessionId,
    setRunning,
    setTasks,
  ]);

  const runDirectCommerceCommand = useCallback(async (text: string) => {
    setMessages((prev) => [
      ...prev,
      { id: uid(), role: "user", content: text, timestamp: new Date() },
    ]);
    setInput("");
    setLocalRunning(true);
    setRunning(true);
    setTasks([]);

    try {
      let content = "";
      let taskName = "";
      let actions: MessageAction[] | undefined;
      const productKeyword = parseProductSearchRequest(text);
      const orderDate = parseOrderDateQuestion(text);

      if (isLoginStatusCommand(text)) {
        taskName = "쿠팡 연동 확인";
        setTasks([{ id: uid(), name: taskName, status: "running", time: "live" }]);
        const response = await fetchProviderLoginStatus(mcpCfg, PROVIDER);
        setConn("connected");
        content = response.logged_in
          ? `쿠팡 연동됨\n\n${response.message || "바로 다음 작업을 진행할 수 있습니다."}`
          : `쿠팡 연동 필요\n\n${response.message || "쿠팡 로그인이 필요합니다."}`;
        actions = response.logged_in ? LOGGED_IN_ACTIONS : LOGIN_ACTIONS;
      } else if (isLoginCommand(text)) {
        taskName = "쿠팡 로그인";
        setTasks([{ id: uid(), name: taskName, status: "running", time: "live" }]);
        const response = await triggerProviderLogin(mcpCfg, PROVIDER);
        setConn(response.success ? "connected" : "error");
        content = response.success
          ? `쿠팡 연동됨\n\n${response.message || "바로 다음 작업을 진행할 수 있습니다."}`
          : `쿠팡 연동 필요\n\n${response.message || "쿠팡 로그인을 완료하지 못했습니다."}`;
        actions = response.success ? LOGGED_IN_ACTIONS : LOGIN_ACTIONS;
      } else if (productKeyword) {
        taskName = "상품 최저가 검색";
        setTasks([{ id: uid(), name: taskName, status: "running", time: "live" }]);
        setConn("connected");
        const response = await searchProducts(mcpCfg, productKeyword, PROVIDER);
        if (!response.success) {
          content = response.message || "상품을 검색하지 못했습니다. 다시 시도해주세요.";
          actions = LOGIN_ACTIONS;
        } else {
          content = formatProductSearchAnswer(productKeyword, response.items);
          actions = LOGGED_IN_ACTIONS;
        }
      } else if (orderDate) {
        taskName = "저장된 주문 검색";
        setTasks([{ id: uid(), name: taskName, status: "running", time: "live" }]);
        setConn("connected");
        const response = await fetchCachedOrders(mcpCfg);
        if (response.groups.length === 0) {
          content = "저장된 주문 목록이 아직 없습니다.\n\n먼저 주문 목록을 불러온 뒤 다시 질문해주세요.";
          actions = [{ label: "주문 목록 불러오기", command: "주문목록 가져와줘" }];
        } else {
          content = formatOrderDateAnswer(orderDate, response.groups);
          actions = [{ label: "주문 목록 보기", command: "주문목록 가져와줘" }];
        }
      } else if (isOrdersCommand(text)) {
        taskName = "주문 목록 화면 열기";
        setTasks([{ id: uid(), name: taskName, status: "running", time: "live" }]);
        setConn("connected");
        router.push("/orders");
        content = "주문 목록 화면을 열었습니다.\n\n주문 목록 불러오기 버튼을 누르면 저장된 주문부터 확인합니다.";
        actions = LOGGED_IN_ACTIONS;
      } else if (isCartCommand(text)) {
        taskName = "장바구니 목록 화면 열기";
        setTasks([{ id: uid(), name: taskName, status: "running", time: "live" }]);
        setConn("connected");
        router.push("/cart");
        content = "장바구니 목록 화면을 열었습니다.\n\n장바구니 목록 불러오기 버튼을 누르면 현재 장바구니를 조회합니다.";
        actions = LOGGED_IN_ACTIONS;
      } else if (isReviewCommand(text)) {
        taskName = "리뷰 작성 화면 열기";
        setTasks([{ id: uid(), name: taskName, status: "running", time: "live" }]);
        setConn("connected");
        router.push("/reviews");
        content = "리뷰 작성 화면을 열었습니다.\n\n새로고침 버튼을 누르면 리뷰 목록을 조회합니다.";
        actions = LOGGED_IN_ACTIONS;
      }

      setTasks([
        {
          id: uid(),
          name: taskName || "작업 완료",
          status: "success",
          time: "live",
        },
      ]);
      setMessages((prev) => [
        ...prev,
        {
          id: uid(),
          role: "assistant",
          content: content || "요청한 작업을 완료했습니다.",
          timestamp: new Date(),
          actions,
        },
      ]);
    } catch {
      setConn("error");
      setTasks([
        {
          id: uid(),
          name: "작업 실패",
          status: "error",
          time: "live",
        },
      ]);
      setMessages((prev) => [
        ...prev,
        {
          id: uid(),
          role: "assistant",
          content: "쿠팡 정보를 불러오지 못했습니다.\n\n연결 상태를 확인한 뒤 다시 시도해주세요.",
          timestamp: new Date(),
          actions: LOGIN_ACTIONS,
        },
      ]);
    } finally {
      bumpMemoryRevision();
      setLocalRunning(false);
      setRunning(false);
    }
  }, [
    bumpMemoryRevision,
    mcpCfg,
    router,
    setConn,
    setRunning,
    setTasks,
  ]);

  const send = useCallback((command?: string) => {
    const text = command ?? input.trim();
    if (!text || running) return;
    if (text === OPEN_MCP_MODAL_COMMAND) {
      setMessages((prev) => [
        ...prev,
        {
          id: uid(),
          role: "user",
          content: "MCP 연결하기",
          timestamp: new Date(),
        },
        {
          id: uid(),
          role: "assistant",
          content: "MCP 연결 설정 창을 열었어요.\n\nHost와 Port를 확인한 뒤 연결 버튼을 눌러주세요.",
          timestamp: new Date(),
        },
      ]);
      setShowMcp(true);
      return;
    }
    if (isDirectCommerceCommand(text)) {
      void runDirectCommerceCommand(text);
      return;
    }

    const history: AgentChatMessage[] = messages
      .filter((message) => message.role === "user" || message.role === "assistant")
      .map((message) => ({ role: message.role, content: message.content }));
    history.push({ role: "user", content: text });

    setMessages((prev) => [
      ...prev,
      { id: uid(), role: "user", content: text, timestamp: new Date() },
    ]);
    setInput("");
    setLocalRunning(true);
    setRunning(true);
    setTasks([]);

    const assistantId = uid();
    const toolTasks: TaskLog[] = [];

    streamChat(mcpCfg, history, sessionId || uid(), {
      onToken: (tokenText) => {
        if (!tokenText) return;
        setConn("connected");
        setMessages((prev) => {
          const index = prev.findIndex((message) => message.id === assistantId);
          if (index === -1) {
            return [
              ...prev,
              {
                id: assistantId,
                role: "assistant",
                content: tokenText,
                timestamp: new Date(),
              },
            ];
          }
          const next = prev.slice();
          next[index] = {
            ...next[index],
            content: next[index].content + tokenText,
          };
          return next;
        });
      },
      onTool: (name) => {
        const taskId = uid();
        const messageId = uid();
        toolTasks.push({ id: taskId, name, status: "success" });
        setTasks([...toolTasks]);
        setMessages((prev) => [
          ...prev,
          {
            id: messageId,
            role: "system",
            content: `도구 실행: ${name}`,
            timestamp: new Date(),
            tool: `mcp:${name}`,
          },
        ]);
      },
      onDone: () => {
        setMessages((prev) => {
          const index = prev.findIndex((message) => message.id === assistantId);
          if (index === -1) return prev;
          const actions = detectActions(prev[index].content);
          if (!actions) return prev;
          const next = prev.slice();
          next[index] = { ...next[index], actions };
          return next;
        });
        bumpMemoryRevision();
        setLocalRunning(false);
        setRunning(false);
      },
      onError: (message) => {
        setConn("error");
        setMessages((prev) => [
          ...prev,
          {
            id: uid(),
            role: "system",
            content: `⚠ ${message}`,
            timestamp: new Date(),
            tool: "error",
          },
        ]);
        bumpMemoryRevision();
        setLocalRunning(false);
        setRunning(false);
      },
    });
  }, [
    bumpMemoryRevision,
    input,
    mcpCfg,
    messages,
    running,
    runDirectCommerceCommand,
    sessionId,
    setConn,
    setRunning,
    setShowMcp,
    setTasks,
  ]);

  useEffect(() => {
    if (!queuedCommand || running) {
      return;
    }
    const timer = window.setTimeout(() => {
      send(queuedCommand);
      queueCommand(null);
    }, 0);
    return () => window.clearTimeout(timer);
  }, [queuedCommand, running, queueCommand, send]);

  return (
    <div className="flex flex-col flex-1 min-h-0">
      <div
        className="flex-1 overflow-y-auto p-5 flex flex-col gap-4"
        style={{ scrollbarWidth: "none" }}
      >
        {messages.map((message) => (
          <MessageBubble
            key={message.id}
            msg={message}
            onAction={(command) => send(command)}
            busy={running}
          />
        ))}
        <div ref={bottomRef} />
      </div>

      <div className="border-t border-border p-4 shrink-0 bg-card">
        <div className="flex gap-2">
          <div className="flex-1 relative">
            <Terminal
              size={13}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground pointer-events-none"
            />
            <input
              value={input}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  send();
                }
              }}
              disabled={running}
              placeholder="명령 입력 또는 질문..."
              className={cn(
                "w-full bg-background border border-border text-foreground placeholder:text-muted-foreground",
                "pl-9 pr-4 py-2.5 text-sm font-mono",
                "focus:outline-none focus:border-primary transition-colors",
                "disabled:opacity-50 disabled:cursor-not-allowed",
              )}
            />
          </div>
          <button
            onClick={() => send()}
            disabled={!input.trim() || running}
            className="bg-primary text-primary-foreground px-4 py-2.5 text-sm font-medium flex items-center gap-2 hover:bg-blue-600 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {running ? (
              <Loader2 size={14} className="animate-spin" />
            ) : (
              <Send size={14} />
            )}
            실행
          </button>
        </div>
        <div className="mt-2 flex gap-3">
          {CHAT_HINTS.map((hint) => (
            <button
              key={hint}
              onClick={() => send(hint)}
              disabled={running}
              className="font-mono text-[11px] text-muted-foreground hover:text-primary transition-colors disabled:opacity-40"
            >
              ↗ {hint}
            </button>
          ))}
          <button
            onClick={resetConversation}
            disabled={running}
            className="font-mono text-[11px] text-muted-foreground hover:text-primary transition-colors disabled:opacity-40 inline-flex items-center gap-1"
          >
            <RotateCcw size={11} />
            대화 초기화
          </button>
        </div>
      </div>
    </div>
  );
}
