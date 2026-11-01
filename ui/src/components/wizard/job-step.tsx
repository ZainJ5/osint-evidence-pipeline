"use client";

import { JOB_PRESETS, type JobPreset } from "@/lib/job";
import { cn } from "@/lib/cn";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { Field, Input, Textarea } from "@/components/ui/field";
import { TagInput } from "./tag-input";
import type { JobDraft } from "./wizard-state";

interface JobStepProps {
  job: JobDraft;
  onChange: (job: JobDraft) => void;
  suggestions: string[];
}

export function JobStep({ job, onChange, suggestions }: JobStepProps) {
  function applyPreset(preset: JobPreset) {
    onChange({ title: preset.title, text: preset.text, skills: [...preset.skills] });
  }

  return (
    <Card>
      <CardHeader title="Job requirement" description="Required skills are matched against evidence from the candidate's linked accounts." />
      <CardBody className="space-y-5">
        <div>
          <p className="mb-2 text-sm font-medium text-slate-700">Start from a preset</p>
          <div className="flex flex-wrap gap-2">
            {JOB_PRESETS.map((preset) => {
              const active = job.title === preset.title;
              return (
                <button
                  key={preset.title}
                  type="button"
                  aria-pressed={active}
                  onClick={() => applyPreset(preset)}
                  className={cn(
                    "rounded-md border px-3 py-1.5 text-sm font-medium transition-colors",
                    active
                      ? "border-indigo-300 bg-indigo-50 text-indigo-800"
                      : "border-slate-200 bg-white text-slate-700 hover:border-slate-300 hover:bg-slate-50",
                  )}
                >
                  {preset.title}
                </button>
              );
            })}
          </div>
        </div>
        <Field id="job-title" label="Title">
          <Input id="job-title" value={job.title} onChange={(e) => onChange({ ...job, title: e.target.value })} placeholder="e.g. Backend Engineer" />
        </Field>
        <Field id="job-text" label="Description" optional>
          <Textarea
            id="job-text"
            rows={4}
            value={job.text}
            onChange={(e) => onChange({ ...job, text: e.target.value })}
            placeholder="Responsibilities and context for this role"
          />
        </Field>
        <Field id="job-skills" label="Required skills" hint="Press Enter or comma to add a skill; Backspace removes the last one.">
          <TagInput
            id="job-skills"
            value={job.skills}
            onChange={(skills) => onChange({ ...job, skills })}
            suggestions={suggestions}
            placeholder="Python, Docker, PostgreSQL…"
            describedBy="job-skills-hint"
          />
        </Field>
      </CardBody>
    </Card>
  );
}
