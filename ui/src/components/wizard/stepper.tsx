import { Check } from "lucide-react";
import { cn } from "@/lib/cn";

interface StepperProps {
  steps: { title: string; description: string }[];
  current: number;
  onSelect: (index: number) => void;
  maxReachable: number;
}

export function Stepper({ steps, current, onSelect, maxReachable }: StepperProps) {
  return (
    <nav aria-label="Progress" className="mb-6">
      <ol className="grid grid-cols-3 gap-3">
        {steps.map((step, i) => {
          const done = i < current;
          const active = i === current;
          const reachable = i <= maxReachable;
          return (
            <li key={step.title}>
              <button
                type="button"
                disabled={!reachable}
                onClick={() => onSelect(i)}
                aria-current={active ? "step" : undefined}
                className={cn(
                  "flex w-full items-start gap-3 border-t-4 pt-3 text-left transition-colors disabled:cursor-not-allowed",
                  active ? "border-indigo-600" : done ? "border-indigo-300 hover:border-indigo-400" : "border-slate-200",
                )}
              >
                <span
                  className={cn(
                    "flex size-6 shrink-0 items-center justify-center rounded-full text-xs font-semibold",
                    active ? "bg-indigo-600 text-white" : done ? "bg-indigo-100 text-indigo-700" : "bg-slate-100 text-slate-500",
                  )}
                  aria-hidden
                >
                  {done ? <Check className="size-3.5" /> : i + 1}
                </span>
                <span className="min-w-0">
                  <span className={cn("block text-sm font-medium", active ? "text-indigo-700" : "text-slate-800")}>
                    <span className="sr-only">Step {i + 1}: </span>
                    {step.title}
                  </span>
                  <span className="hidden text-xs text-slate-500 sm:block">{step.description}</span>
                </span>
              </button>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
