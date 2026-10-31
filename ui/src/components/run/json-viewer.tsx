"use client";

import { useMemo, useState } from "react";
import { ChevronRight } from "lucide-react";
import type { JsonValue } from "@/lib/types";
import { cn } from "@/lib/cn";
import { Button } from "@/components/ui/button";

const CHUNK = 100;
const MAX_STRING = 400;
const MAX_LINES = 600;

function Primitive({ value }: { value: JsonValue }) {
  const [full, setFull] = useState(false);
  if (value === null) return <span className="text-slate-400">null</span>;
  if (typeof value === "boolean") return <span className="text-violet-700">{String(value)}</span>;
  if (typeof value === "number") return <span className="text-sky-700">{value}</span>;
  if (typeof value === "string") {
    const long = value.length > MAX_STRING;
    return (
      <span className="break-all text-emerald-800">
        &quot;{long && !full ? `${value.slice(0, MAX_STRING)}…` : value}&quot;
        {long && (
          <button type="button" onClick={() => setFull(!full)} className="ml-1 font-sans text-[11px] text-indigo-700 hover:underline">
            {full ? "less" : `${value.length - MAX_STRING} more chars`}
          </button>
        )}
      </span>
    );
  }
  return null;
}

function Node({ name, value, depth, defaultDepth }: { name: string | null; value: JsonValue; depth: number; defaultDepth: number }) {
  const isArray = Array.isArray(value);
  const isObject = value !== null && typeof value === "object";
  const [open, setOpen] = useState(depth < defaultDepth);
  const [shown, setShown] = useState(CHUNK);

  const label = name !== null && <span className="text-slate-800">{name}: </span>;

  if (!isObject) {
    return (
      <div className="py-px pl-5">
        {label}
        <Primitive value={value} />
      </div>
    );
  }

  const entries: [string, JsonValue][] = isArray ? value.map((v, i) => [String(i), v]) : Object.entries(value);
  const summary = isArray ? `Array(${entries.length})` : `{${entries.length} key${entries.length === 1 ? "" : "s"}}`;

  return (
    <div>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        aria-expanded={open}
        className="flex items-center gap-0.5 rounded py-px text-left hover:bg-slate-100"
      >
        <ChevronRight className={cn("size-4 shrink-0 text-slate-400 transition-transform", open && "rotate-90")} aria-hidden />
        {label}
        <span className="text-slate-500">{summary}</span>
      </button>
      {open && (
        <div className="ml-2 border-l border-slate-200 pl-2">
          {entries.slice(0, shown).map(([key, child]) => (
            <Node key={key} name={isArray ? `[${key}]` : key} value={child} depth={depth + 1} defaultDepth={defaultDepth} />
          ))}
          {entries.length > shown && (
            <button
              type="button"
              onClick={() => setShown(shown + CHUNK)}
              className="my-1 ml-5 font-sans text-xs font-medium text-indigo-700 hover:underline"
            >
              Show {Math.min(CHUNK, entries.length - shown)} more of {entries.length - shown} remaining
            </button>
          )}
        </div>
      )}
    </div>
  );
}

function RawView({ value }: { value: JsonValue }) {
  const [query, setQuery] = useState("");
  const lines = useMemo(() => JSON.stringify(value, null, 2).split("\n"), [value]);
  const matches = useMemo(() => {
    const q = query.trim().toLowerCase();
    const all = lines.map((text, i) => ({ text, n: i + 1 }));
    return q ? all.filter((l) => l.text.toLowerCase().includes(q)) : all;
  }, [lines, query]);
  const [limit, setLimit] = useState(MAX_LINES);
  return (
    <div>
      <div className="mb-2 flex items-center gap-3">
        <label htmlFor="raw-search" className="sr-only">
          Search raw JSON
        </label>
        <input
          id="raw-search"
          type="search"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setLimit(MAX_LINES);
          }}
          placeholder="Filter lines…"
          className="h-8 flex-1 rounded-md border border-slate-300 px-2.5 text-sm placeholder:text-slate-400 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 focus:outline-none"
        />
        <span className="text-xs text-slate-500 tabular-nums">
          {query ? `${matches.length} matching lines` : `${lines.length} lines`}
        </span>
      </div>
      <pre className="overflow-auto rounded-md bg-slate-950 p-3 font-mono text-xs leading-5 text-slate-100">
        {matches.slice(0, limit).map((line) => (
          <div key={line.n} className="flex">
            <span className="mr-3 w-10 shrink-0 text-right text-slate-500 select-none">{line.n}</span>
            <span className="whitespace-pre">{line.text}</span>
          </div>
        ))}
      </pre>
      {matches.length > limit && (
        <button type="button" onClick={() => setLimit(limit + MAX_LINES)} className="mt-2 text-xs font-medium text-indigo-700 hover:underline">
          Show {Math.min(MAX_LINES, matches.length - limit)} more lines
        </button>
      )}
    </div>
  );
}

export function JsonViewer({ value }: { value: JsonValue }) {
  const [mode, setMode] = useState<"tree" | "raw">("tree");
  const [depth, setDepth] = useState(1);
  const [version, setVersion] = useState(0);

  function expand(next: number) {
    setDepth(next);
    setVersion((v) => v + 1);
  }

  return (
    <div>
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <div className="inline-flex rounded-md border border-slate-300 p-0.5" role="group" aria-label="View mode">
          {(["tree", "raw"] as const).map((m) => (
            <button
              key={m}
              type="button"
              aria-pressed={mode === m}
              onClick={() => setMode(m)}
              className={cn("rounded px-2.5 py-1 text-xs font-medium", mode === m ? "bg-slate-900 text-white" : "text-slate-600 hover:bg-slate-100")}
            >
              {m === "tree" ? "Tree" : "Raw"}
            </button>
          ))}
        </div>
        {mode === "tree" && (
          <>
            <Button size="sm" variant="ghost" onClick={() => expand(4)}>
              Expand levels
            </Button>
            <Button size="sm" variant="ghost" onClick={() => expand(1)}>
              Collapse all
            </Button>
          </>
        )}
      </div>
      {mode === "tree" ? (
        <div className="overflow-auto rounded-md border border-slate-200 bg-white p-3 font-mono text-xs leading-5">
          <Node key={version} name={null} value={value} depth={0} defaultDepth={depth} />
        </div>
      ) : (
        <RawView value={value} />
      )}
    </div>
  );
}
