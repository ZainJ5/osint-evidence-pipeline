import { cn } from "@/lib/cn";

interface MeterProps {
  value: number;
  label: string;
  className?: string;
  barClassName?: string;
  marker?: { at: number; label: string };
  size?: "sm" | "md";
}

function clamp(value: number): number {
  return Math.max(0, Math.min(1, Number.isFinite(value) ? value : 0));
}

export function Meter({ value, label, className, barClassName = "bg-indigo-600", marker, size = "md" }: MeterProps) {
  const pct = clamp(value) * 100;
  return (
    <div
      role="meter"
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={Math.round(pct)}
      className={cn("relative w-full rounded-full bg-slate-100", size === "sm" ? "h-1.5" : "h-2.5", className)}
    >
      <div className={cn("h-full rounded-full transition-[width] duration-500", barClassName)} style={{ width: `${pct}%` }} />
      {marker && (
        <div
          className="absolute -top-1 -bottom-1 w-0.5 rounded bg-slate-700"
          style={{ left: `calc(${clamp(marker.at) * 100}% - 1px)` }}
          title={marker.label}
          aria-hidden
        />
      )}
    </div>
  );
}

export function ProgressBar({ value, label }: { value: number | null; label: string }) {
  return (
    <div
      role="progressbar"
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={value === null ? undefined : Math.round(value * 100)}
      className="h-1.5 w-full overflow-hidden rounded-full bg-slate-100"
    >
      <div
        className={cn("h-full rounded-full bg-indigo-600 transition-[width] duration-300", value === null && "w-1/3 animate-pulse")}
        style={value === null ? undefined : { width: `${Math.round(clamp(value) * 100)}%` }}
      />
    </div>
  );
}
