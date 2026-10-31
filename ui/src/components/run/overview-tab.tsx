"use client";

import { useState, type ReactNode } from "react";
import { ChevronDown, Info } from "lucide-react";
import { formatPercent, formatScore } from "@/lib/format";
import type { RunDetail } from "@/lib/types";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Table, TBody, Td, Th, THead, Tr } from "@/components/ui/table";
import { ContributionBar, componentColor } from "./contribution-bar";
import { EvidenceNodeList } from "./evidence-node-item";
import { FailureList } from "./pipeline-timeline";
import { ScoreRing } from "./score-ring";

function Fact({ label, value, sub }: { label: string; value: ReactNode; sub?: ReactNode }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white px-4 py-3">
      <dt className="text-xs font-medium text-slate-500">{label}</dt>
      <dd className="mt-1 text-xl font-semibold text-slate-900 tabular-nums">{value}</dd>
      {sub && <dd className="mt-0.5 text-xs text-slate-500">{sub}</dd>}
    </div>
  );
}

export function KeyFacts({ detail }: { detail: RunDetail }) {
  const linkedAccounts = detail.accounts.filter((a) => a.linked);
  const linkedSources = new Set(linkedAccounts.map((a) => a.source));
  const linkedNodes = detail.evidence.filter((n) => n.linked).length;
  const verified = detail.claims.filter((c) => c.verdict);
  const supported = verified.filter((c) => c.verdict?.label === "supported").length;
  const partial = verified.filter((c) => c.verdict?.label === "partially_supported").length;
  const covered = detail.matches.filter((m) => m.covered).length;
  return (
    <dl className="grid grid-cols-2 gap-3 xl:grid-cols-4">
      <Fact label="Sources linked" value={linkedSources.size} sub={`${linkedAccounts.length} of ${detail.accounts.length} accounts above threshold`} />
      <Fact label="Evidence nodes" value={linkedNodes} sub={`${detail.evidence.length - linkedNodes} excluded from unlinked accounts`} />
      <Fact label="Claims supported" value={`${supported}/${detail.claims.length}`} sub={`${partial} partially supported`} />
      <Fact
        label="Requirement coverage"
        value={formatPercent(detail.coverage)}
        sub={`${covered} of ${detail.matches.length} required skills`}
      />
    </dl>
  );
}

function ComponentEvidence({ ids }: { ids: string[] }) {
  const [open, setOpen] = useState(false);
  if (!ids.length) return <span className="text-slate-400">—</span>;
  return (
    <div>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        aria-expanded={open}
        className="inline-flex items-center gap-1 text-xs font-medium text-indigo-700 hover:underline"
      >
        {ids.length} node{ids.length === 1 ? "" : "s"}
        <ChevronDown className={`size-3.5 transition-transform ${open ? "rotate-180" : ""}`} aria-hidden />
      </button>
      {open && (
        <div className="mt-2 min-w-72">
          <EvidenceNodeList ids={ids} emptyText="No evidence nodes." />
        </div>
      )}
    </div>
  );
}

export function OverviewTab({ detail }: { detail: RunDetail }) {
  const report = detail.report;
  const weightSum = report?.components.reduce((s, c) => s + c.weight, 0) ?? 0;

  return (
    <div className="space-y-6">
      {detail.run.failures.length > 0 && <FailureList failures={detail.run.failures} />}
      {!report ? (
        <Card>
          <EmptyState
            icon={<Info className="size-5" />}
            title="No score for this run"
            description={detail.run.status === "failed" ? "The run failed before scoring finished." : "Scoring has not finished yet."}
          />
        </Card>
      ) : (
        <>
          <div className="grid gap-6 lg:grid-cols-3">
            <Card className="flex flex-col items-center justify-center gap-3 p-6">
              <ScoreRing total={report.total} />
              <p className="text-center text-sm text-slate-500">
                Explainable score for <span className="font-medium text-slate-700">{detail.job.title}</span>
              </p>
            </Card>
            <Card className="lg:col-span-2">
              <CardHeader title="Score breakdown" description="Each component's contribution in points. Contributions add up to the total." />
              <CardBody className="space-y-5">
                <ContributionBar components={report.components} total={report.total} />
                <KeyFacts detail={detail} />
              </CardBody>
            </Card>
          </div>

          <Card>
            <CardHeader title="Components" />
            <Table>
              <THead>
                <tr>
                  <Th>Component</Th>
                  <Th className="text-right">Weight</Th>
                  <Th className="text-right">Value</Th>
                  <Th className="text-right">Points</Th>
                  <Th>Formula</Th>
                  <Th>Evidence</Th>
                </tr>
              </THead>
              <TBody>
                {report.components.map((c, i) => (
                  <Tr key={c.name}>
                    <Td>
                      <span className="inline-flex items-center gap-2 font-medium text-slate-900">
                        <span className={`size-2.5 shrink-0 rounded-sm ${componentColor(i)}`} aria-hidden />
                        {c.label}
                      </span>
                      <span className="block pl-4.5 font-mono text-xs text-slate-400">{c.name}</span>
                    </Td>
                    <Td className="text-right tabular-nums">{c.weight.toFixed(2)}</Td>
                    <Td className="text-right tabular-nums">{formatPercent(c.value)}</Td>
                    <Td className="text-right font-semibold text-slate-900 tabular-nums">{formatScore(c.contribution)}</Td>
                    <Td className="min-w-52 max-w-sm text-slate-600">{c.formula}</Td>
                    <Td>
                      <ComponentEvidence ids={c.evidence_node_ids} />
                    </Td>
                  </Tr>
                ))}
                <Tr className="bg-slate-50/80">
                  <Td className="font-semibold text-slate-900">Total</Td>
                  <Td className="text-right tabular-nums">{weightSum.toFixed(2)}</Td>
                  <Td />
                  <Td className="text-right font-semibold text-slate-900 tabular-nums">{formatScore(report.total)}</Td>
                  <Td colSpan={2} />
                </Tr>
              </TBody>
            </Table>
          </Card>

          <Card>
            <CardHeader title="How this score is calculated" />
            <CardBody className="space-y-3 text-sm leading-relaxed text-slate-600">
              <p>
                Each component measures one aspect of the evidence as a value between 0 and 1. Its contribution is{" "}
                <code className="rounded bg-slate-100 px-1.5 py-0.5 font-mono text-xs text-slate-800">100 × weight × value / Σ weights</code>
                {weightSum > 0 && <> (Σ weights = {weightSum.toFixed(2)})</>}, and the total is the sum of all contributions.
              </p>
              <ul className="space-y-1.5">
                {report.components.map((c) => (
                  <li key={c.name}>
                    <span className="font-medium text-slate-800">{c.label}:</span> {c.formula}.{" "}
                    <span className="text-slate-500 tabular-nums">
                      100 × {c.weight} × {Number(c.value.toFixed(4))}
                      {weightSum !== 1 && ` / ${Number(weightSum.toFixed(4))}`} = {formatScore(c.contribution)}
                    </span>
                  </li>
                ))}
              </ul>
              <p>Only evidence from linked accounts counts. Every component lists the evidence nodes it used, each traceable to a raw snapshot.</p>
            </CardBody>
          </Card>
        </>
      )}
    </div>
  );
}
