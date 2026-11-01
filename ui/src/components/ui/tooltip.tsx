"use client";

import { useId, type ReactNode } from "react";
import { cn } from "@/lib/cn";

interface TooltipProps {
  content: ReactNode;
  children: ReactNode;
  side?: "top" | "bottom";
  align?: "center" | "end";
  className?: string;
}

export function Tooltip({ content, children, side = "top", align = "center", className }: TooltipProps) {
  const id = useId();
  return (
    <span className={cn("group/tooltip relative inline-flex", className)} aria-describedby={id}>
      {children}
      <span
        role="tooltip"
        id={id}
        className={cn(
          "pointer-events-none invisible absolute z-30 w-max max-w-72 rounded-md bg-slate-900 px-2.5 py-1.5 text-xs leading-snug font-normal text-white normal-case opacity-0 shadow-lg transition-opacity group-focus-within/tooltip:visible group-focus-within/tooltip:opacity-100 group-hover/tooltip:visible group-hover/tooltip:opacity-100",
          side === "top" ? "bottom-full mb-2" : "top-full mt-2",
          align === "center" ? "left-1/2 -translate-x-1/2" : "right-0",
        )}
      >
        {content}
      </span>
    </span>
  );
}
