"use client";

import { createContext, useContext } from "react";
import type { EvidenceNode, RunDetail, Snapshot } from "@/lib/types";

export interface RunContextValue {
  detail: RunDetail;
  nodeById: Map<string, EvidenceNode>;
  snapshotById: Map<string, Snapshot>;
  openSnapshot: (snapshotId: string) => void;
}

export const RunContext = createContext<RunContextValue | null>(null);

export function useRunContext(): RunContextValue {
  const ctx = useContext(RunContext);
  if (!ctx) throw new Error("useRunContext must be used inside RunContext");
  return ctx;
}
