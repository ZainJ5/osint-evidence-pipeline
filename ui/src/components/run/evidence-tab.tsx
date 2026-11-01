"use client";

import { useMemo, useState } from "react";
import { Search, SearchX } from "lucide-react";
import { sourceLabel, summarizeEvidence } from "@/lib/domain";
import type { EvidenceKind, EvidenceNode } from "@/lib/types";
import { cn } from "@/lib/cn";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Table, TBody, Td, Th, THead, Tr } from "@/components/ui/table";
import { Tooltip } from "@/components/ui/tooltip";
import { LinkedBadge } from "@/components/status/status-badges";
import { SourceBadge } from "@/components/status/source-badge";
import { SnapshotLink } from "./evidence-node-item";

const KINDS: EvidenceKind[] = ["skill", "project", "contribution", "achievement"];
const PAGE = 200;

function Select({ id, label, value, onChange, options }: { id: string; label: string; value: string; onChange: (v: string) => void; options: { value: string; label: string }[] }) {
  return (
    <div>
      <label htmlFor={id} className="sr-only">
        {label}
      </label>
      <select
        id={id}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="h-9 rounded-md border border-slate-300 bg-white px-2.5 text-sm text-slate-700 shadow-xs focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 focus:outline-none"
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </div>
  );
}

function matchesQuery(node: EvidenceNode, query: string): boolean {
  if (!query) return true;
  const haystack = `${node.handle} ${node.kind} ${node.locator} ${JSON.stringify(node.value)}`.toLowerCase();
  return haystack.includes(query.toLowerCase());
}

export function EvidenceTab({ evidence }: { evidence: EvidenceNode[] }) {
  const [source, setSource] = useState("all");
  const [kind, setKind] = useState("all");
  const [linked, setLinked] = useState("all");
  const [query, setQuery] = useState("");
  const [limit, setLimit] = useState(PAGE);

  const sources = useMemo(() => [...new Set(evidence.map((n) => n.source))], [evidence]);
  const rows = useMemo(
    () =>
      evidence.filter(
        (n) =>
          (source === "all" || n.source === source) &&
          (kind === "all" || n.kind === kind) &&
          (linked === "all" || (linked === "linked") === n.linked) &&
          matchesQuery(n, query.trim()),
      ),
    [evidence, source, kind, linked, query],
  );

  return (
    <Card>
      <div className="flex flex-wrap items-center gap-2 border-b border-slate-100 px-4 py-3">
        <div className="relative min-w-56 flex-1">
          <Search className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-slate-400" aria-hidden />
          <label htmlFor="evidence-search" className="sr-only">
            Search evidence
          </label>
          <input
            id="evidence-search"
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search names, repos, values…"
            className="h-9 w-full rounded-md border border-slate-300 bg-white pr-3 pl-8 text-sm shadow-xs placeholder:text-slate-400 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 focus:outline-none"
          />
        </div>
        <Select id="evidence-source" label="Source" value={source} onChange={setSource} options={[{ value: "all", label: "All sources" }, ...sources.map((s) => ({ value: s, label: sourceLabel(s) }))]} />
        <Select id="evidence-kind" label="Kind" value={kind} onChange={setKind} options={[{ value: "all", label: "All kinds" }, ...KINDS.map((k) => ({ value: k, label: k[0].toUpperCase() + k.slice(1) }))]} />
        <Select
          id="evidence-linked"
          label="Identity"
          value={linked}
          onChange={setLinked}
          options={[
            { value: "all", label: "Linked and unlinked" },
            { value: "linked", label: "Linked only" },
            { value: "unlinked", label: "Unlinked only" },
          ]}
        />
        <span className="ml-auto text-xs text-slate-500 tabular-nums" aria-live="polite">
          {rows.length} of {evidence.length} nodes
        </span>
      </div>
      {rows.length === 0 ? (
        <EmptyState icon={<SearchX className="size-5" />} title="No evidence matches" description="Adjust the filters or search text." />
      ) : (
        <Table>
          <THead>
            <tr>
              <Th>Source</Th>
              <Th>Kind</Th>
              <Th>Evidence</Th>
              <Th>Identity</Th>
              <Th>Locator</Th>
              <Th>
                <span className="sr-only">Snapshot</span>
              </Th>
            </tr>
          </THead>
          <TBody>
            {rows.slice(0, limit).map((node) => {
              const summary = summarizeEvidence(node);
              return (
                <Tr key={node.id} className={cn(!node.linked && "bg-slate-50/70 text-slate-500 [&_td]:opacity-70")}>
                  <Td>
                    <SourceBadge source={node.source} />
                    <span className="block pl-6.5 text-xs text-slate-500">{node.handle}</span>
                  </Td>
                  <Td className="capitalize">{node.kind}</Td>
                  <Td className="min-w-64">
                    <span className="font-medium text-slate-900">{summary.title}</span>
                    {summary.facts.length > 0 && (
                      <span className="mt-0.5 block text-xs text-slate-500">{summary.facts.map((f) => `${f.label}: ${f.value}`).join(" · ")}</span>
                    )}
                  </Td>
                  <Td>
                    {node.linked ? (
                      <LinkedBadge linked />
                    ) : (
                      <Tooltip align="end" content="This account is below the identity threshold. Its evidence is excluded from verification and scoring.">
                        <span tabIndex={0} className="rounded-full">
                          <LinkedBadge linked={false} />
                        </span>
                      </Tooltip>
                    )}
                  </Td>
                  <Td className="max-w-56 font-mono text-xs break-all">{node.locator}</Td>
                  <Td>
                    <SnapshotLink snapshotId={node.snapshot_id} />
                  </Td>
                </Tr>
              );
            })}
          </TBody>
        </Table>
      )}
      {rows.length > limit && (
        <div className="border-t border-slate-100 p-3 text-center">
          <button type="button" onClick={() => setLimit(limit + PAGE)} className="text-sm font-medium text-indigo-700 hover:underline">
            Show {Math.min(PAGE, rows.length - limit)} more
          </button>
        </div>
      )}
    </Card>
  );
}
