"use client";

import { useCallback, useEffect, useState } from "react";
import { fetchMcpServers } from "@/lib/api";
import type { McpServerInfo } from "@/lib/types";

export function useMcpServers() {
  const [servers, setServers] = useState<McpServerInfo[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const res = await fetchMcpServers();
      setServers(res.servers);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "목록을 불러오지 못했습니다.");
    } finally {
      setLoaded(true);
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- initial data fetch on mount
    refresh();
  }, [refresh]);

  return { servers, error, loaded, refresh };
}
