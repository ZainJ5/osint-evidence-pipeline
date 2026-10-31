"use client";

import Link from "next/link";
import { useCallback, useMemo, useState } from "react";
import { ArrowLeft, FileQuestion, Loader2 } from "lucide-react";
import { formatDateTime, formatDuration } from "@/lib/format";
import type { RunDetail } from "@/lib/types";
import { buttonClasses, Button } from "@/components/ui/button";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { CopyButton } from "@/components/ui/copy-button";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorPanel } from "@/components/ui/error-panel";
import { PageHeader } from "@/components/ui/page-header";
import { Skeleton } from "@/components/ui/skeleton";
import { TabPanel, Tabs, type TabItem } from "@/components/ui/tabs";
import { RunStatusBadge } from "@/components/status/status-badges";
import { ClaimsTab } from "./claims-tab";
import { EvidenceTab } from "./evidence-tab";
import { IdentityTab } from "./identity-tab";
import { OverviewTab } from "./overview-tab";
import { PipelineTimeline } from "./pipeline-timeline";
import { RequirementsTab } from "./requirements-tab";
import { RunActions, ReplayBanner, type ReplayState } from "./run-actions";
import { RunContext, type RunContextValue } from "./run-context";
import { SnapshotDrawer } from "./snapshot-drawer";
import { SnapshotsTab } from "./snapshots-tab";
import { useRun } from "./use-run";

type TabId = "overview" | "claims" | "requirements" | "identity" | "evidence" | "snapshots";

function LoadingView() {
  return (
    <div role="status" aria-label="Loading run">
      <Skeleton className="mb-2 h-4 w-32" />
      <Skeleton className="mb-6 h-7 w-80" />
      <Skeleton className="mb-6 h-10 w-full" />
      <div className="grid gap-6 lg:grid-cols-3">
        <Skeleton className="h-56" />
        <Skeleton className="h-56 lg:col-span-2" />
      </div>
    </div>
  );
}

function threshold(detail: RunDetail): number {
  const value = detail.run.config.link_threshold;
  return typeof value === "number" && Number.isFinite(value) ? value : 0.5;
}

function RunHeader({ detail, replay, onReplay }: { detail: RunDetail; replay: ReplayState; onReplay: (s: ReplayState) => void }) {
  const { run } = detail;
  return (
    <PageHeader
      eyebrow={
        <Link href="/" className="inline-flex items-center gap-1 text-xs font-medium text-slate-500 hover:text-slate-800">
          <ArrowLeft className="size-3.5" aria-hidden />
          Dashboard
        </Link>
      }
      title={
        <span className="flex flex-wrap items-center gap-3">
          {detail.candidate.name ?? "Unnamed candidate"}
          <span className="font-normal text-slate-400">·</span>
          <span className="font-medium text-slate-700">{detail.job.title}</span>
          <RunStatusBadge status={run.status} />
        </span>
      }
      description={
        <span className="flex flex-wrap items-center gap-x-4 gap-y-1">
          <span>Started {formatDateTime(run.started_at)}</span>
          {run.finished_at && (
            <span>
              Finished {formatDateTime(run.finished_at)} ({formatDuration(run.started_at, run.finished_at)})
            </span>
          )}
          <span className="inline-flex items-center gap-1">
            Run <code className="font-mono text-xs text-slate-600">{run.id}</code>
            <CopyButton value={run.id} label="Copy run ID" />
          </span>
          {detail.candidate.email_masked && <span>{detail.candidate.email_masked}</span>}
        </span>
      }
      actions={<RunActions detail={detail} replay={replay} onReplay={onReplay} />}
    />
  );
}

function FinishedTabs({ detail }: { detail: RunDetail }) {
  const [tab, setTab] = useState<TabId>("overview");
  const items: TabItem<TabId>[] = [
    { id: "overview", label: "Overview" },
    { id: "claims", label: "Claims", count: detail.claims.length },
    { id: "requirements", label: "Requirements", count: detail.matches.length },
    { id: "identity", label: "Identity", count: detail.accounts.length },
    { id: "evidence", label: "Evidence", count: detail.evidence.length },
    { id: "snapshots", label: "Raw data", count: detail.snapshots.length },
  ];
  return (
    <div>
      <Tabs items={items} value={tab} onChange={setTab} label="Run details" idPrefix="run" />
      <TabPanel idPrefix="run" id={tab}>
        {tab === "overview" && <OverviewTab detail={detail} />}
        {tab === "claims" && <ClaimsTab claims={detail.claims} resumeText={detail.candidate.resume_text} />}
        {tab === "requirements" && <RequirementsTab matches={detail.matches} coverage={detail.coverage} requiredSkills={detail.job.required_skills} />}
        {tab === "identity" && <IdentityTab accounts={detail.accounts} threshold={threshold(detail)} />}
        {tab === "evidence" && <EvidenceTab evidence={detail.evidence} />}
        {tab === "snapshots" && <SnapshotsTab snapshots={detail.snapshots} />}
      </TabPanel>
    </div>
  );
}

export function RunView({ runId }: { runId: string }) {
  const { state, reload } = useRun(runId);
  const [snapshotId, setSnapshotId] = useState<string | null>(null);
  const [replay, setReplay] = useState<ReplayState>({ kind: "idle" });
  const openSnapshot = useCallback((id: string) => setSnapshotId(id), []);

  const detail = state.kind === "ready" ? state.detail : null;
  const context = useMemo<RunContextValue | null>(
    () =>
      detail && {
        detail,
        nodeById: new Map(detail.evidence.map((n) => [n.id, n])),
        snapshotById: new Map(detail.snapshots.map((s) => [s.id, s])),
        openSnapshot,
      },
    [detail, openSnapshot],
  );

  if (state.kind === "loading") return <LoadingView />;

  if (state.kind === "error") {
    if (state.error.isNotFound) {
      return (
        <Card>
          <EmptyState
            icon={<FileQuestion className="size-5" />}
            title="Run not found"
            description={`No run with ID ${runId} exists. It may have been deleted with the candidate's data.`}
            action={
              <Link href="/" className={buttonClasses("secondary")}>
                Back to dashboard
              </Link>
            }
          />
        </Card>
      );
    }
    return (
      <ErrorPanel
        error={state.error}
        title="This run could not be loaded"
        action={
          <Button size="sm" onClick={reload}>
            Try again
          </Button>
        }
      />
    );
  }

  if (!context || !detail) return null;
  const running = detail.run.status === "running";

  return (
    <RunContext.Provider value={context}>
      <RunHeader detail={detail} replay={replay} onReplay={setReplay} />
      <div className="space-y-6">
        <ReplayBanner state={replay} original={detail.report?.total ?? null} onDismiss={() => setReplay({ kind: "idle" })} />
        {state.pollError && (
          <p role="status" className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
            Lost contact with the backend ({state.pollError.code}). Retrying…
          </p>
        )}
        {running ? (
          <Card>
            <CardHeader
              title={
                <span className="inline-flex items-center gap-2">
                  <Loader2 className="size-4 animate-spin text-indigo-600" aria-hidden />
                  Pipeline running
                </span>
              }
              description="This page updates automatically. Results appear when scoring finishes."
            />
            <CardBody>
              <PipelineTimeline progress={detail.progress} status={detail.run.status} stage={detail.run.stage} failures={detail.run.failures} />
            </CardBody>
          </Card>
        ) : (
          <FinishedTabs detail={detail} />
        )}
        {!running && detail.progress.length > 0 && (
          <details className="group rounded-lg border border-slate-200 bg-white">
            <summary className="cursor-pointer px-5 py-3 text-sm font-medium text-slate-700 select-none">Pipeline timeline</summary>
            <div className="border-t border-slate-100 px-5 py-4">
              <PipelineTimeline progress={detail.progress} status={detail.run.status} stage={detail.run.stage} failures={detail.run.failures} />
            </div>
          </details>
        )}
      </div>
      <SnapshotDrawer snapshotId={snapshotId} snapshot={snapshotId ? (context.snapshotById.get(snapshotId) ?? null) : null} onClose={() => setSnapshotId(null)} />
    </RunContext.Provider>
  );
}
