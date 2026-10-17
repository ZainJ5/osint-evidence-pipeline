"use client";

import { useState, type KeyboardEvent } from "react";
import { Plus, X } from "lucide-react";
import { cn } from "@/lib/cn";

interface TagInputProps {
  id: string;
  value: string[];
  onChange: (value: string[]) => void;
  suggestions?: string[];
  placeholder?: string;
  invalid?: boolean;
  describedBy?: string;
  max?: number;
}

function includesTag(list: string[], tag: string): boolean {
  return list.some((t) => t.toLowerCase() === tag.toLowerCase());
}

export function TagInput({ id, value, onChange, suggestions = [], placeholder, invalid, describedBy, max = 50 }: TagInputProps) {
  const [draft, setDraft] = useState("");

  function add(raw: string) {
    const tags = raw
      .split(",")
      .map((t) => t.trim())
      .filter(Boolean);
    const next = [...value];
    for (const tag of tags) {
      if (!includesTag(next, tag) && next.length < max) next.push(tag);
    }
    if (next.length !== value.length) onChange(next);
    setDraft("");
  }

  function onKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Enter" || event.key === ",") {
      event.preventDefault();
      if (draft.trim()) add(draft);
    } else if (event.key === "Backspace" && !draft && value.length) {
      onChange(value.slice(0, -1));
    }
  }

  const open = suggestions.filter((s) => !includesTag(value, s));

  return (
    <div>
      <div
        className={cn(
          "flex min-h-10 flex-wrap items-center gap-1.5 rounded-md border bg-white px-2 py-1.5 shadow-xs focus-within:border-indigo-500 focus-within:ring-2 focus-within:ring-indigo-500/20",
          invalid ? "border-rose-400" : "border-slate-300",
        )}
      >
        <ul className="contents" aria-label="Selected skills">
          {value.map((tag) => (
            <li key={tag} className="inline-flex items-center gap-1 rounded bg-indigo-50 py-0.5 pr-1 pl-2 text-xs font-medium text-indigo-800 ring-1 ring-indigo-200 ring-inset">
              {tag}
              <button
                type="button"
                onClick={() => onChange(value.filter((t) => t !== tag))}
                className="rounded p-0.5 text-indigo-500 hover:bg-indigo-100 hover:text-indigo-800"
                aria-label={`Remove ${tag}`}
              >
                <X className="size-3" aria-hidden />
              </button>
            </li>
          ))}
        </ul>
        <input
          id={id}
          value={draft}
          onChange={(event) => {
            const next = event.target.value;
            if (next.includes(",")) add(next);
            else setDraft(next);
          }}
          onKeyDown={onKeyDown}
          onBlur={() => draft.trim() && add(draft)}
          placeholder={value.length ? "" : placeholder}
          aria-invalid={invalid || undefined}
          aria-describedby={describedBy}
          className="min-w-32 flex-1 border-0 bg-transparent px-1 py-0.5 text-sm outline-none placeholder:text-slate-400 focus-visible:outline-none"
        />
      </div>
      {open.length > 0 && (
        <div className="mt-2 flex flex-wrap items-center gap-1.5">
          <span className="text-xs text-slate-500">From the resume:</span>
          {open.map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => add(s)}
              className="inline-flex items-center gap-1 rounded border border-slate-200 bg-white px-2 py-0.5 text-xs text-slate-700 hover:border-indigo-300 hover:text-indigo-700"
            >
              <Plus className="size-3" aria-hidden />
              {s}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
