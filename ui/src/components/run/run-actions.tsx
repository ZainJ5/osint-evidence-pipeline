"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { CheckCircle2, Download, RotateCcw, Trash2, XCircle } from "lucide-react";
import { deleteCandidate, replayRun, toApiError, type ApiError } from "@/lib/api";
import { formatScore } from "@/lib/format";
import type { ReplayResult, RunDetail } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { ErrorPanel } from "@/components/ui/error-panel";
import { useToast } from "@/components/ui/toast";

export type ReplayState = { kind: "idle" } | { kind: "running" } | { kind: "done"; result: ReplayResult } | { kind: "error"; error: ApiError };

function Check({ ok, label }: { ok: boolean; label: string }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      {ok ? <CheckCircle2 className="size-4 text-emerald-600" aria-hidden /> : <XCircle className="size-4 text-rose-600" aria-hidden />}
      {label} {ok ? "identical" : "differs"}
    </span>
  );
}

export function ReplayBanner({ state, original, onDismiss }: { state: ReplayState; original: number | null; onDismiss: () => void }) {
  if (state.kind === "idle" || state.kind === "running") return null;
  if (state.kind === "error") {
    return (
      <ErrorPanel
        error={state.error}
        title="Replay failed"
        action={
          <Button size="sm" onClick={onDismiss}>
            Dismiss
          </Button>
        }
      />
    );
  }
  const { result } = state;
  const ok = result.evidence_identical && result.score_identical;
  return (
    <div
      role="status"
      className={`flex flex-wrap items-center gap-x-5 gap-y-2 rounded-lg border px-4 py-3 text-sm ${ok ? "border-emerald-200 bg-emerald-50 text-emerald-950" : "border-rose-200 bg-rose-50 text-rose-950"}`}
    >
      <span className="font-semibold">{ok ? "Reproduced offline from stored snapshots:" : "Replay mismatch:"}</span>
      <Check ok={result.evidence_identical} label="evidence" />
      <Check ok={result.score_identical} label="score" />
      <span className="text-slate-600 tabular-nums">
        Replayed score {formatScore(result.report.total)}
        {original !== null && ` (original ${formatScore(original)})`}
      </span>
      <button type="button" onClick={onDismiss} className="ml-auto text-xs font-medium text-slate-600 hover:underline">
        Dismiss
      </button>
    </div>
  );
}

function download(detail: RunDetail) {
  const blob = new Blob([JSON.stringify(detail, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `run-${detail.run.id}.json`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

interface RunActionsProps {
  detail: RunDetail;
  replay: ReplayState;
  onReplay: (state: ReplayState) => void;
}

export function RunActions({ detail, replay, onReplay }: RunActionsProps) {
  const router = useRouter();
  const toast = useToast();
  const [confirming, setConfirming] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<ApiError | null>(null);
  const running = detail.run.status === "running";

  async function runReplay() {
    onReplay({ kind: "running" });
    try {
      onReplay({ kind: "done", result: await replayRun(detail.run.id) });
    } catch (error) {
      onReplay({ kind: "error", error: toApiError(error) });
    }
  }

  async function remove() {
    setDeleting(true);
    setDeleteError(null);
    try {
      await deleteCandidate(detail.candidate.id);
      toast.show({ tone: "success", title: "Candidate data deleted", description: `${detail.candidate.name ?? "The candidate"}'s runs, snapshots and evidence were removed.` });
      router.push("/");
    } catch (error) {
      setDeleteError(toApiError(error));
      setDeleting(false);
    }
  }

  return (
    <>
      <Button onClick={() => void runReplay()} loading={replay.kind === "running"} disabled={running || !detail.report} title="Recompute offline from stored snapshots">
        {replay.kind !== "running" && <RotateCcw className="size-4" aria-hidden />}
        Replay
      </Button>
      <Button onClick={() => download(detail)}>
        <Download className="size-4" aria-hidden />
        Export JSON
      </Button>
      <Button variant="ghost" className="text-rose-700 hover:bg-rose-50 hover:text-rose-800" onClick={() => setConfirming(true)}>
        <Trash2 className="size-4" aria-hidden />
        Delete candidate data
      </Button>
      <Dialog
        open={confirming}
        onClose={() => !deleting && setConfirming(false)}
        title="Delete candidate data?"
        description="This permanently removes the candidate, all of their runs, raw snapshots, evidence and verdicts. It cannot be undone."
        footer={
          <>
            <Button onClick={() => setConfirming(false)} disabled={deleting}>
              Cancel
            </Button>
            <Button variant="danger" onClick={() => void remove()} loading={deleting}>
              Delete permanently
            </Button>
          </>
        }
      >
        <p className="text-sm text-slate-700">
          Candidate: <span className="font-medium">{detail.candidate.name ?? "Unnamed"}</span>
          <span className="block font-mono text-xs text-slate-500">{detail.candidate.id}</span>
        </p>
        {deleteError && <ErrorPanel error={deleteError} title="Deletion failed" className="mt-3" />}
      </Dialog>
    </>
  );
}
