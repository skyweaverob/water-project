import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

export function EmptyState({
  message,
  action,
  className,
}: {
  message: string;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("flex flex-col items-center justify-center text-center py-7", className)}>
      <p className="text-body-lg text-ink-muted">{message}</p>
      {action ? <div className="mt-2">{action}</div> : null}
    </div>
  );
}
