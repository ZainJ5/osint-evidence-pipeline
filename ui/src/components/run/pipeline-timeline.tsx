import type { ReactNode } from "react";
import { AlertTriangle, CheckCircle2, Circle, Loader2 } from "lucide-react";
import { explainFailure, STAGE_INFO } from "@/lib/domain";
import { formatDuration } from "@/lib/format";
import { STAGES, type Failure, type ProgressEvent, type RunStatus, type Stage } from "@/lib/types";
import { cn } from "@/lib/cn";
import { SourceMark } from "@/components/status/source-badge";

type StageState = "pending" | "active" | "done" | "stopped";

interface StageView {
  stage: Stage;
  state: StageState;
  startedAt: string | null;
  doneAt: string | null;
  detail: Record<string, unknown>;
}

function buildStages(progress: ProgressEvent[], runStatus: RunStatus, current: Stage | "finished"): StageView[] {
  return STAGES.map((stage) => {
    const started = progress.find((e) => e.stage === stage && e.status === "started");
    const done = progress.find((e) => e.stage === stage && e.status === "done");
    let state: StageState = "pending";
    if (done) state = "done";
    else if (started) state = runStatus === "running" ? "active" : "stopped";
    else if (runStatus === "running" && current === stage) state = "active";
    return {
      stage,
      state,
      startedAt: started?.at ?? null,
      doneAt: done?.at ?? null,
      detail: { ...(started?.detail ?? {}), ...(done?.detail ?? {}) },
    };
  });
}

function formatDetail(detail: Record<string, unknown>): string[] {
  return Object.entries(detail)
    .filter(([, value]) => value !== null && value !== undefined && typeof value !== "object")
    .map(([key, value]) => `${String(value)} ${key.replace(/_/g, " ")}`);
}

const ICONS: Record<StageState, ReactNode> = {
  pending: <Circle className="size-5 text-slate-300" aria-hidden />,
  active: <Loader2 className="size-5 animate-spin text-indigo-600" aria-hidden />,
  done: <CheckCircle2 className="size-5 text-emerald-600" aria-hidden />,
  stopped: <AlertTriangle className="size-5 text-amber-600" aria-hidden />,
};

const STATE_TEXT: Record<StageState, string> = {
  pending: "Waiting",
  active: "In progress",
  done: "Done",
  stopped: "Did not finish",
};

export function FailureList({ failures }: { failures: Failure[] }) {
  if (!failures.length) return null;
  return (
    <ul className="space-y-2" aria-label="Source failures">
      {failures.map((failure, i) => (
        <li key={`${failure.source}-${failure.code}-${i}`} className="flex items-start gap-2.5 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
          <SourceMark source={failure.source} className="mt-0.5" />
          <span className="min-w-0">
            {explainFailure(failure)}
            <span className="ml-1.5 font-mono text-xs text-amber-700">{failure.code}</span>
          </span>
        </li>
      ))}
    </ul>
  );
}

interface PipelineTimelineProps {
  progress: ProgressEvent[];
  status: RunStatus;
  stage: Stage | "finished";
  failures: Failure[];
}

export function PipelineTimeline({ progress, status, stage, failures }: PipelineTimelineProps) {
  const stages = buildStages(progress, status, stage);
  const noProgress = progress.length === 0;
  return (
    <div>
      {noProgress && (
        <p className="mb-4 text-sm text-slate-500">
          {status === "running"
            ? "Waiting for the first stage to report progress…"
            : "Stage progress is not available for this run (it is kept in memory by the API process)."}
        </p>
      )}
      <ol className="relative">
        {stages.map((s, i) => {
          const details = formatDetail(s.detail);
          const stageFailures = s.stage === "collect" ? failures : [];
          return (
            <li key={s.stage} className="relative flex gap-4 pb-6 last:pb-0" aria-current={s.state === "active" ? "step" : undefined}>
              {i < stages.length - 1 && (
                <span
                  aria-hidden
                  className={cn("absolute top-6 left-[9px] h-[calc(100%-1.5rem)] w-0.5", s.state === "done" ? "bg-emerald-200" : "bg-slate-200")}
                />
              )}
              <span className="relative z-10 bg-white">{ICONS[s.state]}</span>
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
                  <h3 className={cn("text-sm font-semibold", s.state === "pending" ? "text-slate-400" : "text-slate-900")}>
                    {STAGE_INFO[s.stage].label}
                  </h3>
                  <span className={cn("text-xs", s.state === "active" ? "font-medium text-indigo-700" : "text-slate-500")}>
                    {STATE_TEXT[s.state]}
                    {s.state === "done" && s.startedAt && s.doneAt && ` · ${formatDuration(s.startedAt, s.doneAt)}`}
                  </span>
                </div>
                <p className={cn("text-sm", s.state === "pending" ? "text-slate-400" : "text-slate-600")}>{STAGE_INFO[s.stage].description}</p>
                {details.length > 0 && (
                  <ul className="mt-1.5 flex flex-wrap gap-1.5">
                    {details.map((d) => (
                      <li key={d} className="rounded bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-700 tabular-nums">
                        {d}
                      </li>
                    ))}
                  </ul>
                )}
                {stageFailures.length > 0 && (
                  <div className="mt-2">
                    <FailureList failures={stageFailures} />
                  </div>
                )}
              </div>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
