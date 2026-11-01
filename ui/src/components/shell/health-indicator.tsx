"use client";

import { useEffect, useState } from "react";
import { getHealth, toApiError, type ApiError } from "@/lib/api";
import type { Health } from "@/lib/types";
import { Tooltip } from "@/components/ui/tooltip";
import { cn } from "@/lib/cn";

type State = { kind: "loading" } | { kind: "ok"; health: Health } | { kind: "down"; error: ApiError };

export function HealthIndicator() {
  const [state, setState] = useState<State>({ kind: "loading" });

  useEffect(() => {
    let active = true;
    async function check() {
      try {
        const health = await getHealth();
        if (active) setState({ kind: "ok", health });
      } catch (error) {
        if (active) setState({ kind: "down", error: toApiError(error) });
      }
    }
    void check();
    const timer = setInterval(check, 30_000);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, []);

  const ok = state.kind === "ok" && state.health.status === "ok";
  const label = state.kind === "loading" ? "Checking backend" : ok ? "Backend online" : "Backend unreachable";
  const detail =
    state.kind === "ok"
      ? `Storage: ${state.health.storage} · Claim extractor: ${state.health.extractor}`
      : state.kind === "down"
        ? `${state.error.code}: ${state.error.message}`
        : "Contacting GET /health";

  return (
    <Tooltip content={detail} side="bottom" align="end">
      <span
        tabIndex={0}
        role="status"
        aria-label={`${label}. ${detail}`}
        className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-medium text-slate-700"
      >
        <span
          aria-hidden
          className={cn(
            "size-2 rounded-full",
            state.kind === "loading" ? "animate-pulse bg-slate-300" : ok ? "bg-emerald-500" : "bg-rose-500",
          )}
        />
        {label}
        {state.kind === "ok" && (
          <span className="hidden text-slate-500 lg:inline">
            · {state.health.storage} · {state.health.extractor}
          </span>
        )}
      </span>
    </Tooltip>
  );
}
