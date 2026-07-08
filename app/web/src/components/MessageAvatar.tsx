"use client";

import { BoltIcon } from "@/components/icons";

export function MessageAvatar() {
  return (
    <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-accent text-accent-ink">
      <BoltIcon className="h-4 w-4" />
    </span>
  );
}
