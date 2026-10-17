"use client";

import { useState } from "react";
import { ClipboardPaste, FileText, RotateCcw, Upload } from "lucide-react";
import { ApiError, parseResume, toApiError } from "@/lib/api";
import { EMAIL_PATTERN, MAX_RESUME_CHARS } from "@/lib/domain";
import { formatNumber } from "@/lib/format";
import { SOURCES, type ParsedResume } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { ErrorPanel } from "@/components/ui/error-panel";
import { Field, Input, Textarea } from "@/components/ui/field";
import { ProgressBar } from "@/components/ui/meter";
import { ClaimsPreview } from "./claims-preview";
import { Dropzone, validateResumeFile } from "./dropzone";
import { HandlesEditor } from "./handles-editor";
import type { ResumeDraft } from "./wizard-state";

interface ResumeStepProps {
  resume: ResumeDraft | null;
  onChange: (resume: ResumeDraft | null) => void;
}

type UploadState = { kind: "idle" } | { kind: "uploading"; name: string; progress: number | null } | { kind: "error"; error: ApiError };

function draftFrom(parsed: ParsedResume): ResumeDraft {
  const handles = { ...parsed.handles };
  return {
    filename: parsed.filename,
    text: parsed.text,
    name: parsed.name ?? "",
    email: parsed.email ?? "",
    detected: { ...parsed.handles },
    handles,
    visibleHandles: SOURCES.filter((s) => handles[s]),
    claims: parsed.claims,
    extractor: parsed.extractor,
  };
}

export function ResumeStep({ resume, onChange }: ResumeStepProps) {
  const [upload, setUpload] = useState<UploadState>({ kind: "idle" });
  const [mode, setMode] = useState<"file" | "paste">("file");
  const [pasted, setPasted] = useState("");
  const [emailTouched, setEmailTouched] = useState(false);

  async function submit(file: File) {
    const invalid = validateResumeFile(file);
    if (invalid) {
      setUpload({ kind: "error", error: new ApiError(0, "UNSUPPORTED_FILE", invalid) });
      return;
    }
    setUpload({ kind: "uploading", name: file.name, progress: 0 });
    try {
      const parsed = await parseResume(file, (progress) =>
        setUpload({ kind: "uploading", name: file.name, progress: progress >= 1 ? null : progress }),
      );
      onChange(draftFrom(parsed));
      setUpload({ kind: "idle" });
    } catch (error) {
      setUpload({ kind: "error", error: toApiError(error) });
    }
  }

  function submitPasted() {
    const file = new File([pasted], "pasted-resume.txt", { type: "text/plain" });
    void submit(file);
  }

  if (!resume) {
    const busy = upload.kind === "uploading";
    return (
      <Card>
        <CardHeader
          title="Candidate resume"
          description="The system reads the resume, detects profile handles and lists the claims it will verify against public evidence."
        />
        <CardBody className="space-y-4">
          {mode === "file" ? (
            <Dropzone onFile={(file) => void submit(file)} disabled={busy} />
          ) : (
            <Field id="resume-paste" label="Resume text" hint={`${formatNumber(pasted.length)} / ${formatNumber(MAX_RESUME_CHARS)} characters`}>
              <Textarea
                id="resume-paste"
                rows={12}
                value={pasted}
                onChange={(event) => setPasted(event.target.value)}
                placeholder="Paste the full resume text here"
                aria-describedby="resume-paste-hint"
              />
            </Field>
          )}
          {busy && (
            <div className="rounded-md border border-slate-200 bg-white p-3" aria-live="polite">
              <div className="mb-2 flex items-center justify-between text-sm">
                <span className="font-medium text-slate-800">{upload.progress === null ? "Reading resume…" : `Uploading ${upload.name}…`}</span>
                {upload.progress !== null && <span className="text-slate-500 tabular-nums">{Math.round(upload.progress * 100)}%</span>}
              </div>
              <ProgressBar value={upload.progress} label="Resume upload progress" />
            </div>
          )}
          {upload.kind === "error" && <ErrorPanel error={upload.error} title="The resume could not be read" />}
          <div className="flex flex-wrap items-center justify-between gap-3">
            <button
              type="button"
              onClick={() => setMode(mode === "file" ? "paste" : "file")}
              className="inline-flex items-center gap-1.5 text-sm font-medium text-indigo-700 hover:underline"
            >
              {mode === "file" ? <ClipboardPaste className="size-4" aria-hidden /> : <Upload className="size-4" aria-hidden />}
              {mode === "file" ? "Paste resume text instead" : "Upload a file instead"}
            </button>
            {mode === "paste" && (
              <Button variant="primary" onClick={submitPasted} disabled={!pasted.trim() || busy} loading={busy}>
                Read resume text
              </Button>
            )}
          </div>
        </CardBody>
      </Card>
    );
  }

  const update = (patch: Partial<ResumeDraft>) => onChange({ ...resume, ...patch });
  const emailInvalid = emailTouched && !EMAIL_PATTERN.test(resume.email.trim());
  const tooLong = resume.text.length > MAX_RESUME_CHARS;

  return (
    <div className="grid gap-6 lg:grid-cols-5">
      <div className="space-y-6 lg:col-span-2">
        <Card>
          <CardHeader
            title="Candidate"
            description="Check what was detected. You can correct any field."
            actions={
              <Button size="sm" variant="ghost" onClick={() => onChange(null)}>
                <RotateCcw className="size-3.5" aria-hidden />
                Replace resume
              </Button>
            }
          />
          <CardBody className="space-y-4">
            <div className="flex items-center gap-2 rounded-md bg-slate-50 px-3 py-2 text-sm text-slate-700">
              <FileText className="size-4 shrink-0 text-slate-500" aria-hidden />
              <span className="truncate font-medium">{resume.filename}</span>
              <span className="ml-auto shrink-0 text-xs text-slate-500">{formatNumber(resume.text.length)} chars</span>
            </div>
            <Field id="candidate-name" label="Full name">
              <Input id="candidate-name" value={resume.name} onChange={(e) => update({ name: e.target.value })} autoComplete="off" />
            </Field>
            <Field id="candidate-email" label="Email" error={emailInvalid ? "Enter a valid email address." : null}>
              <Input
                id="candidate-email"
                type="email"
                value={resume.email}
                invalid={emailInvalid}
                onBlur={() => setEmailTouched(true)}
                onChange={(e) => update({ email: e.target.value })}
                autoComplete="off"
              />
            </Field>
          </CardBody>
        </Card>
        <Card>
          <CardHeader title="Public profiles" description="Evidence is collected only from these accounts." />
          <CardBody>
            <HandlesEditor
              handles={resume.handles}
              detected={resume.detected}
              visible={resume.visibleHandles}
              onChange={(handles) => update({ handles })}
              onVisibleChange={(visibleHandles) => update({ visibleHandles })}
            />
          </CardBody>
        </Card>
      </div>
      <div className="space-y-6 lg:col-span-3">
        <Card>
          <CardHeader
            title="Claims we found"
            description="Each claim will be verified against public evidence from the linked accounts."
            actions={resume.extractor && <span className="text-xs text-slate-500">Extractor: {resume.extractor}</span>}
          />
          <CardBody>
            <ClaimsPreview claims={resume.claims} />
          </CardBody>
        </Card>
        <Card>
          <CardHeader title="Extracted text" description="What the system read from the file." />
          <CardBody>
            {tooLong && (
              <p className="mb-3 rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-800">
                The text is {formatNumber(resume.text.length)} characters; the backend accepts at most {formatNumber(MAX_RESUME_CHARS)}.
              </p>
            )}
            <div
              tabIndex={0}
              aria-label="Extracted resume text"
              className="max-h-96 overflow-auto rounded-md border border-slate-200 bg-slate-50/60 p-4 text-sm leading-relaxed whitespace-pre-wrap text-slate-700"
            >
              {resume.text}
            </div>
          </CardBody>
        </Card>
      </div>
    </div>
  );
}
