export interface QuickAction {
  id: string;
  label: string;
  description: string;
  iconName: string;
  command: string;
  color: string;
  route?: string;
}

export const QUICK_ACTIONS: QuickAction[] = [
  {
    id: "login",
    label: "자동 로그인",
    description: "쿠팡 계정 자동 인증",
    iconName: "LogIn",
    command: "coupang.login()",
    color: "text-blue-400",
  },
  {
    id: "orders",
    label: "주문 목록",
    description: "최근 주문 내역 조회",
    iconName: "ShoppingBag",
    command: "coupang.getOrders()",
    color: "text-cyan-400",
    route: "/orders",
  },
  {
    id: "review",
    label: "리뷰 작성",
    description: "구매 상품 리뷰 등록",
    iconName: "Star",
    command: "coupang.writeReview()",
    color: "text-blue-300",
    route: "/reviews",
  },
  {
    id: "delivery",
    label: "배송 조회",
    description: "실시간 배송 상태 확인",
    iconName: "Package",
    command: "coupang.trackDelivery()",
    color: "text-indigo-400",
  },
];
