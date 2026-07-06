"use client";

import { useCallback, useState } from "react";
import { Loader2, Pencil, Send, Star, Trash2 } from "lucide-react";
import { useApp } from "@/context/app-context";
import {
  createReview,
  deleteReview,
  fetchReviews,
  updateReview,
  type EditableReviewItemSummary,
  type ReviewableItemSummary,
} from "@/lib/agent";
import { cn } from "@/lib/utils";

const PROVIDER = "coupang";

type ReviewTab = "write" | "edit";

export function ReviewsPage() {
  const { connStatus, mcpCfg } = useApp();
  const [tab, setTab] = useState<ReviewTab>("write");
  const [reviewable, setReviewable] = useState<ReviewableItemSummary[]>([]);
  const [editable, setEditable] = useState<EditableReviewItemSummary[]>([]);
  const [selectedReviewableId, setSelectedReviewableId] = useState<string | null>(null);
  const [selectedEditableId, setSelectedEditableId] = useState<string | null>(null);
  const [rating, setRating] = useState(5);
  const [hoverRating, setHoverRating] = useState(0);
  const [content, setContent] = useState("");
  const [loaded, setLoaded] = useState(false);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [needsRefresh, setNeedsRefresh] = useState(false);

  const selectedReviewable = reviewable.find((item) => item.product_id === selectedReviewableId) || null;
  const selectedEditable = editable.find((item) => item.review_id === selectedEditableId) || null;

  const activateReviewable = useCallback((item: ReviewableItemSummary | null) => {
    setSelectedReviewableId(item?.product_id ?? null);
    setRating(5);
    setContent("");
  }, []);

  const activateEditable = useCallback((item: EditableReviewItemSummary | null) => {
    setSelectedEditableId(item?.review_id ?? null);
    setRating(item?.rating || 5);
    setContent(item?.review_text || "");
  }, []);

  const loadReviewData = useCallback(async () => {
    if (connStatus !== "connected") {
      setReviewable([]);
      setEditable([]);
      setLoaded(false);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const response = await fetchReviews(mcpCfg, PROVIDER);
      if (!response.success) {
        setReviewable([]);
        setEditable([]);
        setLoaded(false);
        setError(response.message || "리뷰 목록을 불러오지 못했습니다. 다시 시도해주세요.");
        return;
      }
      const reviewableResponse = response.reviewable;
      const editableResponse = response.editable;

      setReviewable(reviewableResponse.items);
      setEditable(editableResponse.items);
      const nextReviewable =
        reviewableResponse.items.find((item) => item.product_id === selectedReviewableId)
        ?? reviewableResponse.items[0]
        ?? null;
      const nextEditable =
        editableResponse.items.find((item) => item.review_id === selectedEditableId)
        ?? editableResponse.items[0]
        ?? null;
      activateReviewable(nextReviewable);
      activateEditable(nextEditable);
      setLoaded(true);
      setNeedsRefresh(false);
    } catch (fetchError) {
      void fetchError;
      setReviewable([]);
      setEditable([]);
      setLoaded(false);
      setError("리뷰 목록을 불러오지 못했습니다. 다시 시도해주세요.");
    } finally {
      setLoading(false);
    }
  }, [activateEditable, activateReviewable, connStatus, mcpCfg, selectedEditableId, selectedReviewableId]);

  const handleCreate = useCallback(async () => {
    if (!selectedReviewable || !content.trim()) {
      return;
    }

    setSubmitting(true);
    setError(null);
    setMessage(null);
    try {
      const response = await createReview(mcpCfg, {
        provider: PROVIDER,
        order_id: selectedReviewable.completed_order_vendor_item_id,
        product_id: selectedReviewable.product_id,
        rating,
        text: content.trim(),
        review_url: selectedReviewable.review_url,
      });
      if (!response.success) {
        setError(response.message || "리뷰 등록에 실패했습니다.");
        return;
      }
      setMessage(response.message || "리뷰를 등록했습니다.");
      setNeedsRefresh(true);
      setTab("edit");
    } catch (submitError) {
      void submitError;
      setError("리뷰 등록 중 오류가 발생했습니다.");
    } finally {
      setSubmitting(false);
    }
  }, [content, mcpCfg, rating, selectedReviewable]);

  const handleEdit = useCallback(async () => {
    if (!selectedEditable || !content.trim()) {
      return;
    }

    setSubmitting(true);
    setError(null);
    setMessage(null);
    try {
      const response = await updateReview(mcpCfg, selectedEditable.review_id, {
        provider: PROVIDER,
        order_id: selectedEditable.order_id,
        product_id: selectedEditable.product_id,
        rating,
        text: content.trim(),
      });
      if (!response.success) {
        setError(response.message || "리뷰 수정에 실패했습니다.");
        return;
      }
      setMessage(response.message || "리뷰를 수정했습니다.");
      setNeedsRefresh(true);
    } catch (submitError) {
      void submitError;
      setError("리뷰 수정 중 오류가 발생했습니다.");
    } finally {
      setSubmitting(false);
    }
  }, [content, mcpCfg, rating, selectedEditable]);

  const handleDelete = useCallback(async () => {
    if (!selectedEditable) {
      return;
    }

    setSubmitting(true);
    setError(null);
    setMessage(null);
    try {
      const response = await deleteReview(mcpCfg, selectedEditable.review_id, {
        provider: PROVIDER,
        order_id: selectedEditable.order_id,
        product_id: selectedEditable.product_id,
      });
      if (!response.success) {
        setError(response.message || "리뷰 삭제에 실패했습니다.");
        return;
      }
      setMessage(response.message || "리뷰를 삭제했습니다.");
      setNeedsRefresh(true);
      setContent("");
    } catch (submitError) {
      void submitError;
      setError("리뷰 삭제 중 오류가 발생했습니다.");
    } finally {
      setSubmitting(false);
    }
  }, [mcpCfg, selectedEditable]);

  const activeItems = tab === "write" ? reviewable : editable;

  return (
    <div className="flex-1 overflow-y-auto p-5" style={{ scrollbarWidth: "none" }}>
      <div className="mx-auto flex max-w-6xl flex-col gap-5">
        <div className="mb-0">
          <div>
            <h2 className="font-mono text-base font-semibold text-foreground">리뷰 관리</h2>
            <p className="mt-0.5 font-mono text-[11px] text-muted-foreground">
              {loaded
                ? `작성 가능 리뷰 ${reviewable.length}건 · 작성한 리뷰 ${editable.length}건`
                : loading
                  ? "리뷰 목록을 불러오는 중입니다."
                  : "리뷰 목록을 준비하는 중입니다."}
            </p>
          </div>
          {connStatus === "connected" && (
            <button
              onClick={() => void loadReviewData()}
              disabled={loading || connStatus !== "connected"}
              className="mt-4 bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground transition-colors hover:bg-blue-600 disabled:opacity-40"
            >
              {loading ? "불러오는 중..." : loaded ? "다시 불러오기" : "리뷰 목록 불러오기"}
            </button>
          )}
        </div>

        {connStatus !== "connected" && (
          <div className="border border-border bg-secondary px-4 py-3 font-mono text-[11px] text-muted-foreground">
            MCP 연결 후 리뷰 목록을 불러올 수 있습니다. 먼저 MCP를 연결해주세요.
          </div>
        )}

        {error && (
          <div className="border border-red-200 bg-red-50 px-4 py-3 font-mono text-[11px] text-red-600">
            {error}
          </div>
        )}

        {message && (
          <div className="flex flex-wrap items-center justify-between gap-3 border border-blue-200 bg-blue-50 px-4 py-3 font-mono text-[11px] text-blue-700">
            <span>{message}</span>
            {needsRefresh && (
              <button
                onClick={() => void loadReviewData()}
                disabled={loading || connStatus !== "connected"}
                className="bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground transition-colors hover:bg-blue-600 disabled:opacity-40"
              >
                {loading ? "갱신 중..." : "리뷰 목록 갱신"}
              </button>
            )}
          </div>
        )}

        {!loaded && connStatus === "connected" && !error && (
          <div className="border border-border bg-secondary px-4 py-5 font-mono text-[11px] text-muted-foreground">
            리뷰 목록 불러오기 버튼을 누르면 작성 가능한 리뷰와 작성한 리뷰를 조회합니다.
          </div>
        )}

        {loaded && (
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => {
              setTab("write");
              activateReviewable(selectedReviewable ?? reviewable[0] ?? null);
            }}
            className={cn(
              "border px-3 py-1.5 font-mono text-xs transition-colors",
              tab === "write"
                ? "border-primary bg-primary text-primary-foreground"
                : "border-border text-muted-foreground hover:border-primary hover:text-foreground",
            )}
          >
            작성 가능
          </button>
          <button
            onClick={() => {
              setTab("edit");
              activateEditable(selectedEditable ?? editable[0] ?? null);
            }}
            className={cn(
              "border px-3 py-1.5 font-mono text-xs transition-colors",
              tab === "edit"
                ? "border-primary bg-primary text-primary-foreground"
                : "border-border text-muted-foreground hover:border-primary hover:text-foreground",
            )}
          >
            작성한 리뷰
          </button>
        </div>
        )}

        {loaded && (
        <div className="grid gap-5 lg:grid-cols-[340px_minmax(0,1fr)]">
          <section className="border border-border bg-card">
            <div className="border-b border-border px-4 py-3 font-mono text-[11px] text-muted-foreground">
            {tab === "write" ? "리뷰 등록 대상" : "수정/삭제 대상"}
            </div>
            <div className="flex max-h-[560px] flex-col overflow-y-auto">
              {activeItems.length === 0 && !loading && (
                <div className="px-4 py-6 font-mono text-[11px] text-muted-foreground">
                  {tab === "write"
                    ? "작성 가능한 리뷰가 없습니다."
                    : "수정 가능한 리뷰가 없습니다."}
                </div>
              )}
              {tab === "write" && reviewable.map((item) => (
                <button
                  key={item.product_id}
                  onClick={() => activateReviewable(item)}
                  className={cn(
                    "border-b border-border px-4 py-4 text-left transition-colors last:border-b-0",
                    selectedReviewableId === item.product_id
                      ? "bg-secondary/60"
                      : "hover:bg-secondary/30",
                  )}
                >
                  <div className="text-sm text-foreground">{item.product_name}</div>
                  <div className="mt-1 font-mono text-[11px] text-muted-foreground">
                    상품번호 {item.product_id}
                  </div>
                  <div className="mt-1 font-mono text-[11px] text-muted-foreground">
                    배송일 {item.delivery_date || "-"}
                  </div>
                </button>
              ))}
              {tab === "edit" && editable.map((item) => (
                <button
                  key={item.review_id}
                  onClick={() => activateEditable(item)}
                  className={cn(
                    "border-b border-border px-4 py-4 text-left transition-colors last:border-b-0",
                    selectedEditableId === item.review_id
                      ? "bg-secondary/60"
                      : "hover:bg-secondary/30",
                  )}
                >
                  <div className="text-sm text-foreground">{item.product_name}</div>
                  <div className="mt-1 font-mono text-[11px] text-muted-foreground">
                    리뷰 ID {item.review_id}
                  </div>
                  <div className="mt-1 font-mono text-[11px] text-muted-foreground">
                    현재 별점 {item.rating} / 5
                  </div>
                </button>
              ))}
            </div>
          </section>

          <section className="border border-border bg-card">
            <div className="border-b border-border px-5 py-4">
              <div className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
                {tab === "write" ? "Review Create" : "Review Edit"}
              </div>
              <div className="mt-2 text-sm text-foreground">
                {tab === "write"
                  ? (selectedReviewable?.product_name || "리뷰를 작성할 상품을 선택하세요.")
                  : (selectedEditable?.product_name || "수정할 리뷰를 선택하세요.")}
              </div>
            </div>

            <div className="flex flex-col gap-6 px-5 py-5">
              <div>
                <div className="mb-3 font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
                  별점
                </div>
                <div className="flex items-center gap-1">
                  {[1, 2, 3, 4, 5].map((star) => (
                    <button
                      key={star}
                      onClick={() => setRating(star)}
                      onMouseEnter={() => setHoverRating(star)}
                      onMouseLeave={() => setHoverRating(0)}
                      className={cn(
                        "transition-colors",
                        star <= (hoverRating || rating) ? "text-primary" : "text-border",
                      )}
                    >
                      <Star size={24} fill="currentColor" />
                    </button>
                  ))}
                  <span className="ml-3 font-mono text-sm text-muted-foreground">
                    {hoverRating || rating} / 5
                  </span>
                </div>
              </div>

              <div>
                <div className="mb-3 font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
                  리뷰 내용
                </div>
                <textarea
                  value={content}
                  onChange={(event) => setContent(event.target.value)}
                  placeholder="구매하신 상품에 대한 실제 리뷰를 작성하세요."
                  rows={8}
                  className="w-full resize-none border border-border bg-background px-4 py-3 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none"
                />
                <div className="mt-1 text-right font-mono text-[11px] text-muted-foreground">
                  {content.length}자
                </div>
              </div>

              {tab === "edit" && selectedEditable && (
                <div className="border border-border bg-secondary/30 px-4 py-3">
                  <div className="font-mono text-[10px] text-muted-foreground">기존 리뷰 정보</div>
                  <div className="mt-1 font-mono text-[11px] text-muted-foreground">
                    리뷰 ID {selectedEditable.review_id} · 주문 {selectedEditable.order_id}
                  </div>
                </div>
              )}

              <div className="flex flex-wrap gap-2">
                {tab === "write" ? (
                  <button
                    onClick={() => void handleCreate()}
                    disabled={!selectedReviewable || !content.trim() || submitting}
                    className="flex items-center gap-2 bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground transition-colors hover:bg-blue-600 disabled:opacity-40"
                  >
                    {submitting ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />}
                    리뷰 제출
                  </button>
                ) : (
                  <>
                    <button
                      onClick={() => void handleEdit()}
                      disabled={!selectedEditable || !content.trim() || submitting}
                      className="flex items-center gap-2 bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground transition-colors hover:bg-blue-600 disabled:opacity-40"
                    >
                      {submitting ? <Loader2 size={14} className="animate-spin" /> : <Pencil size={14} />}
                      리뷰 수정
                    </button>
                    <button
                      onClick={() => void handleDelete()}
                      disabled={!selectedEditable || submitting}
                      className="flex items-center gap-2 border border-red-300 px-4 py-2.5 text-sm font-medium text-red-600 transition-colors hover:bg-red-50 disabled:opacity-40"
                    >
                      {submitting ? <Loader2 size={14} className="animate-spin" /> : <Trash2 size={14} />}
                      리뷰 삭제
                    </button>
                  </>
                )}
              </div>
            </div>
          </section>
        </div>
        )}
      </div>
    </div>
  );
}
