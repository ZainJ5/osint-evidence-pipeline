import { DEMO_MODE } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { HealthIndicator } from "./health-indicator";

export function TopBar() {
  return (
    <header className="sticky top-0 z-20 flex h-14 shrink-0 items-center justify-between gap-4 border-b border-slate-200 bg-white/90 px-4 backdrop-blur md:px-8">
      <p className="truncate text-sm text-slate-500">Candidate evidence verification</p>
      <div className="flex items-center gap-3">
        {DEMO_MODE && <Badge tone="partial">Demo data</Badge>}
        <HealthIndicator />
      </div>
    </header>
  );
}
