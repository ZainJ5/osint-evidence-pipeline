import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

export type Tone = "neutral" | "accent" | "supported" | "partial" | "unsupported" | "unlinked" | "running";

const TONES: Record<Tone, string> = {
  neutral: "bg-slate-100 text-slate-700 ring-slate-200",
  accent: "bg-indigo-50 text-indigo-700 ring-indigo-200",
  supported: "bg-emerald-50 text-emerald-800 ring-emerald-200",
  partial: "bg-amber-50 text-amber-800 ring-amber-200",
  unsupported: "bg-rose-50 text-rose-800 ring-rose-200",
  unlinked: "bg-slate-100 text-slate-600 ring-slate-300",
  running: "bg-sky-50 text-sky-800 ring-sky-200",
};

interface BadgeProps {
  tone?: Tone;
  icon?: ReactNode;
  children: ReactNode;
  className?: string;
  title?: string;
}

export function Badge({ tone = "neutral", icon, children, className, title }: BadgeProps) {
  return (
    <span
      title={title}
      className={cn(
        "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium whitespace-nowrap ring-1 ring-inset",
        TONES[tone],
        className,
      )}
    >
      {icon}
      {children}
    </span>
  );
}
