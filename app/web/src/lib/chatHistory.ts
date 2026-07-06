import type { ChatMessage } from "@/lib/types";
import { parseOrderListResult } from "@/lib/orderSummary";

const LIST_TOOLS = new Set([
  "review_list_reviewable",
  "review_list_editable",
  "search_products",
  "order_list",
  "cart_list",
]);

type HistoryEntry = { role: "user" | "assistant"; content: string };

function compactListItem(toolName: string, item: Record<string, unknown>, index: number) {
  const rowIndex = typeof item.index === "number" ? item.index : index + 1;

  if (toolName === "review_list_editable") {
    return {
      index: rowIndex,
      review_id: item.review_id,
      product_id: item.product_id ?? "",
      order_id: item.order_id ?? "",
      product_name: item.product_name,
      rating: item.rating,
      review_text:
        typeof item.review_text === "string" && item.review_text.length > 120
          ? `${item.review_text.slice(0, 117)}...`
          : item.review_text,
      written_at: item.written_at,
    };
  }

  if (toolName === "review_list_reviewable") {
    return {
      index: rowIndex,
      product_id: item.product_id,
      product_name: item.product_name,
      delivery_date: item.delivery_date,
      completed_order_vendor_item_id: item.completed_order_vendor_item_id,
      vendor_item_id: item.vendor_item_id,
      review_url: item.review_url,
    };
  }

  if (toolName === "search_products") {
    return {
      index: rowIndex,
      product_id: item.product_id,
      product_name: item.product_name,
      price: item.price,
      rating: item.rating,
      image_url: item.image_url,
      product_link: item.product_link,
    };
  }

  if (toolName === "cart_list") {
    return {
      index: rowIndex,
      product_name: item.product_name,
      option_text: item.option_text,
      quantity: item.quantity,
      unit_price: item.unit_price,
      total_price: item.total_price,
      product_id: item.product_id,
      vendor_item_id: item.vendor_item_id,
      item_id: item.item_id,
      image_url: item.image_url,
      product_link: item.product_link,
    };
  }

  return {
    index: rowIndex,
    product_id: item.product_id,
    product_name: item.product_name,
    vendor_item_id: item.vendor_item_id,
    item_id: item.item_id,
  };
}

/** LLM에 보낼 도구 결과 JSON을 필수 필드만 남기고 압축합니다. */
export function compactToolResultForHistory(toolName: string, raw: string): string {
  try {
    const parsed = JSON.parse(raw) as Record<string, unknown>;

    if (toolName === "order_list") {
      const view = parseOrderListResult(parsed);
      if (view) {
        return JSON.stringify({
          message: view.message,
          total_count: view.total_count,
          shown_count: view.shown_count,
          items: view.items.map((item) => ({
            index: item.index,
            order_id: item.order_id,
            title: item.title,
            ordered_at: item.ordered_at,
            total_price: item.total_price,
            products: item.products.slice(0, 3),
          })),
        });
      }
    }

    if (!LIST_TOOLS.has(toolName) || !Array.isArray(parsed.items)) {
      return raw;
    }

    const items = parsed.items.map((item, i) => {
      if (typeof item !== "object" || item === null) return item;
      return compactListItem(toolName, item as Record<string, unknown>, i);
    });

    return JSON.stringify({
      provider: parsed.provider,
      success: parsed.success,
      item_count: items.length,
      items,
    });
  } catch {
    return raw;
  }
}

function toolResultHistoryContent(toolName: string, raw: string): string {
  return `[${toolName} 결과] ${compactToolResultForHistory(toolName, raw)}`;
}

/** WebSocket으로 보낼 대화 기록. 목록 도구는 최신 1건만, JSON은 압축. */
export function toHistoryPayload(messages: ChatMessage[]): HistoryEntry[] {
  const out: HistoryEntry[] = [];
  const latestListToolIdx = new Map<string, number>();

  for (const m of messages) {
    if (m.role === "user") {
      out.push({ role: "user", content: m.content });
      continue;
    }
    if (m.role === "assistant" && m.content) {
      out.push({ role: "assistant", content: m.content });
      continue;
    }
    if (m.role === "tool" && m.toolCall?.result) {
      const name = m.toolCall.name;
      const entry: HistoryEntry = {
        role: "assistant",
        content: toolResultHistoryContent(name, m.toolCall.result),
      };
      if (LIST_TOOLS.has(name)) {
        const prev = latestListToolIdx.get(name);
        if (prev !== undefined) {
          out[prev] = entry;
        } else {
          latestListToolIdx.set(name, out.length);
          out.push(entry);
        }
      } else {
        out.push(entry);
      }
    }
  }

  return out;
}
