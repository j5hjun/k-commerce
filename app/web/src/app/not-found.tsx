import Link from "next/link";

export default function NotFound() {
  return (
    <div className="flex-1 flex flex-col items-center justify-center gap-4 text-muted-foreground">
      <span className="font-mono text-4xl">404</span>
      <p className="font-mono text-sm">페이지를 찾을 수 없습니다</p>
      <Link href="/" className="font-mono text-xs text-primary hover:underline">
        ← 홈으로
      </Link>
    </div>
  );
}
