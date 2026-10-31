"use client";

import { useState } from "react";
import { ChevronDown, ListChecks } from "lucide-react";
import { formatPercent } from "@/lib/format";
import type { Match } from "@/lib/types";
import { cn } from "@/lib/cn";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Meter } from "@/components/ui/meter";
import { CoverageBadge } from "@/components/status/status-badges";
import { EvidenceNodeList } from "./evidence-node-item";

function MatchRow({ match, label }: { match: Match; label: string }) {
  const [open, setOpen] = useState(false);
  return (
    <li className="py-3">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        <span className="min-w-40 flex-1 text-sm font-medium text-slate-900">{label}</span>
        <CoverageBadge covered={match.covered} />
        <div className="flex w-44 items-center gap-2" title="Similarity between the required skill and the best matching evidence">
          <Meter value={match.similarity} label={`Similarity for ${label}`} size="sm" barClassName={match.covered ? "bg-emerald-500" : "bg-slate-400"} />
          <span className="w-10 text-right text-xs text-slate-600 tabular-nums">{formatPercent(match.similarity)}</span>
        </div>
        <button
          type="button"
          onClick={() => setOpen(!open)}
          aria-expanded={open}
          disabled={!match.node_ids.length}
          className="inline-flex w-28 items-center justify-end gap-1 text-xs font-medium text-indigo-700 hover:underline disabled:text-slate-400 disabled:no-underline"
        >
          {match.node_ids.length} node{match.node_ids.length === 1 ? "" : "s"}
          {match.node_ids.length > 0 && <ChevronDown className={cn("size-3.5 transition-transform", open && "rotate-180")} aria-hidden />}
        </button>
      </div>
      {open && (
        <div className="mt-3">
          <EvidenceNodeList ids={match.node_ids} emptyText="No matching evidence." />
        </div>
      )}
    </li>
  );
}

export function RequirementsTab({ matches, coverage, requiredSkills }: { matches: Match[]; coverage: number | null; requiredSkills: string[] }) {
  if (!matches.length) {
    return (
      <Card>
        <EmptyState icon={<ListChecks className="size-5" />} title="No requirement matches" description="Matching has not produced results for this run." />
      </Card>
    );
  }
  const covered = matches.filter((m) => m.covered).length;
  const labelFor = (skill: string) => requiredSkills.find((s) => s.toLowerCase() === skill.toLowerCase()) ?? skill;
  return (
    <div className="space-y-6">
      <Card>
        <CardBody className="flex flex-wrap items-center gap-6">
          <div>
            <p className="text-xs font-medium text-slate-500">Requirement coverage</p>
            <p className="text-3xl font-semibold text-slate-900 tabular-nums">{formatPercent(coverage)}</p>
          </div>
          <div className="min-w-56 flex-1">
            <Meter value={coverage ?? 0} label="Requirement coverage" barClassName="bg-emerald-500" />
            <p className="mt-2 text-sm text-slate-600">
              {covered} of {matches.length} required skills are backed by evidence from linked accounts.
            </p>
          </div>
        </CardBody>
      </Card>
      <Card>
        <CardHeader title="Required skills" description="Similarity is how closely the best evidence matches the required skill (1.00 = exact)." />
        <CardBody className="py-1">
          <ul className="divide-y divide-slate-100">
            {matches.map((match) => (
              <MatchRow key={match.skill} match={match} label={labelFor(match.skill)} />
            ))}
          </ul>
        </CardBody>
      </Card>
    </div>
  );
}
