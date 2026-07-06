import {
  CheckCircle2,
  Circle,
  Loader2,
  XCircle,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { TaskStatus } from "@/data/taskHistory.mock";
type OrderStatus =
  | "배송완료"
  | "배송중"
  | "주문확인"
  | "취소"
  | "상품준비중"
  | "주문접수"
  | "배송조회불가";

export function TaskIcon({
  status,
}: {
  status: TaskStatus | "ok" | "err";
}) {
  if (status === "success" || status === "ok") {
    return (
      <CheckCircle2 size={12} className="text-primary shrink-0" />
    );
  }
  if (status === "error" || status === "err") {
    return <XCircle size={12} className="text-red-500 shrink-0" />;
  }
  if (status === "running") {
    return (
      <Loader2 size={12} className="text-primary animate-spin shrink-0" />
    );
  }
  return <Circle size={12} className="text-muted-foreground shrink-0" />;
}

export function OrderBadge({ status }: { status: OrderStatus }) {
  const styles: Record<OrderStatus, string> = {
    배송완료:
      "bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300",
    배송중:
      "bg-cyan-100 text-cyan-700 dark:bg-cyan-900/40 dark:text-cyan-300",
    주문확인:
      "bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400",
    상품준비중:
      "bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300",
    주문접수:
      "bg-violet-100 text-violet-700 dark:bg-violet-900/40 dark:text-violet-300",
    배송조회불가:
      "bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-300",
    취소: "bg-red-100 text-red-600 dark:bg-red-900/40 dark:text-red-300",
  };

  return (
    <span className={cn("font-mono text-[11px] px-2 py-0.5", styles[status])}>
      {status}
    </span>
  );
}
