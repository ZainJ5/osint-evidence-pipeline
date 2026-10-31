"use client";

import { useEffect, useState } from "react";
import { ShieldAlert, ShieldCheck } from "lucide-react";
import { getSnapshotRaw, toApiError, type ApiError } from "@/lib/api";
import { sourceLabel } from "@/lib/domain";
import { formatBytes, formatDateTime } from "@/lib/format";
import type { RawSnapshot, Snapshot } from "@/lib/types";
import { CopyButton } from "@/components/ui/copy-button";
import { Dialog } from "@/components/ui/dialog";
import { ErrorPanel } from "@/components/ui/error-panel";
import { Skeleton } from "@/components/ui/skeleton";
import { JsonViewer } from "./json-viewer";

type State = { kind: "loading" } | { kind: "ready"; raw: RawSnapshot } | { kind: "error"; error: ApiError };

function SnapshotBody({ snapshotId }: { snapshotId: string }) {
  const [state, setState] = useState<State>({ kind: "loading" });

  useEffect(() => {
    let active = true;
    getSnapshotRaw(snapshotId)
      .then((raw) => active && setState({ kind: "ready", raw }))
      .catch((error: unknown) => active && setState({ kind: "error", error: toApiError(error) }));
    return () => {
      active = false;
    };
  }, [snapshotId]);

  if (state.kind === "loading") {
    return (
      <div className="space-y-3" role="status" aria-label="Loading snapshot">
        <Skeleton className="h-12 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }
  if (state.kind === "error") {
    return (
      <ErrorPanel
        error={state.error}
        title={state.error.code === "HASH_MISMATCH" ? "Integrity check failed: stored bytes do not match the SHA-256" : "Snapshot could not be loaded"}
      />
    );
  }
  const { raw } = state;
  return (
    <div className="space-y-4">
      {raw.verified ? (
        <p className="flex items-center gap-2 rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm font-medium text-emerald-900">
          <ShieldCheck className="size-4 text-emerald-600" aria-hidden />
          Integrity verified (SHA-256 match)
        </p>
      ) : (
        <p className="flex items-center gap-2 rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-sm font-medium text-rose-900">
          <ShieldAlert className="size-4 text-rose-600" aria-hidden />
          Integrity not verified
        </p>
      )}
      <JsonViewer value={raw.payload} />
    </div>
  );
}

function Meta({ snapshot }: { snapshot: Snapshot }) {
  return (
    <dl className="mt-2 grid grid-cols-2 gap-x-6 gap-y-1 text-xs sm:grid-cols-4">
      <div>
        <dt className="text-slate-500">Source</dt>
        <dd className="font-medium text-slate-800">
          {sourceLabel(snapshot.source)} · {snapshot.handle}
        </dd>
      </div>
      <div>
        <dt className="text-slate-500">Size</dt>
        <dd className="font-medium text-slate-800">{formatBytes(snapshot.size)}</dd>
      </div>
      <div>
        <dt className="text-slate-500">Fetched</dt>
        <dd className="font-medium text-slate-800">{formatDateTime(snapshot.fetched_at)}</dd>
      </div>
      <div className="col-span-2 sm:col-span-4">
        <dt className="text-slate-500">SHA-256</dt>
        <dd className="flex items-center gap-1 font-mono break-all text-slate-800">
          {snapshot.sha256}
          <CopyButton value={snapshot.sha256} label="Copy SHA-256" />
        </dd>
      </div>
    </dl>
  );
}

export function SnapshotDrawer({ snapshot, snapshotId, onClose }: { snapshot: Snapshot | null; snapshotId: string | null; onClose: () => void }) {
  return (
    <Dialog
      open={snapshotId !== null}
      onClose={onClose}
      variant="drawer"
      title={snapshot ? <span className="font-mono text-sm">{snapshot.endpoint}</span> : "Raw snapshot"}
      description={snapshot ? <Meta snapshot={snapshot} /> : snapshotId}
    >
      {snapshotId && <SnapshotBody key={snapshotId} snapshotId={snapshotId} />}
    </Dialog>
  );
}
