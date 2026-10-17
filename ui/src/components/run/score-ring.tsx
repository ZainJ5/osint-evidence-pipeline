import { formatScore } from "@/lib/format";

function bandColor(total: number): string {
  if (total >= 70) return "#059669";
  if (total >= 45) return "#d97706";
  return "#e11d48";
}

export function ScoreRing({ total, size = 168 }: { total: number; size?: number }) {
  const stroke = 14;
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const fraction = Math.max(0, Math.min(100, total)) / 100;
  return (
    <div className="relative inline-flex" style={{ width: size, height: size }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} role="img" aria-label={`Score ${formatScore(total)} out of 100`}>
        <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke="#e2e8f0" strokeWidth={stroke} />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={bandColor(total)}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={`${circumference * fraction} ${circumference}`}
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
          className="transition-[stroke-dasharray] duration-700"
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center" aria-hidden>
        <span className="text-4xl font-semibold tracking-tight text-slate-900 tabular-nums">{formatScore(total)}</span>
        <span className="text-xs font-medium text-slate-500">out of 100</span>
      </div>
    </div>
  );
}
