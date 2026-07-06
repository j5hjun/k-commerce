import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "COUPANG_MCP",
  description: "쿠팡 자동화 MCP 대시보드",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ko" className="h-full">
      <body className="min-h-full antialiased">{children}</body>
    </html>
  );
}
