"use client";

import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";
import { CheckCircle2, Info, X, XCircle } from "lucide-react";
import { cn } from "@/lib/cn";

type ToastTone = "success" | "error" | "info";

interface ToastItem {
  id: number;
  tone: ToastTone;
  title: string;
  description?: string;
}

interface ToastApi {
  show: (toast: Omit<ToastItem, "id">) => void;
}

const ToastContext = createContext<ToastApi | null>(null);

const ICONS: Record<ToastTone, ReactNode> = {
  success: <CheckCircle2 className="size-5 text-emerald-600" aria-hidden />,
  error: <XCircle className="size-5 text-rose-600" aria-hidden />,
  info: <Info className="size-5 text-indigo-600" aria-hidden />,
};

let nextId = 1;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const dismiss = useCallback((id: number) => setToasts((list) => list.filter((t) => t.id !== id)), []);

  const show = useCallback(
    (toast: Omit<ToastItem, "id">) => {
      const id = nextId++;
      setToasts((list) => [...list.slice(-3), { ...toast, id }]);
      setTimeout(() => dismiss(id), toast.tone === "error" ? 8000 : 5000);
    },
    [dismiss],
  );

  const api = useMemo(() => ({ show }), [show]);

  return (
    <ToastContext.Provider value={api}>
      {children}
      <div aria-live="polite" className="pointer-events-none fixed right-4 bottom-4 z-50 flex w-full max-w-sm flex-col gap-2">
        {toasts.map((toast) => (
          <div
            key={toast.id}
            role={toast.tone === "error" ? "alert" : "status"}
            className={cn("animate-slide-in pointer-events-auto flex items-start gap-3 rounded-lg border border-slate-200 bg-white p-4 shadow-lg")}
          >
            {ICONS[toast.tone]}
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium text-slate-900">{toast.title}</p>
              {toast.description && <p className="mt-0.5 text-sm text-slate-600">{toast.description}</p>}
            </div>
            <button
              type="button"
              onClick={() => dismiss(toast.id)}
              className="rounded p-0.5 text-slate-400 hover:text-slate-700"
              aria-label="Dismiss notification"
            >
              <X className="size-4" aria-hidden />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast(): ToastApi {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used inside ToastProvider");
  return ctx;
}
