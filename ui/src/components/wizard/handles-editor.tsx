"use client";

import { Plus, X } from "lucide-react";
import { HANDLE_RULES, isValidHandle, normalizeHandle, SOURCE_LABEL } from "@/lib/domain";
import { SOURCES, type Handles, type Source } from "@/lib/types";
import { Field, Input } from "@/components/ui/field";
import { SourceMark } from "@/components/status/source-badge";

interface HandlesEditorProps {
  handles: Handles;
  detected: Handles;
  visible: Source[];
  onChange: (handles: Handles) => void;
  onVisibleChange: (visible: Source[]) => void;
}

export function handleError(source: Source, handle: string | undefined): string | null {
  if (!handle) return null;
  return isValidHandle(source, handle) ? null : `Not a valid ${SOURCE_LABEL[source]} handle. ${HANDLE_RULES[source].hint}`;
}

export function HandlesEditor({ handles, detected, visible, onChange, onVisibleChange }: HandlesEditorProps) {
  const hidden = SOURCES.filter((s) => !visible.includes(s));

  function update(source: Source, value: string) {
    onChange({ ...handles, [source]: value });
  }

  function remove(source: Source) {
    const next = { ...handles };
    delete next[source];
    onChange(next);
    onVisibleChange(visible.filter((s) => s !== source));
  }

  return (
    <div className="space-y-4">
      {visible.length === 0 && (
        <p className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
          No public profiles were found in the resume. Add at least one handle so evidence can be collected.
        </p>
      )}
      {visible.map((source) => {
        const id = `handle-${source}`;
        const value = handles[source] ?? "";
        const error = handleError(source, value);
        return (
          <Field
            key={source}
            id={id}
            label={
              <span className="inline-flex items-center gap-2">
                <SourceMark source={source} />
                {SOURCE_LABEL[source]}
                {detected[source] && detected[source] === value && (
                  <span className="text-xs font-normal text-slate-400">Detected in resume</span>
                )}
              </span>
            }
            hint={HANDLE_RULES[source].hint}
            error={error}
          >
            <div className="flex gap-2">
              <Input
                id={id}
                value={value}
                invalid={Boolean(error)}
                placeholder={HANDLE_RULES[source].example}
                autoComplete="off"
                spellCheck={false}
                aria-describedby={error ? `${id}-error` : `${id}-hint`}
                onChange={(event) => update(source, event.target.value)}
                onBlur={(event) => update(source, normalizeHandle(source, event.target.value))}
              />
              <button
                type="button"
                onClick={() => remove(source)}
                className="rounded-md px-2 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
                aria-label={`Remove ${SOURCE_LABEL[source]} handle`}
              >
                <X className="size-4" aria-hidden />
              </button>
            </div>
          </Field>
        );
      })}
      {hidden.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {hidden.map((source) => (
            <button
              key={source}
              type="button"
              onClick={() => onVisibleChange([...visible, source])}
              className="inline-flex items-center gap-1.5 rounded-md border border-dashed border-slate-300 px-2.5 py-1.5 text-xs font-medium text-slate-600 hover:border-indigo-400 hover:text-indigo-700"
            >
              <Plus className="size-3.5" aria-hidden />
              Add {SOURCE_LABEL[source]} handle
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
