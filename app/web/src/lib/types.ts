export type ChatRole = "user" | "assistant" | "system" | "tool";

export type ToolCallStatus = "running" | "completed" | "failed";

export interface ToolCall {
  id: string;
  name: string;
  args: Record<string, unknown>;
  result?: string;
  status: ToolCallStatus;
  time?: string;
}

export interface ChatMessage {
  id: string;
  role: ChatRole;
  content: string;
  time?: string;
  toolCall?: ToolCall;
}

export type McpServerConfig = Record<string, string | string[] | Record<string, string>>;

export interface McpServerInfo {
  name: string;
  transport: string;
  tools: string[];
  config: McpServerConfig;
  error?: string | null;
}
