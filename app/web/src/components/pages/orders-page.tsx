"use client";

import Image from "next/image";
import { useCallback, useEffect, useState } from "react";
import { useApp } from "@/context/app-context";
import {
  fetchDeliveryTracking,
  fetchCachedOrders,
  fetchOrders,
  type DeliveryTrackingResponse,
  type OrderGroupSummary,
} from "@/lib/agent";
import { cn } from "@/lib/utils";

const PAGE_SIZE = 10;
const PROVIDER = "coupang";

export function OrdersPage() {
  const { mcpCfg, connStatus } = useApp();
  const [groups, setGroups] = useState<OrderGroupSummary[]>([]);
  const [years, setYears] = useState<string[]>([]);
  const [collectedAt, setCollectedAt] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [activeTab, setActiveTab] = useState("전체");
  const [page, setPage] = useState(1);
  const [selectedGroup, setSelectedGroup] = useState<OrderGroupSummary | null>(null);
  const [tracking, setTracking] = useState<DeliveryTrackingResponse | null>(null);
  const [trackingLoading, setTrackingLoading] = useState(false);
  const [trackingError, setTrackingError] = useState<string | null>(null);

  const applyOrders = useCallback((response: Awaited<ReturnType<typeof fetchOrders>>) => {
    setGroups(response.groups);
    setYears(response.years);
    setCollectedAt(response.collected_at);
    setLoaded(true);
  }, []);

  useEffect(() => {
    let cancelled = false;
    async function loadCachedOrders() {
      if (connStatus !== "connected" || loaded || loading) {
        return;
      }
      try {
        const response = await fetchCachedOrders(mcpCfg);
        if (cancelled || response.groups.length === 0) {
          return;
        }
        applyOrders(response);
      } catch {
        // 저장된 주문이 없거나 읽지 못하면 기존 버튼 안내를 유지합니다.
      }
    }
    void loadCachedOrders();
    return () => {
      cancelled = true;
    };
  }, [applyOrders, connStatus, loaded, loading, mcpCfg]);

  const loadOrders = useCallback(async (refresh = false, silent = false) => {
    if (connStatus !== "connected") {
      setError("MCP 연결 후 주문 목록을 불러올 수 있습니다. 먼저 MCP를 연결해주세요.");
      return;
    }
    if (!silent) {
      setLoading(true);
    }
    setError(null);
    try {
      const response = await fetchOrders(mcpCfg, refresh);
      applyOrders(response);
    } catch (fetchError) {
      void fetchError;
      if (refresh) {
        setGroups([]);
        setYears([]);
        setCollectedAt(null);
      }
      setLoaded(false);
      setError(
        refresh
          ? "주문 목록을 다시 불러오지 못했습니다. 다시 시도해주세요."
          : "주문 목록을 불러오지 못했습니다. 다시 시도해주세요.",
      );
    } finally {
      if (!silent) {
        setLoading(false);
      }
    }
  }, [applyOrders, connStatus, mcpCfg]);

  const openTrackingModal = useCallback(async (group: OrderGroupSummary) => {
    setSelectedGroup(group);
    setTracking(null);
    setTrackingError(null);

    if (!group.shipment_box_id) {
      setTrackingError("배송 그룹 ID가 없어 배송조회 데이터를 가져올 수 없습니다.");
      return;
    }

    setTrackingLoading(true);
    try {
      const response = await fetchDeliveryTracking(
        mcpCfg,
        group.order_id,
        group.shipment_box_id,
        PROVIDER,
      );
      setTracking(response);
    } catch (fetchError) {
      void fetchError;
      setTrackingError("실제 배송조회 정보를 가져오지 못했습니다.");
    } finally {
      setTrackingLoading(false);
    }
  }, [mcpCfg]);

  const tabs = ["전체", "최근 6개월", ...years];
  const sixMonthsAgo = new Date();
  sixMonthsAgo.setMonth(sixMonthsAgo.getMonth() - 6);
  const filteredGroups = groups.filter((group) => {
    if (activeTab === "전체") return true;
    if (activeTab === "최근 6개월") {
      const timestamp = group.ordered_at > 10_000_000_000
        ? Math.floor(group.ordered_at / 1000)
        : group.ordered_at;
      return timestamp * 1000 >= sixMonthsAgo.getTime();
    }
    return group.year === activeTab;
  });
  const totalPages = Math.max(1, Math.ceil(filteredGroups.length / PAGE_SIZE));
  const currentPage = Math.min(page, totalPages);
  const pagedGroups = filteredGroups.slice(
    (currentPage - 1) * PAGE_SIZE,
    currentPage * PAGE_SIZE,
  );

  return (
    <div className="flex-1 overflow-y-auto p-5" style={{ scrollbarWidth: "none" }}>
      <div className="mb-5">
        <div>
          <h2 className="text-base font-semibold text-foreground font-mono">
            주문 목록
          </h2>
          <p className="font-mono text-[11px] text-muted-foreground mt-0.5">
            {loaded
              ? `총 ${filteredGroups.length}개 주문 묶음${collectedAt ? ` · 마지막 업데이트 ${collectedAt}` : ""}`
              : loading
                ? "주문 목록을 불러오는 중입니다."
                : "주문 목록을 준비하는 중입니다."}
          </p>
        </div>
        {connStatus === "connected" && (
          <button
            onClick={() => void loadOrders(loaded)}
            disabled={loading || connStatus !== "connected"}
            className="mt-4 bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground transition-colors hover:bg-blue-600 disabled:opacity-40"
          >
            {loading ? "불러오는 중..." : loaded ? "다시 불러오기" : "주문 목록 불러오기"}
          </button>
        )}
      </div>

      {connStatus !== "connected" && (
        <div className="mb-4 border border-border bg-secondary px-4 py-3 font-mono text-[11px] text-muted-foreground">
          MCP 연결 후 주문 목록을 불러올 수 있습니다. 먼저 MCP를 연결해주세요.
        </div>
      )}

      {error && (
        <div className="mb-4 border border-red-200 bg-red-50 px-4 py-3 font-mono text-[11px] text-red-600">
          {error}
        </div>
      )}

      {!loaded && connStatus === "connected" && !error && (
        <div className="mb-4 border border-border bg-secondary px-4 py-5 font-mono text-[11px] text-muted-foreground">
          주문 목록 불러오기 버튼을 누르면 저장된 주문부터 조회합니다.
        </div>
      )}

      {loaded && (
        <div className="mb-4 flex flex-wrap gap-2">
          {tabs.map((tab) => (
            <button
              key={tab}
              onClick={() => {
                setActiveTab(tab);
                setPage(1);
              }}
              className={cn(
                "px-3 py-1.5 text-xs font-mono border transition-colors",
                activeTab === tab
                  ? "border-primary bg-primary text-primary-foreground"
                  : "border-border text-muted-foreground hover:text-foreground hover:border-primary",
              )}
            >
              {tab}
            </button>
          ))}
        </div>
      )}

      <div className="flex flex-col gap-4">
        {loaded && pagedGroups.map((group) => (
          <div key={group.id} className="border border-border bg-card">
            <div className="flex items-center justify-between border-b border-border px-4 py-3">
              <div>
                <div className="font-mono text-[11px] text-muted-foreground">
                  {group.date} 주문
                </div>
                <div className="mt-1 flex items-center gap-2">
                  <span className="border border-border px-2 py-0.5 font-mono text-[11px] text-foreground">
                    {group.display_status || "상태 확인 필요"}
                  </span>
                  {group.delivery_message && (
                    <span className="font-mono text-[11px] text-primary">
                      {group.delivery_message}
                    </span>
                  )}
                </div>
              </div>
              <div className="text-right">
                <div className="font-mono text-[11px] text-muted-foreground">
                  주문번호
                </div>
                <div className="font-mono text-[12px] text-primary">{group.order_id}</div>
              </div>
            </div>

            <div className="grid lg:grid-cols-[1fr_220px]">
              <div className="divide-y divide-border">
                {group.items.map((item) => (
                  <div
                    key={`${group.id}-${item.product}`}
                    className="grid gap-4 px-4 py-4 sm:grid-cols-[88px_1fr]"
                  >
                    <div className="overflow-hidden border border-border bg-secondary/30 aspect-square">
                      {item.image ? (
                        <Image
                          src={item.image}
                          alt={item.product}
                          width={120}
                          height={120}
                          unoptimized
                          className="h-full w-full object-cover"
                        />
                      ) : (
                        <div className="flex h-full w-full items-center justify-center font-mono text-[10px] text-muted-foreground">
                          NO IMAGE
                        </div>
                      )}
                    </div>
                    <div>
                      <div className="text-sm text-foreground leading-6">
                        {item.link ? (
                          <a
                            href={item.link}
                            target="_blank"
                            rel="noreferrer"
                            className="hover:text-primary hover:underline transition-colors"
                          >
                            {item.product}
                          </a>
                        ) : (
                          item.product
                        )}
                      </div>
                      <div className="mt-2 font-mono text-[12px] text-muted-foreground">
                        {item.price} · {item.quantity}개
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              <div className="border-t border-border px-4 py-4 lg:border-l lg:border-t-0">
                <div className="flex flex-col gap-2">
                  {group.has_track_action && (
                    <button
                      onClick={() => void openTrackingModal(group)}
                      className="border border-primary px-3 py-2 text-sm text-primary transition-colors hover:bg-blue-50"
                    >
                      배송 조회
                    </button>
                  )}
                  {group.has_exchange_return_action && (
                    <button className="border border-border px-3 py-2 text-sm text-foreground transition-colors hover:border-primary">
                      교환, 반품 신청
                    </button>
                  )}
                </div>
              </div>
            </div>
          </div>
        ))}
        {loaded && filteredGroups.length === 0 && !loading && (
          <div className="px-4 py-6 font-mono text-[11px] text-muted-foreground">
            표시할 주문이 없습니다.
          </div>
        )}
      </div>

      {loaded && filteredGroups.length > 0 && (
        <div className="mt-4 flex items-center justify-between">
          <div className="font-mono text-[11px] text-muted-foreground">
            페이지 {currentPage} / {totalPages}
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => setPage((value) => Math.max(1, value - 1))}
              disabled={currentPage === 1}
              className="border border-border px-3 py-1.5 text-xs font-mono text-muted-foreground hover:text-foreground hover:border-primary disabled:opacity-40"
            >
              이전
            </button>
            <button
              onClick={() => setPage((value) => Math.min(totalPages, value + 1))}
              disabled={currentPage === totalPages}
              className="border border-border px-3 py-1.5 text-xs font-mono text-muted-foreground hover:text-foreground hover:border-primary disabled:opacity-40"
            >
              다음
            </button>
          </div>
        </div>
      )}

      {selectedGroup && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
          onClick={(event) => {
            if (event.target === event.currentTarget) {
              setSelectedGroup(null);
              setTracking(null);
              setTrackingError(null);
            }
          }}
        >
          <div className="w-full max-w-xl border border-border bg-card shadow-2xl">
            <div className="flex items-center justify-between border-b border-border px-5 py-4">
              <div>
                <div className="font-mono text-[11px] text-muted-foreground">
                  배송 조회
                </div>
                <div className="mt-1 font-mono text-sm text-foreground">
                  주문번호 {selectedGroup.order_id}
                </div>
              </div>
              <button
                onClick={() => {
                  setSelectedGroup(null);
                  setTracking(null);
                  setTrackingError(null);
                }}
                className="font-mono text-xs text-muted-foreground hover:text-foreground"
              >
                닫기
              </button>
            </div>
            <div className="grid gap-4 px-5 py-4 md:grid-cols-2">
              <div className="border border-border bg-secondary/40 px-4 py-3">
                <div className="font-mono text-[10px] text-muted-foreground">배송 그룹 ID</div>
                <div className="mt-1 font-mono text-sm text-foreground">
                  {selectedGroup.shipment_box_id || "-"}
                </div>
              </div>
              <div className="border border-border bg-secondary/40 px-4 py-3">
                <div className="font-mono text-[10px] text-muted-foreground">화면 표시 상태</div>
                <div className="mt-1 font-mono text-sm text-foreground">{selectedGroup.display_status || "-"}</div>
              </div>
              <div className="border border-border bg-secondary/40 px-4 py-3">
                <div className="font-mono text-[10px] text-muted-foreground">배송 상태</div>
                <div className="mt-1 font-mono text-sm text-foreground">{selectedGroup.display_status || "상태 확인 필요"}</div>
              </div>
              <div className="border border-border bg-secondary/40 px-4 py-3">
                <div className="font-mono text-[10px] text-muted-foreground">송장번호</div>
                <div className="mt-1 font-mono text-sm text-foreground">
                  {tracking?.tracking_number || tracking?.invoice_number || selectedGroup.invoice_number || "없음"}
                </div>
              </div>
              <div className="border border-border bg-secondary/40 px-4 py-3">
                <div className="font-mono text-[10px] text-muted-foreground">도착 메시지</div>
                <div className="mt-1 font-mono text-sm text-foreground">
                  {tracking?.summary || selectedGroup.delivery_message || "없음"}
                </div>
              </div>
              <div className="border border-border bg-secondary/40 px-4 py-3">
                <div className="font-mono text-[10px] text-muted-foreground">택배사</div>
                <div className="mt-1 font-mono text-sm text-foreground">{tracking?.courier_name || "확인 중"}</div>
              </div>
            </div>
            <div className="border-t border-border px-5 py-4">
              <div className="mb-3 flex items-center justify-between">
                <div className="font-mono text-[10px] text-muted-foreground">실제 배송조회 내역</div>
                {tracking?.collected_at && (
                  <div className="font-mono text-[10px] text-muted-foreground">
                    조회 시각 {tracking.collected_at}
                  </div>
                )}
              </div>
              {trackingLoading && (
                <div className="border border-border bg-secondary/40 px-4 py-4 font-mono text-[11px] text-muted-foreground">
                  쿠팡 배송조회 화면을 열어 실제 추적 정보를 읽는 중입니다.
                </div>
              )}
              {trackingError && (
                <div className="border border-red-200 bg-red-50 px-4 py-4 font-mono text-[11px] text-red-600">
                  {trackingError}
                </div>
              )}
              {!trackingLoading && !trackingError && tracking && tracking.events.length > 0 && (
                <div className="flex flex-col gap-2">
                  {tracking.events.map((event, index) => (
                    <div
                      key={`${tracking.shipment_box_id}-${event.time || "no-time"}-${index}`}
                      className="border border-border bg-secondary/30 px-4 py-3"
                    >
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-mono text-[11px] text-primary">{event.status}</span>
                        {event.time && (
                          <span className="font-mono text-[10px] text-muted-foreground">
                            {event.time}
                          </span>
                        )}
                        {event.location && (
                          <span className="font-mono text-[10px] text-muted-foreground">
                            {event.location}
                          </span>
                        )}
                      </div>
                      {event.description && (
                        <div className="mt-1 font-mono text-[11px] text-foreground">
                          {event.description}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
              {!trackingLoading && !trackingError && tracking && tracking.events.length === 0 && tracking.raw_lines.length === 0 && (
                <div className="border border-border bg-secondary/30 px-4 py-4 font-mono text-[11px] text-muted-foreground">
                  쿠팡 배송조회 화면에서 추가 추적 정보를 읽지 못했습니다.
                </div>
              )}
              {!trackingLoading && !trackingError && tracking && tracking.raw_lines.length > 0 && (
                <div className="mt-3 flex flex-col gap-2">
                  {tracking.raw_lines.slice(0, 20).map((line, index) => (
                    <div
                      key={`${tracking.shipment_box_id}-line-${index}`}
                      className="font-mono text-[11px] text-muted-foreground"
                    >
                      {line}
                    </div>
                  ))}
                </div>
              )}
            </div>
            <div className="border-t border-border px-5 py-4">
              <div className="mb-3 font-mono text-[10px] text-muted-foreground">주문 상품</div>
              <div className="flex flex-col gap-2">
                {selectedGroup.items.map((item) => (
                  <div
                    key={`${selectedGroup.id}-${item.product}`}
                    className="grid gap-3 border border-border px-4 py-3 sm:grid-cols-[72px_1fr]"
                  >
                    <div className="overflow-hidden border border-border bg-secondary/30 aspect-square">
                      {item.image ? (
                        <Image
                          src={item.image}
                          alt={item.product}
                          width={120}
                          height={120}
                          unoptimized
                          className="h-full w-full object-cover"
                        />
                      ) : (
                        <div className="flex h-full w-full items-center justify-center font-mono text-[10px] text-muted-foreground">
                          NO IMAGE
                        </div>
                      )}
                    </div>
                    <div>
                      <div className="text-sm text-foreground leading-6">
                        {item.link ? (
                          <a
                            href={item.link}
                            target="_blank"
                            rel="noreferrer"
                            className="hover:text-primary hover:underline transition-colors"
                          >
                            {item.product}
                          </a>
                        ) : (
                          item.product
                        )}
                      </div>
                      <div className="mt-1 font-mono text-[11px] text-muted-foreground">
                        {item.price} · {item.quantity}개
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
