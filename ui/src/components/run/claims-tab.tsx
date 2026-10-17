"use client";

import { useMemo, useState, type ReactNode } from "react";
import { ChevronDown, Quote } from "lucide-react";
import { findClaimSpans, VERDICT_INFO } from "@/lib/domain";
import { formatNumber } from "@/lib/format";
import type { Claim, VerdictLabel } from "@/lib/types";
import { cn } from "@/lib/cn";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { VerdictBadge } from "@/components/status/status-badges";
import { EvidenceNodeList } from "./evidence-node-item";

type Filter = "all" | VerdictLabel;

const HIGHLIGHT: Record<VerdictLabel | "none", string> = {
  supported: "bg-emerald-100 decoration-emerald-500 hover:bg-emerald-200",
  partially_supported: "bg-amber-100 decoration-amber-500 hover:bg-amber-200",
  unsupported: "bg-rose-100 decoration-rose-500 hover:bg-rose-200",
  none: "bg-slate-100 decoration-slate-400 hover:bg-slate-200",
};

function claimElementId(claim: Claim): string {
  return `claim-${claim.id}`;
}

function ClaimCard({ claim }: { claim: Claim }) {
  const [open, setOpen] = useState(false);
  const ids = claim.verdict?.evidence_node_ids ?? [];
  const facts = [
    { label: "Kind", value: claim.kind },
    { label: "Subject", value: claim.subject },
    { label: "Years", value: claim.years !== null ? String(claim.years) : null },
    { label: "Rating", value: claim.rating !== null ? String(claim.rating) : null },
    { label: "Solved", value: claim.solved !== null ? formatNumber(claim.solved) : null },
  ].filter((f) => f.value);
  return (
    <Card id={claimElementId(claim)} className="scroll-mt-24">
      <CardBody className="space-y-3">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <p className="flex min-w-0 items-start gap-2 text-sm font-medium text-slate-900">
            <Quote className="mt-0.5 size-4 shrink-0 text-slate-300" aria-hidden />
            <span>{claim.text}</span>
          </p>
          <VerdictBadge label={claim.verdict?.label ?? null} />
        </div>
        <dl className="flex flex-wrap gap-x-4 gap-y-1 text-xs">
          {facts.map((f) => (
            <div key={f.label} className="flex gap-1">
              <dt className="text-slate-500">{f.label}</dt>
              <dd className="font-medium text-slate-800">{f.value}</dd>
            </div>
          ))}
        </dl>
        {claim.verdict && <p className="text-sm text-slate-600">{claim.verdict.rationale}</p>}
        <div>
          <button
            type="button"
            onClick={() => setOpen(!open)}
            aria-expanded={open}
            disabled={!ids.length}
            className="inline-flex items-center gap-1 text-xs font-medium text-indigo-700 hover:underline disabled:text-slate-400 disabled:no-underline"
          >
            {ids.length ? `${ids.length} evidence node${ids.length === 1 ? "" : "s"} used` : "No evidence used"}
            {ids.length > 0 && <ChevronDown className={cn("size-3.5 transition-transform", open && "rotate-180")} aria-hidden />}
          </button>
          {open && (
            <div className="mt-2">
              <EvidenceNodeList ids={ids} emptyText="No evidence nodes." />
            </div>
          )}
        </div>
      </CardBody>
    </Card>
  );
}

function ResumeHighlights({ text, claims, onSelect }: { text: string; claims: Claim[]; onSelect: (claim: Claim) => void }) {
  const spans = useMemo(() => findClaimSpans(text, claims), [text, claims]);
  const parts: ReactNode[] = [];
  let cursor = 0;
  spans.forEach((span, i) => {
    if (span.start > cursor) parts.push(text.slice(cursor, span.start));
    const label = span.claim.verdict?.label ?? "none";
    parts.push(
      <button
        key={`${span.claim.id}-${i}`}
        type="button"
        onClick={() => onSelect(span.claim)}
        className={cn("rounded-sm px-0.5 underline decoration-2 underline-offset-2 transition-colors", HIGHLIGHT[label])}
        aria-label={`${span.claim.text}: ${span.claim.verdict ? VERDICT_INFO[span.claim.verdict.label].label : "not verified"}. Show claim.`}
      >
        {text.slice(span.start, span.end)}
      </button>,
    );
    cursor = span.end;
  });
  if (cursor < text.length) parts.push(text.slice(cursor));
  return (
    <div className="max-h-[70vh] overflow-auto text-sm leading-7 whitespace-pre-wrap text-slate-700" tabIndex={0} aria-label="Resume text with highlighted claims">
      {parts}
    </div>
  );
}

export function ClaimsTab({ claims, resumeText }: { claims: Claim[]; resumeText: string }) {
  const [filter, setFilter] = useState<Filter>("all");

  const counts = useMemo(() => {
    const c: Record<Filter, number> = { all: claims.length, supported: 0, partially_supported: 0, unsupported: 0 };
    for (const claim of claims) if (claim.verdict) c[claim.verdict.label] += 1;
    return c;
  }, [claims]);

  const unlocated = useMemo(
    () => claims.length - new Set(findClaimSpans(resumeText, claims).map((s) => s.claim.id)).size,
    [claims, resumeText],
  );

  const visible = filter === "all" ? claims : claims.filter((c) => c.verdict?.label === filter);

  function select(claim: Claim) {
    if (filter !== "all" && claim.verdict?.label !== filter) setFilter("all");
    requestAnimationFrame(() => {
      const el = document.getElementById(claimElementId(claim));
      if (!el) return;
      el.scrollIntoView({ behavior: "smooth", block: "center" });
      el.classList.remove("flash");
      void el.offsetWidth;
      el.classList.add("flash");
    });
  }

  if (!claims.length) {
    return (
      <Card>
        <EmptyState icon={<Quote className="size-5" />} title="No claims" description="No verifiable claims were extracted from the resume." />
      </Card>
    );
  }

  const filters: { id: Filter; label: string }[] = [
    { id: "all", label: "All" },
    { id: "supported", label: VERDICT_INFO.supported.label },
    { id: "partially_supported", label: VERDICT_INFO.partially_supported.label },
    { id: "unsupported", label: VERDICT_INFO.unsupported.label },
  ];

  return (
    <div className="grid gap-6 lg:grid-cols-5">
      <div className="lg:col-span-3">
        <div className="mb-4 flex flex-wrap gap-2" role="group" aria-label="Filter claims by verdict">
          {filters.map((f) => (
            <button
              key={f.id}
              type="button"
              aria-pressed={filter === f.id}
              onClick={() => setFilter(f.id)}
              className={cn(
                "rounded-full border px-3 py-1 text-xs font-medium transition-colors",
                filter === f.id ? "border-indigo-300 bg-indigo-50 text-indigo-800" : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50",
              )}
            >
              {f.label} <span className="tabular-nums">({counts[f.id]})</span>
            </button>
          ))}
        </div>
        <div className="space-y-3">
          {visible.map((claim) => (
            <ClaimCard key={claim.id} claim={claim} />
          ))}
          {!visible.length && <p className="text-sm text-slate-500">No claims with this verdict.</p>}
        </div>
      </div>
      <div className="lg:col-span-2">
        <Card className="lg:sticky lg:top-20">
          <CardHeader title="Resume" description="Highlighted text is a claim. Select it to jump to its verdict." />
          <CardBody>
            <ResumeHighlights text={resumeText} claims={claims} onSelect={select} />
            <ul className="mt-4 flex flex-wrap gap-3 border-t border-slate-100 pt-3 text-xs text-slate-600" aria-label="Legend">
              {(["supported", "partially_supported", "unsupported"] as VerdictLabel[]).map((label) => (
                <li key={label} className="inline-flex items-center gap-1.5">
                  <span className={cn("size-3 rounded-sm", HIGHLIGHT[label])} aria-hidden />
                  {VERDICT_INFO[label].label}
                </li>
              ))}
            </ul>
            {unlocated > 0 && (
              <p className="mt-2 text-xs text-slate-500">
                {unlocated} claim{unlocated === 1 ? " is" : "s are"} paraphrased and cannot be located verbatim in the text.
              </p>
            )}
          </CardBody>
        </Card>
      </div>
    </div>
  );
}
