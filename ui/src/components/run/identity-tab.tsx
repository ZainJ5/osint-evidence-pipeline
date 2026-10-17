import { ExternalLink, Info, UserSearch } from "lucide-react";
import { sourceLabel } from "@/lib/domain";
import { formatPercent } from "@/lib/format";
import type { Account } from "@/lib/types";
import { cn } from "@/lib/cn";
import { Card, CardBody } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Meter } from "@/components/ui/meter";
import { LinkedBadge } from "@/components/status/status-badges";
import { SourceMark } from "@/components/status/source-badge";

function AccountCard({ account, threshold }: { account: Account; threshold: number }) {
  return (
    <Card className={cn(!account.linked && "bg-slate-50")}>
      <CardBody className="space-y-4">
        <div className="flex items-start justify-between gap-3">
          <div className="flex min-w-0 items-center gap-3">
            <SourceMark source={account.source} className="size-8 text-xs" />
            <div className="min-w-0">
              <p className="text-sm font-semibold text-slate-900">{sourceLabel(account.source)}</p>
              {account.profile_url ? (
                <a
                  href={account.profile_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-sm text-indigo-700 hover:underline"
                >
                  {account.handle}
                  <ExternalLink className="size-3.5" aria-hidden />
                  <span className="sr-only">(opens in a new tab)</span>
                </a>
              ) : (
                <p className="text-sm text-slate-600">{account.handle}</p>
              )}
            </div>
          </div>
          <LinkedBadge linked={account.linked} />
        </div>
        <div>
          <div className="mb-1.5 flex items-center justify-between text-xs">
            <span className="font-medium text-slate-600">Identity confidence</span>
            <span className="font-semibold text-slate-900 tabular-nums">{formatPercent(account.confidence)}</span>
          </div>
          <Meter
            value={account.confidence}
            label={`Identity confidence for ${account.handle}`}
            barClassName={account.linked ? "bg-indigo-600" : "bg-slate-400"}
            marker={{ at: threshold, label: `Link threshold ${threshold.toFixed(2)}` }}
          />
          <div className="relative mt-1 h-4 text-[11px] text-slate-500">
            <span className="absolute -translate-x-1/2 whitespace-nowrap" style={{ left: `${threshold * 100}%` }}>
              Threshold {threshold.toFixed(2)}
            </span>
          </div>
        </div>
        <div>
          <p className="mb-1.5 text-xs font-medium text-slate-600">Signals</p>
          {account.rationale.length ? (
            <ul className="space-y-1.5">
              {account.rationale.map((line, i) => (
                <li key={i} className="rounded bg-slate-50 px-2.5 py-1.5 font-mono text-xs leading-relaxed break-words text-slate-700">
                  {line}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-slate-500">No signals fired.</p>
          )}
        </div>
      </CardBody>
    </Card>
  );
}

export function IdentityTab({ accounts, threshold }: { accounts: Account[]; threshold: number }) {
  if (!accounts.length) {
    return (
      <Card>
        <EmptyState icon={<UserSearch className="size-5" />} title="No accounts resolved" description="Identity resolution did not produce any account decisions." />
      </Card>
    );
  }
  return (
    <div className="space-y-4">
      <p className="flex items-start gap-2 rounded-md border border-slate-200 bg-white px-4 py-3 text-sm text-slate-600">
        <Info className="mt-0.5 size-4 shrink-0 text-indigo-600" aria-hidden />
        Accounts with confidence below {threshold.toFixed(2)} are unlinked. Their evidence is kept for audit but excluded from verification,
        matching and scoring.
      </p>
      <div className="grid gap-4 md:grid-cols-2">
        {accounts.map((account) => (
          <AccountCard key={`${account.source}:${account.handle}`} account={account} threshold={threshold} />
        ))}
      </div>
    </div>
  );
}
