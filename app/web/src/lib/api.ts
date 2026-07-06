import type { McpServerInfo } from "./types";

export const HTTP_BASE = process.env.NEXT_PUBLIC_AGENT_HTTP_URL ?? "http://localhost:8000";
export const WS_BASE = HTTP_BASE.replace(/^http/, "ws");

export interface McpServersResponse {
  servers: McpServerInfo[];
}

interface ErrorDetail {
  detail?: string | { failed?: Record<string, string> };
}

function formatServerError(data: ErrorDetail | null): string {
  const detail = data?.detail;
  if (!detail) return "요청을 처리하지 못했습니다.";
  if (typeof detail === "string") return detail;
  if (detail.failed) {
    return Object.entries(detail.failed)
      .map(([name, message]) => `${name}: ${message}`)
      .join("\n");
  }
  return "요청을 처리하지 못했습니다.";
}

export async function fetchMcpServers(): Promise<McpServersResponse> {
  const res = await fetch(`${HTTP_BASE}/api/mcp/servers`);
  if (!res.ok) {
    throw new Error(formatServerError(await res.json().catch(() => null)));
  }
  return res.json();
}

export async function registerMcpServers(rawJson: string): Promise<McpServersResponse> {
  let body: unknown;
  try {
    body = JSON.parse(rawJson);
  } catch {
    throw new Error("JSON 형식이 올바르지 않습니다.");
  }

  const res = await fetch(`${HTTP_BASE}/api/mcp/servers`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  const data = await res.json().catch(() => null);
  if (!res.ok) {
    throw new Error(formatServerError(data));
  }
  return data as McpServersResponse;
}

export async function deleteMcpServer(name: string): Promise<McpServersResponse> {
  const res = await fetch(`${HTTP_BASE}/api/mcp/servers/${encodeURIComponent(name)}`, {
    method: "DELETE",
  });

  const data = await res.json().catch(() => null);
  if (!res.ok) {
    throw new Error(formatServerError(data));
  }
  return data as McpServersResponse;
}
