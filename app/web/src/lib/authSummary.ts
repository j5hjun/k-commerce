export const AUTH_ACTION_TOOLS = new Set(["login", "logout"]);

export interface AuthActionView {
  success: boolean;
  provider?: string;
  title: string;
  message?: string;
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return typeof value === "object" && value !== null ? (value as Record<string, unknown>) : null;
}

export function parseAuthActionResult(toolName: string, raw: unknown): AuthActionView | null {
  if (!AUTH_ACTION_TOOLS.has(toolName)) return null;

  const parsed = asRecord(raw);
  if (!parsed || !("success" in parsed) || "logged_in" in parsed) return null;

  const titles: Record<string, string> = {
    login: "로그인",
    logout: "로그아웃",
  };

  return {
    success: Boolean(parsed.success),
    provider: typeof parsed.provider === "string" ? parsed.provider : undefined,
    title: titles[toolName] ?? "인증",
    message: typeof parsed.message === "string" ? parsed.message : undefined,
  };
}
