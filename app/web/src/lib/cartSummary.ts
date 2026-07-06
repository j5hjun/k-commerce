export interface CartItemSummary {
  index: number;
  product_name: string;
  option_text?: string;
  quantity?: number;
  unit_price?: string;
  total_price?: string;
  product_id?: string;
  vendor_item_id?: string;
  item_id?: string;
  image_url?: string;
  product_link?: string;
}

export interface CartListViewModel {
  message?: string;
  item_count: number;
  items: CartItemSummary[];
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return typeof value === "object" && value !== null ? (value as Record<string, unknown>) : null;
}

function isCartLikeItem(record: Record<string, unknown>): boolean {
  if (typeof record.product_name !== "string") return false;
  if ("delivery_date" in record || "review_text" in record) return false;
  if ("title" in record && ("order_id" in record || "products" in record)) return false;
  if ("price" in record && !("total_price" in record) && !("unit_price" in record)) return false;
  if (
    "option_text" in record ||
    "quantity" in record ||
    "unit_price" in record ||
    "total_price" in record
  ) {
    return true;
  }
  return (
    "product_id" in record &&
    ("vendor_item_id" in record || "item_id" in record || "product_link" in record) &&
    !("rating" in record)
  );
}

export function parseCartListResult(raw: unknown): CartListViewModel | null {
  const parsed = asRecord(raw);
  if (!parsed) return null;

  const items = parsed.items;
  if (!Array.isArray(items) || items.length === 0) return null;

  const first = asRecord(items[0]);
  if (!first || !isCartLikeItem(first)) return null;

  const cartItems = items.flatMap((item, i) => {
    const record = asRecord(item);
    if (!record || typeof record.product_name !== "string") return [];
    return [
      {
        index: typeof record.index === "number" ? record.index : i + 1,
        product_name: record.product_name,
        option_text: typeof record.option_text === "string" ? record.option_text : undefined,
        quantity: typeof record.quantity === "number" ? record.quantity : undefined,
        unit_price: typeof record.unit_price === "string" ? record.unit_price : undefined,
        total_price: typeof record.total_price === "string" ? record.total_price : undefined,
        product_id: typeof record.product_id === "string" ? record.product_id : undefined,
        vendor_item_id: typeof record.vendor_item_id === "string" ? record.vendor_item_id : undefined,
        item_id: typeof record.item_id === "string" ? record.item_id : undefined,
        image_url: typeof record.image_url === "string" ? record.image_url : undefined,
        product_link: typeof record.product_link === "string" ? record.product_link : undefined,
      },
    ];
  });

  if (cartItems.length === 0) return null;

  return {
    message: typeof parsed.message === "string" ? parsed.message : undefined,
    item_count: typeof parsed.item_count === "number" ? parsed.item_count : cartItems.length,
    items: cartItems,
  };
}

export interface CartQuantityUpdateView {
  success: boolean;
  message?: string;
  quantity: number;
  product_name?: string;
  option_text?: string;
  notice?: string;
}

export interface CartDeleteActionView {
  success: boolean;
  title: string;
  message?: string;
  deleted_count?: number;
}

export const CART_ACTION_TOOLS = new Set([
  "cart_update_quantity",
  "cart_delete_item",
  "cart_delete_items",
  "cart_clear",
]);

export function parseCartQuantityUpdateResult(raw: unknown): CartQuantityUpdateView | null {
  const parsed = asRecord(raw);
  if (!parsed || typeof parsed.quantity !== "number") return null;
  if (!("success" in parsed) || Array.isArray(parsed.items)) return null;

  return {
    success: Boolean(parsed.success),
    message: typeof parsed.message === "string" ? parsed.message : undefined,
    quantity: parsed.quantity,
    product_name: typeof parsed.product_name === "string" && parsed.product_name ? parsed.product_name : undefined,
    option_text: typeof parsed.option_text === "string" && parsed.option_text ? parsed.option_text : undefined,
    notice: typeof parsed.notice === "string" && parsed.notice ? parsed.notice : undefined,
  };
}

export interface CartProductIds {
  product_id?: string;
  vendor_item_id?: string;
  item_id?: string;
}

export function lookupCartProductFromHistory(
  priorMessages: Array<{ role: string; toolCall?: { name?: string; result?: string } }>,
  ids: CartProductIds,
): Pick<CartItemSummary, "product_name" | "option_text"> | null {
  const productId = ids.product_id?.trim() ?? "";
  const vendorItemId = ids.vendor_item_id?.trim() ?? "";
  const itemId = ids.item_id?.trim() ?? "";
  if (!productId && !vendorItemId && !itemId) return null;

  for (let i = priorMessages.length - 1; i >= 0; i -= 1) {
    const message = priorMessages[i];
    if (message.role !== "tool" || message.toolCall?.name !== "cart_list" || !message.toolCall.result) {
      continue;
    }
    try {
      const view = parseCartListResult(JSON.parse(message.toolCall.result));
      if (!view) continue;
      for (const item of view.items) {
        if (vendorItemId && item.vendor_item_id === vendorItemId) {
          return { product_name: item.product_name, option_text: item.option_text };
        }
        if (itemId && item.item_id === itemId) {
          return { product_name: item.product_name, option_text: item.option_text };
        }
        if (productId && item.product_id === productId) {
          return { product_name: item.product_name, option_text: item.option_text };
        }
      }
    } catch {
      continue;
    }
  }
  return null;
}

export function enrichCartQuantityUpdateView(
  view: CartQuantityUpdateView,
  raw: unknown,
  priorMessages: Array<{ role: string; toolCall?: { name?: string; result?: string } }>,
): CartQuantityUpdateView {
  if (view.product_name) return view;
  const parsed = asRecord(raw);
  if (!parsed) return view;
  const found = lookupCartProductFromHistory(priorMessages, {
    product_id: typeof parsed.product_id === "string" ? parsed.product_id : undefined,
    vendor_item_id: typeof parsed.vendor_item_id === "string" ? parsed.vendor_item_id : undefined,
    item_id: typeof parsed.item_id === "string" ? parsed.item_id : undefined,
  });
  if (!found) return view;
  return {
    ...view,
    product_name: found.product_name,
    option_text: view.option_text ?? found.option_text,
  };
}

export function parseCartDeleteActionResult(
  toolName: string,
  raw: unknown,
): CartDeleteActionView | null {
  if (!["cart_delete_item", "cart_delete_items", "cart_clear"].includes(toolName)) return null;

  const parsed = asRecord(raw);
  if (!parsed || !("success" in parsed) || typeof parsed.quantity === "number") return null;

  const titles: Record<string, string> = {
    cart_delete_item: "장바구니 상품 삭제",
    cart_delete_items: "장바구니 상품 삭제",
    cart_clear: "장바구니 비우기",
  };

  return {
    success: Boolean(parsed.success),
    title: titles[toolName] ?? "장바구니 변경",
    message: typeof parsed.message === "string" ? parsed.message : undefined,
    deleted_count: typeof parsed.deleted_count === "number" ? parsed.deleted_count : undefined,
  };
}
