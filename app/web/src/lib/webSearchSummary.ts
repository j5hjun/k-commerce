export interface WebSearchItem {
  index: number;
  title: string;
  url: string;
  snippet: string;
}

export interface WebSearchViewModel {
  query: string;
  item_count: number;
  items: WebSearchItem[];
}

function isWebSearchItem(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && ("title" in value || "url" in value || "href" in value);
}

export function parseWebSearchResult(parsed: unknown, toolName?: string): WebSearchViewModel | null {
  if (toolName && toolName !== "web_search") return null;
  if (typeof parsed !== "object" || parsed === null) return null;

  const record = parsed as Record<string, unknown>;
  const rawItems = record.items;
  if (!Array.isArray(rawItems) || rawItems.length === 0) return null;
  if (!rawItems.every(isWebSearchItem)) return null;
  if (rawItems.some((item) => "product_name" in item)) return null;

  const items: WebSearchItem[] = rawItems
    .map((item, i) => {
      const title = String(item.title ?? "").trim();
      const url = String(item.url ?? item.href ?? "").trim();
      const snippet = String(item.snippet ?? item.body ?? "").trim();
      if (!title && !url) return null;
      return {
        index: typeof item.index === "number" ? item.index : i + 1,
        title: title || url,
        url,
        snippet,
      };
    })
    .filter((item): item is WebSearchItem => item !== null);

  if (!items.length) return null;

  return {
    query: String(record.query ?? "").trim(),
    item_count: typeof record.item_count === "number" ? record.item_count : items.length,
    items,
  };
}

/** 이전 plain-text web_search 결과 호환 */
export function parseWebSearchPlainText(content: string): WebSearchViewModel | null {
  const trimmed = content.trim();
  if (!trimmed || trimmed === "검색 결과가 없습니다.") return null;

  const blocks = trimmed.split(/\n(?=\d+\.\s)/).map((block) => block.trim()).filter(Boolean);
  const items: WebSearchItem[] = [];

  for (const block of blocks) {
    const match = block.match(/^(\d+)\.\s*([\s\S]+?)(?:\n\s*(https?:\/\/\S+))?(?:\n\s*([\s\S]+))?$/);
    if (!match) continue;
    const index = Number(match[1]);
    const title = match[2].trim();
    const url = (match[3] ?? "").trim();
    const snippet = (match[4] ?? "").trim();
    if (!title) continue;
    items.push({
      index: Number.isFinite(index) ? index : items.length + 1,
      title,
      url,
      snippet,
    });
  }

  if (!items.length) return null;

  return {
    query: "",
    item_count: items.length,
    items,
  };
}

export function parseWebSearchContent(content: string, toolName?: string): WebSearchViewModel | null {
  if (toolName && toolName !== "web_search") return null;
  try {
    const parsed = JSON.parse(content) as unknown;
    return parseWebSearchResult(parsed, toolName);
  } catch {
    return parseWebSearchPlainText(content);
  }
}
