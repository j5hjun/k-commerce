export type OrderStatus = "배송완료" | "배송중" | "주문확인" | "취소";

export interface Order {
  id: string;
  product: string;
  price: string;
  status: OrderStatus;
  date: string;
  reviewable: boolean;
}

export const MOCK_ORDERS: Order[] = [
  {
    id: "ORD-29481",
    product: "삼성 갤럭시 버즈2 프로",
    price: "189,000원",
    status: "배송완료",
    date: "2026.06.27",
    reviewable: true,
  },
  {
    id: "ORD-29103",
    product: "나이키 에어맥스 270 런닝화",
    price: "149,000원",
    status: "배송중",
    date: "2026.06.28",
    reviewable: false,
  },
  {
    id: "ORD-28874",
    product: "애플 에어팟 4세대",
    price: "229,000원",
    status: "주문확인",
    date: "2026.06.29",
    reviewable: false,
  },
  {
    id: "ORD-28301",
    product: "다이슨 에어랩 멀티스타일러",
    price: "699,000원",
    status: "배송완료",
    date: "2026.06.20",
    reviewable: true,
  },
  {
    id: "ORD-27994",
    product: "뉴발란스 993 그레이",
    price: "219,000원",
    status: "배송완료",
    date: "2026.06.15",
    reviewable: true,
  },
];
