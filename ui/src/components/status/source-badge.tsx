import { sourceLabel } from "@/lib/domain";
import { cn } from "@/lib/cn";

const MARKS: Record<string, { mark: string; className: string }> = {
  github: { mark: "GH", className: "bg-slate-900 text-white" },
  codeforces: { mark: "CF", className: "bg-sky-700 text-white" },
  leetcode: { mark: "LC", className: "bg-amber-500 text-slate-950" },
};

export function SourceMark({ source, className }: { source: string; className?: string }) {
  const entry = MARKS[source] ?? { mark: source.slice(0, 2).toUpperCase(), className: "bg-slate-500 text-white" };
  return (
    <span
      aria-hidden
      className={cn(
        "inline-flex size-5 shrink-0 items-center justify-center rounded text-[9px] leading-none font-bold tracking-tight",
        entry.className,
        className,
      )}
    >
      {entry.mark}
    </span>
  );
}

export function SourceBadge({ source, handle, className }: { source: string; handle?: string; className?: string }) {
  return (
    <span className={cn("inline-flex items-center gap-1.5 text-sm whitespace-nowrap text-slate-700", className)}>
      <SourceMark source={source} />
      <span>{sourceLabel(source)}</span>
      {handle && <span className="text-slate-500">· {handle}</span>}
    </span>
  );
}

export function SourceList({ sources }: { sources: string[] }) {
  if (!sources.length) return <span className="text-sm text-slate-400">None</span>;
  return (
    <span className="inline-flex items-center gap-1" aria-label={sources.map(sourceLabel).join(", ")}>
      {sources.map((source) => (
        <span key={source} title={sourceLabel(source)}>
          <SourceMark source={source} />
        </span>
      ))}
    </span>
  );
}
