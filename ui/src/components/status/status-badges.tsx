import type { ReactNode } from "react";
import { AlertTriangle, CheckCircle2, CircleDashed, CircleMinus, CircleSlash, Link2, Loader2, Unlink, XCircle } from "lucide-react";
import { Badge, type Tone } from "@/components/ui/badge";
import { VERDICT_INFO } from "@/lib/domain";
import type { RunStatus, VerdictLabel } from "@/lib/types";

const RUN_STATUS: Record<RunStatus, { label: string; tone: Tone; icon: ReactNode }> = {
  running: { label: "Running", tone: "running", icon: <Loader2 className="size-3 animate-spin" aria-hidden /> },
  done: { label: "Completed", tone: "supported", icon: <CheckCircle2 className="size-3" aria-hidden /> },
  partial: { label: "Partial", tone: "partial", icon: <AlertTriangle className="size-3" aria-hidden /> },
  failed: { label: "Failed", tone: "unsupported", icon: <XCircle className="size-3" aria-hidden /> },
};

export function RunStatusBadge({ status }: { status: RunStatus }) {
  const info = RUN_STATUS[status] ?? { label: status, tone: "neutral" as Tone, icon: <CircleDashed className="size-3" aria-hidden /> };
  return (
    <Badge tone={info.tone} icon={info.icon} title={status === "partial" ? "Completed with one or more source failures" : undefined}>
      {info.label}
    </Badge>
  );
}

const VERDICT_ICONS: Record<VerdictLabel, ReactNode> = {
  supported: <CheckCircle2 className="size-3" aria-hidden />,
  partially_supported: <CircleMinus className="size-3" aria-hidden />,
  unsupported: <CircleSlash className="size-3" aria-hidden />,
};

export function VerdictBadge({ label }: { label: VerdictLabel | null }) {
  if (!label) return <Badge tone="neutral">Not verified</Badge>;
  const info = VERDICT_INFO[label];
  return (
    <Badge tone={info.tone} icon={VERDICT_ICONS[label]}>
      {info.label}
    </Badge>
  );
}

export function LinkedBadge({ linked }: { linked: boolean }) {
  return linked ? (
    <Badge tone="accent" icon={<Link2 className="size-3" aria-hidden />}>
      Linked
    </Badge>
  ) : (
    <Badge tone="unlinked" icon={<Unlink className="size-3" aria-hidden />}>
      Unlinked
    </Badge>
  );
}

export function CoverageBadge({ covered }: { covered: boolean }) {
  return covered ? (
    <Badge tone="supported" icon={<CheckCircle2 className="size-3" aria-hidden />}>
      Covered
    </Badge>
  ) : (
    <Badge tone="unsupported" icon={<CircleSlash className="size-3" aria-hidden />}>
      Not covered
    </Badge>
  );
}
