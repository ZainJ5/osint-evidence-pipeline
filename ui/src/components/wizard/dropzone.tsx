"use client";

import { useRef, useState, type DragEvent } from "react";
import { FileUp } from "lucide-react";
import { cn } from "@/lib/cn";
import { formatBytes } from "@/lib/format";

export const ACCEPTED_EXTENSIONS = [".pdf", ".docx", ".txt", ".md"];
export const MAX_FILE_BYTES = 5 * 1024 * 1024;

export function validateResumeFile(file: File): string | null {
  const name = file.name.toLowerCase();
  if (!ACCEPTED_EXTENSIONS.some((ext) => name.endsWith(ext))) {
    return `"${file.name}" is not supported. Use a PDF, DOCX, TXT or Markdown file.`;
  }
  if (file.size > MAX_FILE_BYTES) {
    return `"${file.name}" is ${formatBytes(file.size)}. The maximum size is 5 MB.`;
  }
  if (file.size === 0) return `"${file.name}" is empty.`;
  return null;
}

interface DropzoneProps {
  onFile: (file: File) => void;
  disabled?: boolean;
}

export function Dropzone({ onFile, disabled }: DropzoneProps) {
  const input = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  function onDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setDragging(false);
    if (disabled) return;
    const file = event.dataTransfer.files[0];
    if (file) onFile(file);
  }

  return (
    <div
      onDragOver={(event) => {
        event.preventDefault();
        if (!disabled) setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={onDrop}
      onClick={(event) => {
        if (!disabled && event.target === event.currentTarget) input.current?.click();
      }}
      className={cn(
        "relative flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed px-6 py-14 text-center transition-colors",
        dragging ? "border-indigo-500 bg-indigo-50" : "border-slate-300 bg-slate-50/60 hover:border-slate-400",
        disabled && "opacity-60",
      )}
    >
      <div className="mb-4 flex size-12 items-center justify-center rounded-full bg-white text-indigo-600 shadow-sm ring-1 ring-slate-200" aria-hidden>
        <FileUp className="size-5" />
      </div>
      <p className="text-sm font-medium text-slate-900">
        Drop the resume here, or{" "}
        <button
          type="button"
          disabled={disabled}
          onClick={() => input.current?.click()}
          className="font-semibold text-indigo-700 underline-offset-2 hover:underline"
        >
          browse files
        </button>
      </p>
      <p className="mt-1 text-xs text-slate-500">PDF, DOCX, TXT or Markdown · up to 5 MB</p>
      <input
        ref={input}
        type="file"
        className="sr-only"
        tabIndex={-1}
        aria-label="Resume file"
        accept={ACCEPTED_EXTENSIONS.join(",")}
        onChange={(event) => {
          const file = event.target.files?.[0];
          if (file) onFile(file);
          event.target.value = "";
        }}
      />
    </div>
  );
}
