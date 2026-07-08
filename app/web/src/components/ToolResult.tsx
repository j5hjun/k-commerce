"use client";

import {
  formatOrderedAt,
  formatOrderPrice,
  parseOrderListResult,
  type OrderListViewModel,
} from "@/lib/orderSummary";
import {
  enrichCartQuantityUpdateView,
  parseCartDeleteActionResult,
  parseCartListResult,
  parseCartQuantityUpdateResult,
  type CartDeleteActionView,
  type CartListViewModel,
  type CartQuantityUpdateView,
} from "@/lib/cartSummary";
import { parseAuthActionResult, type AuthActionView } from "@/lib/authSummary";
import {
  formatSearchPrice,
  parseSearchListResult,
  type SearchListViewModel,
} from "@/lib/searchSummary";
import { parseReviewActionResult, formatReviewStars, type ReviewActionView } from "@/lib/reviewSummary";
import type { ChatMessage } from "@/lib/types";

interface StatusPayload {
  provider?: string;
  logged_in?: boolean;
  message?: string;
}

interface ReviewableItem {
  index?: number;
  product_id?: string;
  product_name?: string;
  delivery_date?: string;
}

interface EditableReviewItem {
  index?: number;
  review_id?: string;
  product_id?: string;
  product_name?: string;
  rating?: number;
  review_text?: string;
  written_at?: string;
  delivery_date?: string;
}

interface ToolErrorPayload {
  error?: {
    type?: string;
    message?: string;
    tool_name?: string;
  };
}

function isReviewableItem(value: unknown): value is ReviewableItem {
  return (
    typeof value === "object" &&
    value !== null &&
    "product_name" in value &&
    "delivery_date" in value &&
    !("product_link" in value)
  );
}

function isEditableReviewItem(value: unknown): value is EditableReviewItem {
  return (
    typeof value === "object" &&
    value !== null &&
    "product_name" in value &&
    ("review_text" in value || "review_id" in value || "rating" in value) &&
    !("delivery_date" in value)
  );
}

function isStatusPayload(value: unknown): value is StatusPayload {
  return typeof value === "object" && value !== null && "logged_in" in value;
}

function isToolErrorPayload(value: unknown): value is ToolErrorPayload {
  return typeof value === "object" && value !== null && "error" in value;
}

function parseJson(content: string): unknown {
  try {
    return JSON.parse(content);
  } catch {
    return null;
  }
}

export function ToolResult({
  content,
  toolName,
  priorMessages = [],
  toolArgs,
}: {
  content: string;
  toolName?: string;
  priorMessages?: ChatMessage[];
  toolArgs?: Record<string, unknown>;
}) {
  const parsed = parseJson(content);

  if (isToolErrorPayload(parsed) && parsed.error) {
    return (
      <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-500">
        <p className="font-medium">도구 실행 실패</p>
        <p className="mt-1 whitespace-pre-wrap">{parsed.error.message ?? content}</p>
      </div>
    );
  }

  if (isStatusPayload(parsed)) {
    const loggedIn = Boolean(parsed.logged_in);
    return (
      <div className="rounded-xl border border-line bg-panel px-4 py-3 text-sm">
        <div className="flex items-center gap-2">
          <span
            className={`inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-semibold ${
              loggedIn ? "bg-emerald-500/10 text-emerald-600" : "bg-amber-500/10 text-amber-600"
            }`}
          >
            {loggedIn ? "로그인됨" : "미로그인"}
          </span>
          {parsed.provider && (
            <span className="font-mono text-[11px] text-faint">{parsed.provider}</span>
          )}
        </div>
        {parsed.message && <p className="mt-2 text-ink">{parsed.message}</p>}
      </div>
    );
  }

  if (toolName) {
    const authView = parseAuthActionResult(toolName, parsed);
    if (authView) return <AuthActionCard view={authView} />;

    const reviewView = parseReviewActionResult(toolName, parsed, priorMessages, toolArgs);
    if (reviewView) return <ReviewActionCard view={reviewView} />;
  }

  if (
    toolName === "review_list_reviewable" &&
    parsed &&
    typeof parsed === "object" &&
    "items" in parsed
  ) {
    const items = (parsed as { items: unknown }).items;
    if (Array.isArray(items) && items.length > 0 && items.every(isReviewableItem)) {
      return <ReviewableList items={items} />;
    }
  }

  if (
    toolName === "review_list_editable" &&
    parsed &&
    typeof parsed === "object" &&
    "items" in parsed
  ) {
    const items = (parsed as { items: unknown }).items;
    if (Array.isArray(items) && items.length > 0 && items.every(isEditableReviewItem)) {
      return <EditableReviewList items={items} title="수정·삭제 가능한 리뷰" />;
    }
  }

  const orderView = toolName === "order_list" ? parseOrderListResult(parsed) : null;
  if (orderView && orderView.items.length > 0) {
    return <OrderListView view={orderView} />;
  }

  if (toolName === "cart_list") {
    const cartView = parseCartListResult(parsed);
    if (cartView && cartView.items.length > 0) {
      return <CartListView view={cartView} />;
    }
  } else if (toolName === "search_products") {
    const searchView = parseSearchListResult(parsed);
    if (searchView && searchView.items.length > 0) {
      return <SearchProductList view={searchView} />;
    }
  } else {
    const cartView = parseCartListResult(parsed);
    if (cartView && cartView.items.length > 0) {
      return <CartListView view={cartView} />;
    }
    const searchView = parseSearchListResult(parsed);
    if (searchView && searchView.items.length > 0) {
      return <SearchProductList view={searchView} />;
    }
  }

  if (toolName === "cart_update_quantity" || !toolName) {
    const quantityView = parseCartQuantityUpdateResult(parsed);
    if (quantityView) {
      const enriched = enrichCartQuantityUpdateView(quantityView, parsed, priorMessages);
      return <CartQuantityUpdateCard view={enriched} />;
    }
  }

  if (toolName) {
    const deleteView = parseCartDeleteActionResult(toolName, parsed);
    if (deleteView) return <CartDeleteActionCard view={deleteView} />;
  }

  if (parsed && typeof parsed === "object" && "items" in parsed) {
    const items = (parsed as { items: unknown }).items;
    if (Array.isArray(items) && items.length > 0) {
      if (items.every(isReviewableItem)) {
        return <ReviewableList items={items} />;
      }
      if (items.every(isEditableReviewItem)) {
        return (
          <EditableReviewList
            items={items}
            title={toolName === "review_list_editable" ? "수정·삭제 가능한 리뷰" : "작성한 리뷰"}
          />
        );
      }
    }
  }

  if (parsed !== null) {
    const fallbackOrder = toolName === "order_list" ? parseOrderListResult(parsed) : null;
    if (fallbackOrder && fallbackOrder.items.length > 0) {
      return <OrderListView view={fallbackOrder} />;
    }
    return (
      <pre className="max-h-64 overflow-auto rounded-xl border border-line bg-panel-muted p-3 font-mono text-[11px] leading-relaxed text-muted">
        {JSON.stringify(parsed, null, 2)}
      </pre>
    );
  }

  return (
    <pre className="max-h-64 overflow-auto whitespace-pre-wrap rounded-xl border border-line bg-panel-muted p-3 font-mono text-[11px] leading-relaxed text-muted">
      {content}
    </pre>
  );
}

function SearchProductList({ view }: { view: SearchListViewModel }) {
  const more =
    view.item_count > view.items.length
      ? `${view.items.length}건 표시`
      : `${view.item_count}건`;

  return (
    <div className="rounded-xl border border-line bg-panel px-4 py-3 text-sm">
      <p className="font-medium text-ink">검색 결과 ({more})</p>
      <ol className="mt-3 max-h-96 space-y-3 overflow-y-auto">
        {view.items.map((item) => (
          <li key={item.index} className="flex gap-3 text-ink">
            <span className="shrink-0 pt-0.5 font-mono text-xs text-faint">{item.index}.</span>
            {item.image_url ? (
              <a
                href={item.product_link}
                target="_blank"
                rel="noopener noreferrer"
                className="shrink-0"
              >
                {/* eslint-disable-next-line @next/next/no-img-element -- external Coupang CDN */}
                <img
                  src={item.image_url}
                  alt={item.product_name}
                  className="h-14 w-14 rounded-lg border border-line object-cover"
                />
              </a>
            ) : null}
            <div className="min-w-0 flex-1">
              <a
                href={item.product_link}
                target="_blank"
                rel="noopener noreferrer"
                className="font-medium leading-snug hover:text-accent"
              >
                {item.product_name}
              </a>
              <div className="mt-0.5 flex flex-wrap gap-2 text-[11px] text-faint">
                <span className="font-semibold text-accent">{formatSearchPrice(item.price)}</span>
                {item.rating && item.rating !== "-" && <span>리뷰 {item.rating}</span>}
                {item.product_id && <span className="font-mono">ID {item.product_id}</span>}
              </div>
            </div>
          </li>
        ))}
      </ol>
      <p className="mt-3 text-[11px] text-faint">번호를 말씀해 주시면 이어서 진행합니다.</p>
    </div>
  );
}

function ReviewableList({ items }: { items: ReviewableItem[] }) {
  return (
    <div className="rounded-xl border border-line bg-panel px-4 py-3 text-sm">
      <p className="font-medium text-ink">리뷰 작성 가능 ({items.length}건)</p>
      <ol className="mt-3 max-h-80 space-y-2 overflow-y-auto">
        {items.map((item, i) => (
          <li key={item.index ?? i} className="flex gap-2 text-ink">
            <span className="shrink-0 font-mono text-xs text-faint">{item.index ?? i + 1}.</span>
            <div className="min-w-0">
              <p className="leading-snug">{item.product_name}</p>
              {item.delivery_date && (
                <p className="mt-0.5 text-[11px] text-faint">배송일 {item.delivery_date}</p>
              )}
            </div>
          </li>
        ))}
      </ol>
      <p className="mt-3 text-[11px] text-faint">번호를 말씀해 주시면 이어서 진행합니다.</p>
    </div>
  );
}

function formatStars(rating: number): string {
  const safe = Math.max(0, Math.min(5, rating));
  return `${"★".repeat(safe)}${"☆".repeat(5 - safe)}`;
}

function EditableReviewList({
  items,
  title = "작성한 리뷰",
}: {
  items: EditableReviewItem[];
  title?: string;
}) {
  return (
    <div className="rounded-xl border border-line bg-panel px-4 py-3 text-sm">
      <p className="font-medium text-ink">
        {title} ({items.length}건)
      </p>
      <ol className="mt-3 max-h-80 space-y-2 overflow-y-auto">
        {items.map((item, i) => (
          <li key={item.index ?? i} className="flex gap-2 text-ink">
            <span className="shrink-0 font-mono text-xs text-faint">{item.index ?? i + 1}.</span>
            <div className="min-w-0">
              <p className="leading-snug">{item.product_name}</p>
              <div className="mt-0.5 flex flex-wrap items-center gap-2 text-[11px] text-faint">
                {typeof item.rating === "number" && item.rating > 0 && (
                  <span>{formatStars(item.rating)}</span>
                )}
                {item.delivery_date && <span>배송 {item.delivery_date}</span>}
                {item.written_at && <span>작성 {item.written_at}</span>}
                {item.review_id && <span className="font-mono">ID {item.review_id}</span>}
              </div>
              {item.review_text && (
                <p className="mt-1 line-clamp-3 text-[12px] leading-relaxed text-muted">
                  {item.review_text}
                </p>
              )}
            </div>
          </li>
        ))}
      </ol>
      <p className="mt-3 text-[11px] text-faint">
        번호를 말씀해 주시면 수정·삭제를 이어서 진행합니다.
      </p>
    </div>
  );
}

function ReviewActionCard({ view }: { view: ReviewActionView }) {
  return (
    <div className="rounded-xl border border-line bg-panel px-4 py-3 text-sm">
      {view.product_name && <p className="font-medium leading-snug text-ink">{view.product_name}</p>}
      <div className={`flex flex-wrap items-center gap-2 ${view.product_name ? "mt-2" : ""}`}>
        <span
          className={`inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-semibold ${
            view.success ? "bg-emerald-500/10 text-emerald-600" : "bg-red-500/10 text-red-500"
          }`}
        >
          {view.success ? `${view.title} 완료` : `${view.title} 실패`}
        </span>
        {typeof view.rating === "number" && view.rating > 0 && (
          <span className="text-[11px] text-faint">
            {formatReviewStars(view.rating)} ({view.rating}점)
          </span>
        )}
      </div>
      {view.review_text && (
        <p className="mt-2 whitespace-pre-wrap text-ink">{view.review_text}</p>
      )}
      {!view.product_name && view.review_id && (
        <p className="mt-2 font-mono text-[11px] text-faint">리뷰 ID {view.review_id}</p>
      )}
      {view.message &&
        view.message !== "쿠팡 리뷰 수정 성공" &&
        view.message !== "쿠팡 리뷰 삭제 성공" &&
        view.message !== "쿠팡 리뷰 업로드 성공" && (
          <p className="mt-2 text-muted">{view.message}</p>
        )}
    </div>
  );
}

function AuthActionCard({ view }: { view: AuthActionView }) {
  return (
    <div className="rounded-xl border border-line bg-panel px-4 py-3 text-sm">
      <div className="flex items-center gap-2">
        <span
          className={`inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-semibold ${
            view.success ? "bg-emerald-500/10 text-emerald-600" : "bg-red-500/10 text-red-500"
          }`}
        >
          {view.success ? `${view.title} 완료` : `${view.title} 실패`}
        </span>
        {view.provider && <span className="font-mono text-[11px] text-faint">{view.provider}</span>}
      </div>
      {view.message && <p className="mt-2 text-ink">{view.message}</p>}
    </div>
  );
}

function CartQuantityUpdateCard({ view }: { view: CartQuantityUpdateView }) {
  return (
    <div className="rounded-xl border border-line bg-panel px-4 py-3 text-sm">
      {view.product_name && <p className="font-medium leading-snug text-ink">{view.product_name}</p>}
      {view.option_text && <p className="mt-0.5 text-[11px] text-faint">{view.option_text}</p>}
      <div className={`flex flex-wrap items-center gap-2 ${view.product_name ? "mt-2" : ""}`}>
        <span
          className={`inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-semibold ${
            view.success ? "bg-emerald-500/10 text-emerald-600" : "bg-red-500/10 text-red-500"
          }`}
        >
          {view.success ? "수량 변경 완료" : "수량 변경 실패"}
        </span>
        {view.success && (
          <span className="text-[11px] text-faint">
            적용 수량 <span className="font-semibold text-ink">{view.quantity.toLocaleString("ko-KR")}개</span>
          </span>
        )}
      </div>
      {view.notice && <p className="mt-2 text-ink">{view.notice}</p>}
      {!view.notice && view.message && view.message !== "쿠팡 장바구니 수량 수정 성공" && (
        <p className="mt-2 text-ink">{view.message}</p>
      )}
    </div>
  );
}

function CartDeleteActionCard({ view }: { view: CartDeleteActionView }) {
  return (
    <div className="rounded-xl border border-line bg-panel px-4 py-3 text-sm">
      <div className="flex items-center gap-2">
        <span
          className={`inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-semibold ${
            view.success ? "bg-emerald-500/10 text-emerald-600" : "bg-red-500/10 text-red-500"
          }`}
        >
          {view.success ? view.title : `${view.title} 실패`}
        </span>
        {view.success && typeof view.deleted_count === "number" && view.deleted_count > 0 && (
          <span className="text-[11px] text-faint">{view.deleted_count}건 삭제</span>
        )}
      </div>
      {view.message && <p className="mt-2 text-ink">{view.message}</p>}
    </div>
  );
}

function CartListView({ view }: { view: CartListViewModel }) {
  return (
    <div className="rounded-xl border border-line bg-panel px-4 py-3 text-sm">
      <p className="font-medium text-ink">장바구니 ({view.item_count}건)</p>
      <ol className="mt-3 max-h-96 space-y-3 overflow-y-auto">
        {view.items.map((item) => (
          <li key={item.index} className="flex gap-3 text-ink">
            <span className="shrink-0 pt-0.5 font-mono text-xs text-faint">{item.index}.</span>
            {item.image_url ? (
              <a
                href={item.product_link}
                target="_blank"
                rel="noopener noreferrer"
                className="shrink-0"
              >
                {/* eslint-disable-next-line @next/next/no-img-element -- external Coupang CDN */}
                <img
                  src={item.image_url}
                  alt={item.product_name}
                  className="h-14 w-14 rounded-lg border border-line object-cover"
                />
              </a>
            ) : null}
            <div className="min-w-0 flex-1">
              {item.product_link ? (
                <a
                  href={item.product_link}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="font-medium leading-snug hover:text-accent"
                >
                  {item.product_name}
                </a>
              ) : (
                <p className="font-medium leading-snug">{item.product_name}</p>
              )}
              <div className="mt-0.5 flex flex-wrap gap-2 text-[11px] text-faint">
                {item.option_text && <span>{item.option_text}</span>}
                {typeof item.quantity === "number" && <span>수량 {item.quantity}</span>}
                <span className="font-semibold text-accent">
                  {formatSearchPrice(item.total_price || item.unit_price)}
                </span>
                {item.product_id && <span className="font-mono">ID {item.product_id}</span>}
              </div>
            </div>
          </li>
        ))}
      </ol>
      <p className="mt-3 text-[11px] text-faint">번호를 말씀해 주시면 수량 변경·삭제를 이어서 진행합니다.</p>
    </div>
  );
}

function OrderListView({ view }: { view: OrderListViewModel }) {
  const more =
    view.total_count > view.shown_count
      ? `전체 ${view.total_count.toLocaleString("ko-KR")}건 중 ${view.shown_count}건`
      : `${view.shown_count}건`;

  return (
    <div className="rounded-xl border border-line bg-panel px-4 py-3 text-sm">
      <p className="font-medium text-ink">주문 목록 ({more})</p>
      {view.message && <p className="mt-1 text-[11px] text-faint">{view.message}</p>}
      <ol className="mt-3 max-h-80 space-y-3 overflow-y-auto">
        {view.items.map((item) => (
          <li key={item.index} className="flex gap-2 text-ink">
            <span className="shrink-0 font-mono text-xs text-faint">{item.index}.</span>
            <div className="min-w-0">
              <p className="font-medium leading-snug">{item.title}</p>
              <div className="mt-0.5 flex flex-wrap gap-2 text-[11px] text-faint">
                {formatOrderedAt(item.ordered_at) && <span>{formatOrderedAt(item.ordered_at)}</span>}
                <span className="font-mono">주문번호 {item.order_id}</span>
                {formatOrderPrice(item.total_price) && (
                  <span>{formatOrderPrice(item.total_price)}</span>
                )}
              </div>
              <ul className="mt-1 space-y-0.5 text-[12px] text-muted">
                {item.products.map((product, i) => (
                  <li key={i} className="truncate">
                    {product.name}
                    {product.quantity ? ` × ${product.quantity}` : ""}
                    {formatOrderPrice(product.price) ? ` · ${formatOrderPrice(product.price)}` : ""}
                  </li>
                ))}
              </ul>
            </div>
          </li>
        ))}
      </ol>
      <p className="mt-3 text-[11px] text-faint">번호를 말씀해 주시면 이어서 진행합니다.</p>
    </div>
  );
}
