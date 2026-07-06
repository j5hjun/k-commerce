"use client";

import { useCallback, useEffect, useState } from "react";
import { useApp } from "@/context/app-context";
import {
  clearCart,
  deleteCartItem,
  deleteCartItems,
  fetchCart,
  loadCartSnapshot,
  updateCartQuantity,
  type CartItemSummary,
} from "@/lib/agent";

const PROVIDER = "coupang";

export function CartPage() {
  const { connStatus, mcpCfg } = useApp();
  const [items, setItems] = useState<CartItemSummary[]>([]);
  const [message, setMessage] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [loading, setLoading] = useState(false);
  const [mutating, setMutating] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedKeys, setSelectedKeys] = useState<string[]>([]);
  const [quantities, setQuantities] = useState<Record<string, number>>({});
  const [collectedAt, setCollectedAt] = useState<string | null>(null);

  function itemKey(item: CartItemSummary) {
    return `${item.product_id}:${item.vendor_item_id}:${item.item_id}`;
  }

  function itemIdentity(item: CartItemSummary) {
    return {
      product_id: item.product_id,
      vendor_item_id: item.vendor_item_id,
      item_id: item.item_id,
    };
  }

  const applyCart = useCallback((response: Awaited<ReturnType<typeof fetchCart>>) => {
    setItems(response.items);
    setSelectedKeys([]);
    setQuantities(
      Object.fromEntries(
        response.items.map((item) => [itemKey(item), item.quantity]),
      ),
    );
    setMessage(response.message);
    setCollectedAt(response.collected_at ?? null);
    setLoaded(true);
  }, []);

  useEffect(() => {
    let cancelled = false;
    async function loadCachedCart() {
      if (connStatus !== "connected" || loaded || loading) {
        return;
      }
      try {
        const response = await loadCartSnapshot(mcpCfg, PROVIDER);
        if (cancelled || !response.success) {
          return;
        }
        applyCart(response);
      } catch {
        // 저장된 장바구니가 없거나 읽지 못하면 기존 버튼 안내를 유지합니다.
      }
    }
    void loadCachedCart();
    return () => {
      cancelled = true;
    };
  }, [applyCart, connStatus, loaded, loading, mcpCfg]);

  const loadCart = useCallback(async (refresh = false, silent = false) => {
    if (connStatus !== "connected") {
      setError("MCP 연결 후 장바구니 목록을 불러올 수 있습니다. 먼저 MCP를 연결해주세요.");
      setItems([]);
      setLoaded(false);
      return;
    }
    if (!silent) {
      setLoading(true);
    }
    setError(null);
    try {
      const response = await fetchCart(mcpCfg, PROVIDER, refresh);
      if (!response.success) {
        if (refresh) {
          setItems([]);
          setSelectedKeys([]);
          setQuantities({});
          setCollectedAt(null);
        }
        setMessage(null);
        setLoaded(false);
        setError(
          response.message ||
            (refresh
              ? "장바구니 목록을 다시 불러오지 못했습니다. 다시 시도해주세요."
              : "장바구니 목록을 불러오지 못했습니다."),
        );
        return;
      }
      applyCart(response);
    } catch {
      if (refresh) {
        setItems([]);
        setSelectedKeys([]);
        setQuantities({});
        setCollectedAt(null);
      }
      setMessage(null);
      setLoaded(false);
      setError(
        refresh
          ? "장바구니 목록을 다시 불러오지 못했습니다. 다시 시도해주세요."
          : "장바구니 목록을 불러오지 못했습니다. 다시 시도해주세요.",
      );
    } finally {
      if (!silent) {
        setLoading(false);
      }
    }
  }, [applyCart, connStatus, mcpCfg]);

  const reloadAfterMutation = useCallback(async (fallbackMessage: string) => {
    try {
      await loadCart(true, true);
    } catch {
      setMessage(fallbackMessage);
    }
  }, [loadCart]);

  const handleQuantityChange = useCallback(async (item: CartItemSummary) => {
    const key = itemKey(item);
    const quantity = Math.max(1, Number(quantities[key] || item.quantity));
    setMutating(`quantity:${key}`);
    setError(null);
    try {
      const response = await updateCartQuantity(mcpCfg, {
        provider: PROVIDER,
        quantity,
        ...itemIdentity(item),
      });
      if (!response.success) {
        setError(response.message || "수량을 변경하지 못했습니다.");
        return;
      }
      setMessage(response.message || "수량을 변경했습니다.");
      await reloadAfterMutation(response.message || "수량을 변경했습니다.");
    } catch {
      setError("수량을 변경하지 못했습니다. 다시 시도해주세요.");
    } finally {
      setMutating(null);
    }
  }, [mcpCfg, quantities, reloadAfterMutation]);

  const handleDeleteOne = useCallback(async (item: CartItemSummary) => {
    if (!window.confirm("이 상품을 장바구니에서 삭제할까요?")) {
      return;
    }
    const key = itemKey(item);
    setMutating(`delete:${key}`);
    setError(null);
    try {
      const response = await deleteCartItem(mcpCfg, {
        provider: PROVIDER,
        ...itemIdentity(item),
      });
      if (!response.success) {
        setError(response.message || "상품을 삭제하지 못했습니다.");
        return;
      }
      setMessage(response.message || "상품을 삭제했습니다.");
      await reloadAfterMutation(response.message || "상품을 삭제했습니다.");
    } catch {
      setError("상품을 삭제하지 못했습니다. 다시 시도해주세요.");
    } finally {
      setMutating(null);
    }
  }, [mcpCfg, reloadAfterMutation]);

  const handleDeleteSelected = useCallback(async () => {
    const selectedItems = items.filter((item) => selectedKeys.includes(itemKey(item)));
    if (selectedItems.length === 0) {
      return;
    }
    if (!window.confirm(`선택한 ${selectedItems.length}개 상품을 삭제할까요?`)) {
      return;
    }
    setMutating("delete-selected");
    setError(null);
    try {
      const response = await deleteCartItems(mcpCfg, {
        provider: PROVIDER,
        items: selectedItems.map(itemIdentity),
      });
      if (!response.success) {
        setError(response.message || "선택한 상품을 삭제하지 못했습니다.");
        return;
      }
      setMessage(response.message || "선택한 상품을 삭제했습니다.");
      await reloadAfterMutation(response.message || "선택한 상품을 삭제했습니다.");
    } catch {
      setError("선택한 상품을 삭제하지 못했습니다. 다시 시도해주세요.");
    } finally {
      setMutating(null);
    }
  }, [items, mcpCfg, reloadAfterMutation, selectedKeys]);

  const handleClearCart = useCallback(async () => {
    if (items.length === 0 || !window.confirm("장바구니 전체 상품을 삭제할까요?")) {
      return;
    }
    setMutating("clear");
    setError(null);
    try {
      const response = await clearCart(mcpCfg, PROVIDER);
      if (!response.success) {
        setError(response.message || "장바구니를 비우지 못했습니다.");
        return;
      }
      setMessage(response.message || "장바구니를 비웠습니다.");
      await reloadAfterMutation(response.message || "장바구니를 비웠습니다.");
    } catch {
      setError("장바구니를 비우지 못했습니다. 다시 시도해주세요.");
    } finally {
      setMutating(null);
    }
  }, [items.length, mcpCfg, reloadAfterMutation]);

  const totalQuantity = items.reduce((sum, item) => sum + item.quantity, 0);
  const selectedCount = selectedKeys.length;

  return (
    <div className="flex-1 overflow-y-auto p-5" style={{ scrollbarWidth: "none" }}>
      <div className="mb-5">
        <div>
          <h2 className="text-base font-semibold text-foreground font-mono">
            장바구니 목록
          </h2>
          <p className="font-mono text-[11px] text-muted-foreground mt-0.5">
            {loaded
              ? `상품 ${items.length}종 · 총 ${totalQuantity}개${collectedAt ? ` · ${collectedAt}` : ""}`
              : loading
                ? "장바구니 목록을 불러오는 중입니다."
                : "장바구니 목록을 준비하는 중입니다."}
          </p>
        </div>
        {connStatus === "connected" && (
          <button
            onClick={() => void loadCart(true)}
            disabled={loading || connStatus !== "connected"}
            className="mt-4 bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground transition-colors hover:bg-blue-600 disabled:opacity-40"
          >
            {loading ? "불러오는 중..." : loaded ? "다시 불러오기" : "장바구니 목록 불러오기"}
          </button>
        )}
      </div>

      {connStatus !== "connected" && (
        <div className="mb-4 border border-border bg-secondary px-4 py-3 font-mono text-[11px] text-muted-foreground">
          MCP 연결 후 장바구니 목록을 불러올 수 있습니다. 먼저 MCP를 연결해주세요.
        </div>
      )}

      {!loaded && connStatus === "connected" && !error && (
        <div className="mb-4 border border-border bg-secondary px-4 py-5 font-mono text-[11px] text-muted-foreground">
          장바구니 목록 불러오기 버튼을 누르면 현재 장바구니를 조회합니다.
        </div>
      )}

      {error && (
        <div className="mb-4 border border-red-200 bg-red-50 px-4 py-3 font-mono text-[11px] text-red-600">
          {error}
        </div>
      )}

      {!error && message && (
        <div className="mb-4 border border-blue-200 bg-blue-50 px-4 py-3 font-mono text-[11px] text-blue-700">
          {message.split("\n")[0]}
        </div>
      )}

      {loaded && items.length === 0 && !loading && !error && (
        <div className="border border-border bg-secondary px-4 py-8 text-center font-mono text-[11px] text-muted-foreground">
          장바구니가 비어 있습니다.
        </div>
      )}

      {loaded && items.length > 0 && (
        <div className="mb-3 flex flex-wrap items-center gap-2 border border-border bg-card px-4 py-3">
          <label className="flex items-center gap-2 font-mono text-[11px] text-muted-foreground">
            <input
              type="checkbox"
              checked={selectedCount === items.length}
              onChange={(event) => {
                setSelectedKeys(event.target.checked ? items.map(itemKey) : []);
              }}
            />
            전체 선택
          </label>
          <button
            onClick={() => void handleDeleteSelected()}
            disabled={selectedCount === 0 || mutating !== null}
            className="border border-border px-3 py-1.5 text-xs text-foreground transition-colors hover:border-primary disabled:opacity-40"
          >
            {mutating === "delete-selected" ? "삭제 중..." : `선택 삭제${selectedCount ? ` (${selectedCount})` : ""}`}
          </button>
          <button
            onClick={() => void handleClearCart()}
            disabled={items.length === 0 || mutating !== null}
            className="border border-red-200 px-3 py-1.5 text-xs text-red-600 transition-colors hover:bg-red-50 disabled:opacity-40"
          >
            {mutating === "clear" ? "삭제 중..." : "전체 삭제"}
          </button>
        </div>
      )}

      <div className="flex flex-col gap-3">
        {items.map((item) => (
          <article key={itemKey(item)} className="border border-border bg-card">
            <div className="grid gap-3 px-4 py-4 lg:grid-cols-[32px_1fr_260px] lg:items-center">
              <div>
                <input
                  type="checkbox"
                  checked={selectedKeys.includes(itemKey(item))}
                  onChange={(event) => {
                    const key = itemKey(item);
                    setSelectedKeys((prev) =>
                      event.target.checked
                        ? [...prev, key]
                        : prev.filter((value) => value !== key),
                    );
                  }}
                  aria-label={`${item.product_name} 선택`}
                />
              </div>
              <div>
                <div className="font-mono text-[11px] text-muted-foreground">
                  {item.index}번 상품
                </div>
                <h3 className="mt-1 text-sm font-medium leading-6 text-foreground">
                  {item.product_name}
                </h3>
                {item.option_text && (
                  <div className="mt-1 text-xs text-muted-foreground">
                    {item.option_text}
                  </div>
                )}
                {item.delivery_text && (
                  <div className="mt-2 font-mono text-[11px] text-primary">
                    {item.delivery_text}
                  </div>
                )}
              </div>
              <div className="flex flex-col gap-2 lg:items-end lg:text-right">
                <div className="font-mono text-[11px] text-muted-foreground">
                  수량 {item.quantity}개
                </div>
                <div className="mt-1 font-mono text-sm text-foreground">
                  {item.total_price || item.unit_price || "-"}
                </div>
                {item.unit_price && item.total_price && item.unit_price !== item.total_price && (
                  <div className="mt-1 font-mono text-[11px] text-muted-foreground">
                    개당 {item.unit_price}
                  </div>
                )}
                <div className="mt-2 flex flex-wrap gap-2 lg:justify-end">
                  <input
                    type="number"
                    min={1}
                    value={quantities[itemKey(item)] ?? item.quantity}
                    onChange={(event) => {
                      const value = Math.max(1, Number(event.target.value || 1));
                      setQuantities((prev) => ({
                        ...prev,
                        [itemKey(item)]: value,
                      }));
                    }}
                    className="w-20 border border-border bg-background px-2 py-1.5 font-mono text-xs text-foreground"
                    aria-label={`${item.product_name} 수량`}
                  />
                  <button
                    onClick={() => void handleQuantityChange(item)}
                    disabled={mutating !== null}
                    className="border border-border px-3 py-1.5 text-xs text-foreground transition-colors hover:border-primary disabled:opacity-40"
                  >
                    {mutating === `quantity:${itemKey(item)}` ? "변경 중..." : "수량 변경"}
                  </button>
                  <button
                    onClick={() => void handleDeleteOne(item)}
                    disabled={mutating !== null}
                    className="border border-red-200 px-3 py-1.5 text-xs text-red-600 transition-colors hover:bg-red-50 disabled:opacity-40"
                  >
                    {mutating === `delete:${itemKey(item)}` ? "삭제 중..." : "삭제"}
                  </button>
                </div>
              </div>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}
