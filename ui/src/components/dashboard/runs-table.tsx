"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { FileSearch, Plus, RefreshCw } from "lucide-react";
import { listRuns, toApiError, type ApiError } from "@/lib/api";
import type { RunSummary } from "@/lib/types";
import { formatDateTime, formatRelative, formatScore } from "@/lib/format";
import { Card, CardHeader } from "@/components/ui/card";
import { Button, buttonClasses } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorPanel } from "@/components/ui/error-panel";
import { SkeletonRows } from "@/components/ui/skeleton";
import { Table, TBody, Td, Th, THead, Tr } from "@/components/ui/table";
import { RunStatusBadge } from "@/components/status/status-badges";
import { SourceList } from "@/components/status/source-badge";

type State = { kind: "loading" } | { kind: "ready"; runs: RunSummary[] } | { kind: "error"; error: ApiError };

export function RunsTable() {
  const router = useRouter();
  const [state, setState] = useState<State>({ kind: "loading" });
  const [refreshing, setRefreshing] = useState(false);

  const [nonce, setNonce] = useState(0);

  useEffect(() => {
    let active = true;
    listRuns(50)
      .then((runs) => active && setState({ kind: "ready", runs }))
      .catch((error: unknown) => active && setState({ kind: "error", error: toApiError(error) }))
      .finally(() => active && setRefreshing(false));
    return () => {
      active = false;
    };
  }, [nonce]);

  const load = useCallback(() => {
    setRefreshing(true);
    setNonce((n) => n + 1);
  }, []);

  const hasRunning = state.kind === "ready" && state.runs.some((r) => r.status === "running");
  useEffect(() => {
    if (!hasRunning) return;
    const timer = setInterval(() => setNonce((n) => n + 1), 3000);
    return () => clearInterval(timer);
  }, [hasRunning]);

  return (
    <Card>
      <CardHeader
        title="Recent runs"
        description="Newest first. Select a run to inspect its evidence, claims and score."
        actions={
          <Button size="sm" variant="ghost" onClick={load} loading={refreshing} aria-label="Refresh runs">
            {!refreshing && <RefreshCw className="size-3.5" aria-hidden />}
            Refresh
          </Button>
        }
      />
      {state.kind === "loading" && <SkeletonRows rows={6} />}
      {state.kind === "error" && (
        <div className="p-5">
          <ErrorPanel
            error={state.error}
            title="Runs could not be loaded"
            action={
              <Button size="sm" onClick={load}>
                Try again
              </Button>
            }
          />
        </div>
      )}
      {state.kind === "ready" && state.runs.length === 0 && (
        <EmptyState
          icon={<FileSearch className="size-5" />}
          title="No analyses yet"
          description="Upload a resume and a job requirement to collect public evidence and verify the candidate's claims."
          action={
            <Link href="/new" className={buttonClasses("primary")}>
              <Plus className="size-4" aria-hidden />
              New analysis
            </Link>
          }
        />
      )}
      {state.kind === "ready" && state.runs.length > 0 && (
        <Table>
          <THead>
            <tr>
              <Th>Candidate</Th>
              <Th>Job</Th>
              <Th>Sources</Th>
              <Th>Status</Th>
              <Th className="text-right">Score</Th>
              <Th>Started</Th>
            </tr>
          </THead>
          <TBody>
            {state.runs.map((run) => (
              <Tr
                key={run.run_id}
                onClick={() => router.push(`/runs/${run.run_id}`)}
                className="cursor-pointer align-middle transition-colors hover:bg-slate-50"
              >
                <Td>
                  <Link
                    href={`/runs/${run.run_id}`}
                    onClick={(e) => e.stopPropagation()}
                    className="font-medium text-slate-900 hover:text-indigo-700"
                  >
                    {run.candidate_name || "Unnamed candidate"}
                  </Link>
                </Td>
                <Td className="max-w-64 truncate">{run.job_title}</Td>
                <Td>
                  <SourceList sources={run.sources} />
                </Td>
                <Td>
                  <RunStatusBadge status={run.status} />
                </Td>
                <Td className="text-right font-semibold text-slate-900 tabular-nums">
                  {formatScore(run.total)}
                  {run.total !== null && <span className="font-normal text-slate-400">/100</span>}
                </Td>
                <Td className="whitespace-nowrap text-slate-500">
                  <time dateTime={run.started_at} title={formatDateTime(run.started_at)}>
                    {formatRelative(run.started_at)}
                  </time>
                </Td>
              </Tr>
            ))}
          </TBody>
        </Table>
      )}
    </Card>
  );
}
