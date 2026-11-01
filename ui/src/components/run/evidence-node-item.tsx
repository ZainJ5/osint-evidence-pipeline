"use client";

import { Database, Unlink } from "lucide-react";
import { summarizeEvidence } from "@/lib/domain";
import type { EvidenceNode } from "@/lib/types";
import { cn } from "@/lib/cn";
import { SourceMark } from "@/components/status/source-badge";
import { useRunContext } from "./run-context";

export function SnapshotLink({ snapshotId, className }: { snapshotId: string; className?: string }) {
  const { openSnapshot, snapshotById } = useRunContext();
  const snapshot = snapshotById.get(snapshotId);
  return (
    <button
      type="button"
      onClick={(event) => {
        event.stopPropagation();
        openSnapshot(snapshotId);
      }}
      className={cn("inline-flex items-center gap-1 text-xs font-medium whitespace-nowrap text-indigo-700 hover:underline", className)}
      aria-label={`View raw snapshot${snapshot ? ` ${snapshot.endpoint}` : ""}`}
    >
      <Database className="size-3.5" aria-hidden />
      View raw snapshot
    </button>
  );
}

export function EvidenceNodeItem({ node }: { node: EvidenceNode }) {
  const summary = summarizeEvidence(node);
  return (
    <li className={cn("rounded-md border border-slate-200 bg-white p-3", !node.linked && "opacity-60")}>
      <div className="flex flex-wrap items-center gap-2">
        <SourceMark source={node.source} />
        <span className="text-sm font-medium text-slate-900">{summary.title}</span>
        <span className="rounded bg-slate-100 px-1.5 py-0.5 text-[11px] font-medium text-slate-600 capitalize">{node.kind}</span>
        <span className="text-xs text-slate-500">{node.handle}</span>
        {!node.linked && (
          <span className="inline-flex items-center gap-1 text-xs text-slate-500">
            <Unlink className="size-3" aria-hidden />
            Unlinked, excluded
          </span>
        )}
        <SnapshotLink snapshotId={node.snapshot_id} className="ml-auto" />
      </div>
      {summary.facts.length > 0 && (
        <dl className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs">
          {summary.facts.map((f) => (
            <div key={f.label} className="flex gap-1">
              <dt className="text-slate-500">{f.label}</dt>
              <dd className="font-medium text-slate-800">{f.value}</dd>
            </div>
          ))}
        </dl>
      )}
      <p className="mt-1.5 font-mono text-[11px] break-all text-slate-500">{node.locator}</p>
    </li>
  );
}

export function EvidenceNodeList({ ids, emptyText }: { ids: string[]; emptyText: string }) {
  const { nodeById } = useRunContext();
  const nodes = ids.map((id) => nodeById.get(id)).filter((n): n is EvidenceNode => Boolean(n));
  const missing = ids.length - nodes.length;
  if (!ids.length) return <p className="text-sm text-slate-500">{emptyText}</p>;
  return (
    <div>
      <ul className="space-y-2">
        {nodes.map((node) => (
          <EvidenceNodeItem key={node.id} node={node} />
        ))}
      </ul>
      {missing > 0 && <p className="mt-2 text-xs text-slate-500">{missing} referenced node(s) are not part of this run detail.</p>}
    </div>
  );
}
