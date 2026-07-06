export type MessageRole = "user" | "assistant" | "system";

export interface MessageAction {
  label: string;
  command: string;
}

export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  timestamp: Date;
  tool?: string;
  actions?: MessageAction[];
}

export const CHAT_HINTS = ["자동 로그인", "주문 목록 보여줘", "리뷰 작성해줘"];
