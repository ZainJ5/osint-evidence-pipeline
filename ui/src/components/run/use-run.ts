"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { getRun, toApiError, type ApiError } from "@/lib/api";
import type { RunDetail } from "@/lib/types";

const POLL_MS = 1500;

export type RunState =
  | { kind: "loading" }
  | { kind: "ready"; detail: RunDetail; pollError: ApiError | null }
  | { kind: "error"; error: ApiError };

export function useRun(runId: string): { state: RunState; reload: () => void } {
  const [state, setState] = useState<RunState>({ kind: "loading" });
  const [nonce, setNonce] = useState(0);
  const hasDetail = useRef(false);

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;

    async function load() {
      try {
        const detail = await getRun(runId);
        if (cancelled) return;
        hasDetail.current = true;
        setState({ kind: "ready", detail, pollError: null });
        if (detail.run.status === "running") timer = setTimeout(load, POLL_MS);
      } catch (error) {
        if (cancelled) return;
        const apiError = toApiError(error);
        if (hasDetail.current && !apiError.isNotFound) {
          setState((prev) => (prev.kind === "ready" ? { ...prev, pollError: apiError } : { kind: "error", error: apiError }));
          timer = setTimeout(load, POLL_MS * 2);
        } else {
          setState({ kind: "error", error: apiError });
        }
      }
    }

    void load();
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [runId, nonce]);

  const reload = useCallback(() => {
    hasDetail.current = false;
    setState({ kind: "loading" });
    setNonce((n) => n + 1);
  }, []);

  return { state, reload };
}
