import type { ReactNode } from "react";
import { AlertTriangle } from "lucide-react";
import type { ApiError } from "@/lib/api";
import { cn } from "@/lib/cn";

interface ErrorPanelProps {
  error: ApiError;
  title?: string;
  action?: ReactNode;
  className?: string;
}

export function ErrorPanel({ error, title = "Something went wrong", action, className }: ErrorPanelProps) {
  return (
    <div role="alert" className={cn("flex items-start gap-3 rounded-lg border border-rose-200 bg-rose-50 p-4", className)}>
      <AlertTriangle className="mt-0.5 size-5 shrink-0 text-rose-600" aria-hidden />
      <div className="min-w-0 flex-1">
        <p className="text-sm font-semibold text-rose-900">{title}</p>
        <p className="mt-1 text-sm text-rose-800">{error.message}</p>
        <p className="mt-1 font-mono text-xs text-rose-700">
          {error.code}
          {error.status > 0 && ` · HTTP ${error.status}`}
        </p>
        {action && <div className="mt-3">{action}</div>}
      </div>
    </div>
  );
}
