"use client";

import {
  ChevronRight,
  List,
  LogIn,
  ShoppingBag,
  Star,
} from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { TaskIcon } from "@/components/ui/shared";
import { useApp } from "@/context/app-context";
import { cn } from "@/lib/utils";
import type { TaskLog } from "@/data/taskHistory.mock";

const QUICK_ACTIONS = [
  {
    id: "login",
    label: "자동 로그인",
    desc: "쿠팡 계정 자동 인증",
    icon: <LogIn size={15} />,
    cmd: "로그인 진행해줘",
    to: null,
  },
  {
    id: "orders",
    label: "주문 목록",
    desc: "최근 주문 내역 조회",
    icon: <ShoppingBag size={15} />,
    cmd: "주문목록 가져와줘",
    to: "/orders",
  },
  {
    id: "review",
    label: "리뷰 작성",
    desc: "구매 상품 리뷰 등록",
    icon: <Star size={15} />,
    cmd: "리뷰 작성할 상품 보여줘",
    to: "/reviews",
  },
  {
    id: "cart",
    label: "장바구니 목록",
    desc: "현재 담긴 상품 조회",
    icon: <List size={15} />,
    cmd: "장바구니 목록 가져와줘",
    to: "/cart",
  },
] as const;

export function AppSidebar({
  tasks,
  running,
}: {
  tasks: TaskLog[];
  running: boolean;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const { queueCommand } = useApp();

  async function handleAction(action: (typeof QUICK_ACTIONS)[number]) {
    if (action.id === "login") {
      queueCommand("로그인 진행해줘");
      router.push("/");
      return;
    }

    const { cmd, to } = action;
    if (to) {
      router.push(to);
    } else {
      queueCommand(cmd);
      router.push("/");
    }
  }

  return (
    <aside className="w-56 lg:w-64 border-r border-border bg-card flex flex-col shrink-0">
      <div className="px-4 pt-5 pb-3">
        <span className="font-mono text-[10px] text-muted-foreground tracking-widest uppercase">
          빠른 실행
        </span>
      </div>
      <nav className="flex flex-col gap-0.5 px-2">
        {QUICK_ACTIONS.map((action) => {
          const isActive = action.to ? pathname === action.to : pathname === "/";
          return (
            <Link
              key={action.id}
              href={action.to ?? "/"}
              onClick={(event) => {
                event.preventDefault();
                void handleAction(action);
              }}
              className={cn(
                "group flex items-start gap-3 px-3 py-3 text-left border w-full transition-colors duration-150",
                "hover:bg-accent disabled:opacity-40 focus:outline-none",
                isActive && action.to
                  ? "bg-accent border-primary/40"
                  : "border-transparent hover:border-border",
                running && "pointer-events-none opacity-40",
              )}
            >
              <span
                className={cn(
                  "mt-0.5 shrink-0",
                  isActive && action.to
                    ? "text-primary"
                    : "text-muted-foreground",
                )}
              >
                {action.icon}
              </span>
              <div className="flex-1 min-w-0">
                <div
                  className={cn(
                    "text-sm font-medium leading-none mb-1",
                    isActive && action.to
                      ? "text-primary"
                      : "text-foreground",
                  )}
                >
                  {action.label}
                </div>
                <div className="text-[11px] text-muted-foreground">
                  {action.desc}
                </div>
              </div>
              <ChevronRight
                size={12}
                className={cn(
                  "mt-0.5 shrink-0 transition-colors group-hover:text-primary",
                  isActive && action.to
                    ? "text-primary"
                    : "text-muted-foreground/40",
                )}
              />
            </Link>
          );
        })}
      </nav>

      <div className="mt-auto border-t border-border">
        <div className="px-4 pt-4 pb-2">
          <span className="font-mono text-[10px] text-muted-foreground tracking-widest uppercase">
            실행 로그
          </span>
        </div>
        <div className="px-4 pb-4 flex flex-col gap-1.5 min-h-[80px]">
          {tasks.length === 0 && !running && (
            <span className="font-mono text-[11px] text-muted-foreground/50">
              대기 중...
            </span>
          )}
          {tasks.map((task) => (
            <div key={task.id} className="flex items-center gap-2">
              <TaskIcon status={task.status} />
              <span className="font-mono text-[11px] text-muted-foreground flex-1 truncate">
                {task.name}
              </span>
              {task.time && (
                <span className="font-mono text-[10px] text-muted-foreground/50">
                  {task.time}
                </span>
              )}
            </div>
          ))}
          {running && (
            <div className="flex items-center gap-2">
              <TaskIcon status="running" />
              <span className="font-mono text-[11px] text-primary">
                처리 중...
              </span>
            </div>
          )}
        </div>
      </div>
    </aside>
  );
}
