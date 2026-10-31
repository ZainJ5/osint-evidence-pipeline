import type { ReactNode } from "react";
import { Pencil } from "lucide-react";
import { formatNumber, pluralize } from "@/lib/format";
import { SOURCES } from "@/lib/types";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { SourceBadge } from "@/components/status/source-badge";
import { cleanHandles, type JobDraft, type ResumeDraft } from "./wizard-state";

interface ReviewStepProps {
  resume: ResumeDraft;
  job: JobDraft;
  jobId: string;
  onEdit: (step: number) => void;
}

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="grid grid-cols-3 gap-3 py-2 text-sm">
      <dt className="text-slate-500">{label}</dt>
      <dd className="col-span-2 min-w-0 text-slate-900">{children}</dd>
    </div>
  );
}

function EditButton({ onClick, label }: { onClick: () => void; label: string }) {
  return (
    <Button size="sm" variant="ghost" onClick={onClick} aria-label={label}>
      <Pencil className="size-3.5" aria-hidden />
      Edit
    </Button>
  );
}

export function ReviewStep({ resume, job, jobId, onEdit }: ReviewStepProps) {
  const handles = cleanHandles(resume.handles);
  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <Card>
        <CardHeader title="Candidate" actions={<EditButton onClick={() => onEdit(0)} label="Edit candidate" />} />
        <CardBody>
          <dl className="divide-y divide-slate-100">
            <Row label="Name">{resume.name}</Row>
            <Row label="Email">{resume.email}</Row>
            <Row label="Resume">
              <span className="block truncate">{resume.filename}</span>
              <span className="text-xs text-slate-500">
                {formatNumber(resume.text.length)} characters · {pluralize(resume.claims.length, "claim")} detected
              </span>
            </Row>
            <Row label="Profiles">
              <ul className="space-y-1">
                {SOURCES.filter((s) => handles[s]).map((source) => (
                  <li key={source}>
                    <SourceBadge source={source} handle={handles[source]} />
                  </li>
                ))}
              </ul>
            </Row>
          </dl>
        </CardBody>
      </Card>
      <Card>
        <CardHeader title="Job requirement" actions={<EditButton onClick={() => onEdit(1)} label="Edit job requirement" />} />
        <CardBody>
          <dl className="divide-y divide-slate-100">
            <Row label="Title">{job.title}</Row>
            <Row label="Job ID">
              <code className="font-mono text-xs break-all text-slate-600">{jobId}</code>
            </Row>
            <Row label="Description">{job.text ? <span className="line-clamp-3">{job.text}</span> : <span className="text-slate-400">None</span>}</Row>
            <Row label="Required skills">
              <ul className="flex flex-wrap gap-1.5">
                {job.skills.map((skill) => (
                  <li key={skill} className="rounded bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-700">
                    {skill}
                  </li>
                ))}
              </ul>
            </Row>
          </dl>
        </CardBody>
      </Card>
    </div>
  );
}
