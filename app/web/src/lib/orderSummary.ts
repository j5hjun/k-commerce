export interface OrderProductSummary {
  name: string;
  quantity?: number;
  price?: number;
}

export interface OrderSummaryItem {
  index: number;
  order_id: number | string;
  title: string;
  ordered_at?: number;
  total_price?: number;
  products: OrderProductSummary[];
}

export interface OrderListViewModel {
  message?: string;
  total_count: number;
  shown_count: number;
  items: OrderSummaryItem[];
}

const DEFAULT_SHOWN_ORDERS = 10;
const MAX_SHOWN_ORDERS = 50;

/** "상위 5개", "5개만" 등 사용자 발화에서 개수 추출 */
export function extractRequestedLimit(text: string): number | null {
  const patterns = [
    /(?:상위|최근|처음)\s*(\d+)\s*(?:개|건)?/i,
    /(\d+)\s*(?:개|건)\s*(?:만)?/,
    /(\d+)\s*(?:개|건)/,
  ];

  for (const pattern of patterns) {
    const match = text.match(pattern);
    if (!match) continue;
    const value = Number.parseInt(match[1], 10);
    if (value > 0 && value <= MAX_SHOWN_ORDERS) return value;
  }
  return null;
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return typeof value === "object" && value !== null ? (value as Record<string, unknown>) : null;
}

function isOrderSummaryItem(record: Record<string, unknown>): boolean {
  if ("review_id" in record || "delivery_date" in record || "review_text" in record) {
    return false;
  }
  if ("product_name" in record && "rating" in record && !("title" in record)) {
    return false;
  }
  return (
    "products" in record ||
    "title" in record ||
    "ordered_at" in record ||
    "total_price" in record
  );
}

function productName(product: Record<string, unknown>): string {
  const name = product.vendorItemName ?? product.productName ?? product.product_name;
  return typeof name === "string" ? name : "";
}

function summarizeOrder(order: Record<string, unknown>, index: number): OrderSummaryItem {
  const products: OrderProductSummary[] = [];
  const groups = order.deliveryGroupList;
  if (Array.isArray(groups)) {
    for (const group of groups) {
      const groupRecord = asRecord(group);
      if (!groupRecord) continue;
      const productList = groupRecord.productList;
      if (!Array.isArray(productList)) continue;
      for (const product of productList) {
        const productRecord = asRecord(product);
        if (!productRecord) continue;
        const name = productName(productRecord);
        if (!name) continue;
        products.push({
          name,
          quantity: typeof productRecord.quantity === "number" ? productRecord.quantity : undefined,
          price:
            typeof productRecord.discountedUnitPrice === "number"
              ? productRecord.discountedUnitPrice
              : typeof productRecord.unitPrice === "number"
                ? productRecord.unitPrice
                : undefined,
        });
      }
    }
  }

  return {
    index,
    order_id: (order.orderId ?? order.order_id ?? index) as number | string,
    title: typeof order.title === "string" ? order.title : `주문 ${index}`,
    ordered_at: typeof order.orderedAt === "number" ? order.orderedAt : undefined,
    total_price: typeof order.totalProductPrice === "number" ? order.totalProductPrice : undefined,
    products,
  };
}

export function parseOrderListResult(raw: unknown): OrderListViewModel | null {
  const parsed = asRecord(raw);
  if (!parsed) return null;

  if (Array.isArray(parsed.items) && parsed.items.length > 0) {
    const first = asRecord(parsed.items[0]);
    if (first && isOrderSummaryItem(first)) {
      return {
        message: typeof parsed.message === "string" ? parsed.message : undefined,
        total_count: typeof parsed.total_count === "number" ? parsed.total_count : parsed.items.length,
        shown_count: typeof parsed.shown_count === "number" ? parsed.shown_count : parsed.items.length,
        items: parsed.items.flatMap((item, i) => {
          const record = asRecord(item);
          if (!record) return [];
          return [
            {
              index: typeof record.index === "number" ? record.index : i + 1,
              order_id: (record.order_id ?? record.orderId ?? i + 1) as number | string,
              title: typeof record.title === "string" ? record.title : `주문 ${i + 1}`,
              ordered_at: typeof record.ordered_at === "number" ? record.ordered_at : undefined,
              total_price: typeof record.total_price === "number" ? record.total_price : undefined,
              products: Array.isArray(record.products)
                ? record.products
                    .map((p) => asRecord(p))
                    .filter((p): p is Record<string, unknown> => p !== null)
                    .map((p) => ({
                      name: typeof p.name === "string" ? p.name : "",
                      quantity: typeof p.quantity === "number" ? p.quantity : undefined,
                      price: typeof p.price === "number" ? p.price : undefined,
                    }))
                    .filter((p) => p.name)
                : [],
            },
          ];
        }),
      };
    }
  }

  const payload = asRecord(parsed.payload);
  const orders = payload?.orders;
  if (!Array.isArray(orders)) return null;

  const meta = asRecord(payload?.meta);
  const summary = asRecord(meta?.summary);
  const totalOrders = summary?.totalOrders;
  const totalCount = typeof totalOrders === "number" ? totalOrders : orders.length;

  return {
    message: typeof parsed.message === "string" ? parsed.message : undefined,
    total_count: totalCount,
    shown_count: orders.length,
    items: orders
      .map((order, i) => {
        const record = asRecord(order);
        return record ? summarizeOrder(record, i + 1) : null;
      })
      .filter((item): item is OrderSummaryItem => item !== null),
  };
}

export function trimOrderListResult(raw: string, limit?: number | null): string {
  try {
    const parsed = JSON.parse(raw) as unknown;
    const view = parseOrderListResult(parsed);
    if (!view) return raw;

    const shown = Math.min(
      view.items.length,
      limit && limit > 0 ? limit : DEFAULT_SHOWN_ORDERS,
    );
    const trimmed: OrderListViewModel = {
      message: view.message,
      total_count: view.total_count,
      shown_count: shown,
      items: view.items.slice(0, shown),
    };
    return JSON.stringify(trimmed);
  } catch {
    return raw;
  }
}

export function formatOrderPrice(value?: number): string {
  if (typeof value !== "number") return "";
  return `${value.toLocaleString("ko-KR")}원`;
}

export function formatOrderedAt(value?: number): string {
  if (typeof value !== "number" || value <= 0) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleDateString("ko-KR");
}
