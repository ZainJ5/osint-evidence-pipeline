import type { ScoreComponent } from "@/lib/types";
import { formatScore } from "@/lib/format";
import { cn } from "@/lib/cn";

export const COMPONENT_COLORS = ["bg-indigo-600", "bg-sky-500", "bg-violet-500", "bg-teal-500", "bg-fuchsia-500", "bg-cyan-700", "bg-blue-400"];

export function componentColor(index: number): string {
  return COMPONENT_COLORS[index % COMPONENT_COLORS.length];
}

export function ContributionBar({ components, total }: { components: ScoreComponent[]; total: number }) {
  const remaining = Math.max(0, 100 - components.reduce((sum, c) => sum + c.contribution, 0));
  return (
    <div>
      <div className="flex h-4 w-full overflow-hidden rounded-full bg-slate-100" role="img" aria-label={`Score breakdown, total ${formatScore(total)} of 100`}>
        {components.map((c, i) => (
          <span
            key={c.name}
            title={`${c.label}: ${formatScore(c.contribution)} points`}
            className={cn("h-full border-r border-white last:border-r-0 first:rounded-l-full", componentColor(i))}
            style={{ width: `${Math.max(0, c.contribution)}%` }}
          />
        ))}
        {remaining > 0 && <span className="h-full rounded-r-full" style={{ width: `${remaining}%` }} aria-hidden />}
      </div>
      <ul className="mt-3 flex flex-wrap gap-x-4 gap-y-1.5 text-xs text-slate-600">
        {components.map((c, i) => (
          <li key={c.name} className="inline-flex items-center gap-1.5">
            <span className={`size-2.5 rounded-sm ${componentColor(i)}`} aria-hidden />
            {c.label}
            <span className="font-semibold text-slate-900 tabular-nums">{formatScore(c.contribution)}</span>
          </li>
        ))}
        {remaining > 0 && (
          <li className="inline-flex items-center gap-1.5">
            <span className="size-2.5 rounded-sm bg-slate-200" aria-hidden />
            Not earned
            <span className="font-semibold text-slate-900 tabular-nums">{formatScore(Number(remaining.toFixed(1)))}</span>
          </li>
        )}
      </ul>
    </div>
  );
}
