export interface SearchProductItem {
  index: number;
  product_id?: string;
  product_name: string;
  price?: string;
  rating?: string;
  image_url?: string;
  product_link?: string;
}

export interface SearchListViewModel {
  message?: string;
  item_count: number;
  items: SearchProductItem[];
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return typeof value === "object" && value !== null ? (value as Record<string, unknown>) : null;
}

export function formatSearchPrice(price?: string): string {
  if (!price || price === "-") return "-";
  const trimmed = price.trim();
  if (trimmed.includes("원") || trimmed.includes("쿠폰")) return trimmed;
  const digits = trimmed.replace(/[^\d]/g, "");
  if (!digits) return trimmed;
  const value = Number.parseInt(digits, 10);
  if (!Number.isFinite(value) || value <= 0) return trimmed;
  return `${value.toLocaleString("ko-KR")}원`;
}

export function parseSearchListResult(raw: unknown): SearchListViewModel | null {
  const parsed = asRecord(raw);
  if (!parsed) return null;

  const items = parsed.items;
  if (!Array.isArray(items) || items.length === 0) return null;

  const first = asRecord(items[0]);
  if (!first || typeof first.product_name !== "string") return null;
  if ("delivery_date" in first || "review_text" in first) return null;
  if ("option_text" in first || "quantity" in first || "total_price" in first || "unit_price" in first) {
    return null;
  }
  if (!("product_link" in first || "product_id" in first)) return null;

  const searchItems = items.flatMap((item, i) => {
    const record = asRecord(item);
    if (!record || typeof record.product_name !== "string") return [];
    return [
      {
        index: typeof record.index === "number" ? record.index : i + 1,
        product_id: typeof record.product_id === "string" ? record.product_id : undefined,
        product_name: record.product_name,
        price: typeof record.price === "string" ? record.price : undefined,
        rating: typeof record.rating === "string" ? record.rating : undefined,
        image_url: typeof record.image_url === "string" ? record.image_url : undefined,
        product_link: typeof record.product_link === "string" ? record.product_link : undefined,
      },
    ];
  });

  if (searchItems.length === 0) return null;

  return {
    message: typeof parsed.message === "string" ? parsed.message : undefined,
    item_count: typeof parsed.item_count === "number" ? parsed.item_count : searchItems.length,
    items: searchItems,
  };
}

export function trimSearchListResult(raw: string, limit?: number | null): string {
  try {
    const parsed = JSON.parse(raw) as unknown;
    const view = parseSearchListResult(parsed);
    if (!view || !limit || limit <= 0) return raw;

    const trimmed = {
      ...(typeof parsed === "object" && parsed !== null ? (parsed as Record<string, unknown>) : {}),
      item_count: Math.min(view.items.length, limit),
      items: view.items.slice(0, limit),
    };
    return JSON.stringify(trimmed);
  } catch {
    return raw;
  }
}
