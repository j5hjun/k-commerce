export const REVIEW_ACTION_TOOLS = new Set(["review_edit", "review_delete", "review_upload"]);

export interface ReviewActionView {
  success: boolean;
  title: string;
  message?: string;
  product_name?: string;
  rating?: number;
  review_text?: string;
  review_id?: string;
}

interface ReviewListItem {
  index?: number;
  review_id?: string;
  product_id?: string;
  order_id?: string;
  product_name?: string;
  rating?: number;
  review_text?: string;
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return typeof value === "object" && value !== null ? (value as Record<string, unknown>) : null;
}

function parseReviewListItems(raw: string): ReviewListItem[] {
  try {
    const parsed = asRecord(JSON.parse(raw));
    if (!parsed || !Array.isArray(parsed.items)) return [];
    return parsed.items
      .map((item) => (asRecord(item) as ReviewListItem | null))
      .filter((item): item is ReviewListItem => item !== null);
  } catch {
    return [];
  }
}

function lookupReviewFromHistory(
  priorMessages: Array<{ role: string; toolCall?: { name?: string; result?: string } }>,
  ids: { review_id?: string; product_id?: string; order_id?: string },
): Pick<ReviewActionView, "product_name" | "rating" | "review_text"> | null {
  const reviewId = ids.review_id?.trim() ?? "";
  const productId = ids.product_id?.trim() ?? "";
  const orderId = ids.order_id?.trim() ?? "";
  if (!reviewId && !productId && !orderId) return null;

  for (let i = priorMessages.length - 1; i >= 0; i -= 1) {
    const message = priorMessages[i];
    const toolName = message.toolCall?.name;
    if (
      message.role !== "tool" ||
      !message.toolCall?.result ||
      (toolName !== "review_list_editable" && toolName !== "review_list_reviewable")
    ) {
      continue;
    }

    for (const item of parseReviewListItems(message.toolCall.result)) {
      if (reviewId && item.review_id === reviewId) {
        return {
          product_name: item.product_name,
          rating: item.rating,
          review_text: item.review_text,
        };
      }
      if (productId && item.product_id === productId) {
        return {
          product_name: item.product_name,
          rating: item.rating,
          review_text: item.review_text,
        };
      }
      if (orderId && item.order_id === orderId) {
        return {
          product_name: item.product_name,
          rating: item.rating,
          review_text: item.review_text,
        };
      }
    }
  }

  return null;
}

function ratingFromArgs(args?: Record<string, unknown>): number | undefined {
  if (!args || typeof args.rating !== "number") return undefined;
  return args.rating;
}

function textFromArgs(args?: Record<string, unknown>): string | undefined {
  if (!args) return undefined;
  const text = args.text ?? args.review_text;
  return typeof text === "string" && text.trim() ? text.trim() : undefined;
}

const ACTION_TITLES: Record<string, string> = {
  review_edit: "리뷰 수정",
  review_delete: "리뷰 삭제",
  review_upload: "리뷰 작성",
};

export function parseReviewActionResult(
  toolName: string,
  raw: unknown,
  priorMessages: Array<{ role: string; toolCall?: { name?: string; result?: string } }> = [],
  toolArgs?: Record<string, unknown>,
): ReviewActionView | null {
  if (!REVIEW_ACTION_TOOLS.has(toolName)) return null;

  const parsed = asRecord(raw);
  if (!parsed || !("success" in parsed) || Array.isArray(parsed.items)) return null;

  const view: ReviewActionView = {
    success: Boolean(parsed.success),
    title: ACTION_TITLES[toolName] ?? "리뷰 작업",
    message: typeof parsed.message === "string" ? parsed.message : undefined,
    review_id: typeof parsed.review_id === "string" && parsed.review_id ? parsed.review_id : undefined,
    product_name:
      typeof parsed.product_name === "string" && parsed.product_name ? parsed.product_name : undefined,
    rating: typeof parsed.rating === "number" ? parsed.rating : undefined,
    review_text:
      typeof parsed.text === "string" && parsed.text
        ? parsed.text
        : typeof parsed.review_text === "string" && parsed.review_text
          ? parsed.review_text
          : undefined,
  };

  if (view.rating === undefined) view.rating = ratingFromArgs(toolArgs);
  if (!view.review_text) view.review_text = textFromArgs(toolArgs);

  if (!view.product_name || view.rating === undefined || !view.review_text) {
    const found = lookupReviewFromHistory(priorMessages, {
      review_id: view.review_id,
      product_id: typeof parsed.product_id === "string" ? parsed.product_id : undefined,
      order_id: typeof parsed.order_id === "string" ? parsed.order_id : undefined,
    });
    if (found) {
      view.product_name = view.product_name ?? found.product_name;
      if (toolName !== "review_edit" && toolName !== "review_upload") {
        view.rating = view.rating ?? found.rating;
        view.review_text = view.review_text ?? found.review_text;
      } else {
        view.rating = view.rating ?? found.rating;
      }
    }
  }

  return view;
}

export function formatReviewStars(rating: number): string {
  const safe = Math.max(0, Math.min(5, rating));
  return `${"★".repeat(safe)}${"☆".repeat(5 - safe)}`;
}
