export type TaskStatus = "idle" | "running" | "success" | "error";

export interface TaskLog {
  id: string;
  name: string;
  status: TaskStatus;
  time?: string;
}

export interface RecentExecution {
  cmd: string;
  ts: string;
  ok: boolean;
}

export const SYSTEM_STATUS = [
  { label: "MCP 서버", value: "정상", ok: true },
  { label: "쿠팡 세션", value: "활성", ok: true },
  { label: "자동화 엔진", value: "대기", ok: true },
  { label: "리뷰 큐", value: "0건", ok: true },
];

export const RECENT_EXECUTIONS: RecentExecution[] = [
  { cmd: "getOrders()", ts: "14:23:01", ok: true },
  { cmd: "login()", ts: "14:22:48", ok: true },
  { cmd: "writeReview()", ts: "13:50:12", ok: true },
  { cmd: "trackDelivery()", ts: "13:41:07", ok: false },
];

export const SESSION_INFO = {
  id: "sess_7xK2mPqR9vL",
  expiresAt: "23:59:59",
};

/** MCP 명령별 시뮬레이션 응답 */
export function getSimulatedTasks(command: string): TaskLog[] {
  const uid = () => Math.random().toString(36).slice(2, 9);

  if (command.includes("login") || command.includes("로그인")) {
    return [
      { id: uid(), name: "세션 초기화", status: "success", time: "0.2s" },
      { id: uid(), name: "크리덴셜 로드", status: "success", time: "0.1s" },
      { id: uid(), name: "쿠팡 인증 요청", status: "success", time: "1.4s" },
      { id: uid(), name: "토큰 저장", status: "success", time: "0.1s" },
    ];
  }

  if (command.includes("orders") || command.includes("주문")) {
    return [
      { id: uid(), name: "세션 검증", status: "success", time: "0.1s" },
      { id: uid(), name: "주문 API 호출", status: "success", time: "0.8s" },
      { id: uid(), name: "데이터 파싱", status: "success", time: "0.2s" },
    ];
  }

  if (command.includes("review") || command.includes("리뷰")) {
    return [
      { id: uid(), name: "세션 검증", status: "success", time: "0.1s" },
      { id: uid(), name: "리뷰 가능 상품 조회", status: "success", time: "0.6s" },
      { id: uid(), name: "리뷰 내용 생성", status: "success", time: "1.2s" },
      { id: uid(), name: "리뷰 제출", status: "success", time: "0.9s" },
    ];
  }

  return [{ id: uid(), name: "명령 처리", status: "success", time: "0.3s" }];
}

export function getSimulatedResponse(command: string): string {
  if (command.includes("login") || command.includes("로그인")) {
    return "로그인 성공했습니다.\n\n세션 ID: `sess_7xK2mPqR9vL`\n만료: 2026-06-29 23:59:59\n\n이제 주문 조회, 리뷰 작성 등 모든 기능을 사용할 수 있습니다.";
  }

  if (command.includes("orders") || command.includes("주문")) {
    return "최근 주문 5건을 불러왔습니다.\n\n**ORD-29481** — 삼성 갤럭시 버즈2 프로 / 189,000원 / 배송완료\n**ORD-29103** — 나이키 에어맥스 270 / 149,000원 / 배송중\n**ORD-28874** — 애플 에어팟 4세대 / 229,000원 / 주문확인";
  }

  if (command.includes("review") || command.includes("리뷰")) {
    return "리뷰 작성 완료했습니다.\n\n**대상 상품:** 삼성 갤럭시 버즈2 프로\n**별점:** ★★★★★ (5/5)\n**리뷰 ID:** `rev_K9pXmT3nQ`\n**포인트 적립:** +200P\n\n리뷰가 검토 후 24시간 내 공개됩니다.";
  }

  return `"${command}" 명령을 처리했습니다. 좌측 버튼으로 주요 기능을 바로 사용할 수 있습니다.`;
}
