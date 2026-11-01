"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, ArrowRight, Play } from "lucide-react";
import { startRun, toApiError, type ApiError } from "@/lib/api";
import { jobId as deriveJobId } from "@/lib/job";
import { Button } from "@/components/ui/button";
import { Card, CardBody } from "@/components/ui/card";
import { ErrorPanel } from "@/components/ui/error-panel";
import { useToast } from "@/components/ui/toast";
import { JobStep } from "./job-step";
import { ResumeStep } from "./resume-step";
import { ReviewStep } from "./review-step";
import { Stepper } from "./stepper";
import { cleanHandles, jobIssues, resumeIssues, resumeSkillSuggestions, type JobDraft, type ResumeDraft } from "./wizard-state";

const STEPS = [
  { title: "Resume", description: "Upload and check what was read" },
  { title: "Job requirement", description: "Title and required skills" },
  { title: "Review & run", description: "Confirm consent and start" },
];

export function NewAnalysisWizard() {
  const router = useRouter();
  const toast = useToast();
  const [step, setStep] = useState(0);
  const [resume, setResume] = useState<ResumeDraft | null>(null);
  const [job, setJob] = useState<JobDraft>({ title: "", text: "", skills: [] });
  const [consent, setConsent] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const [showIssues, setShowIssues] = useState(false);

  const issues = [resumeIssues(resume), jobIssues(job)];
  const maxReachable = issues[0].length ? 0 : issues[1].length ? 1 : 2;
  const suggestions = useMemo(() => resumeSkillSuggestions(resume?.claims ?? []), [resume]);
  const jobId = deriveJobId(job.title, job.text, job.skills);
  const current = step < 2 ? issues[step] : [];

  function next() {
    if (current.length) {
      setShowIssues(true);
      return;
    }
    setShowIssues(false);
    setStep(step + 1);
  }

  async function start() {
    if (!resume || !consent) return;
    setSubmitting(true);
    setError(null);
    try {
      const { run_id } = await startRun({
        candidate: {
          name: resume.name.trim(),
          email: resume.email.trim(),
          resume_text: resume.text,
          handles: cleanHandles(resume.handles),
        },
        job: { id: jobId, title: job.title.trim(), text: job.text.trim(), required_skills: job.skills },
      });
      toast.show({ tone: "success", title: "Analysis started", description: "Evidence collection is running." });
      router.push(`/runs/${run_id}`);
    } catch (err) {
      setError(toApiError(err));
      setSubmitting(false);
    }
  }

  return (
    <div>
      <Stepper
        steps={STEPS}
        current={step}
        maxReachable={maxReachable}
        onSelect={(i) => {
          setShowIssues(false);
          setStep(i);
        }}
      />

      {step === 0 && <ResumeStep resume={resume} onChange={setResume} />}
      {step === 1 && <JobStep job={job} onChange={setJob} suggestions={suggestions} />}
      {step === 2 && resume && (
        <div className="space-y-6">
          <ReviewStep resume={resume} job={job} jobId={jobId} onEdit={setStep} />
          <Card>
            <CardBody>
              <label className="flex cursor-pointer items-start gap-3">
                <input
                  type="checkbox"
                  checked={consent}
                  onChange={(e) => setConsent(e.target.checked)}
                  className="mt-0.5 size-4 rounded border-slate-300 accent-indigo-600"
                />
                <span className="text-sm">
                  <span className="font-medium text-slate-900">The candidate consented to analysis of their public profiles</span>
                  <span className="mt-0.5 block text-slate-500">
                    Only public data is collected. Raw responses are stored as snapshots and can be deleted with the candidate&apos;s data.
                  </span>
                </span>
              </label>
            </CardBody>
          </Card>
          {error && (
            <ErrorPanel
              error={error}
              title={error.code === "JOB_CONFLICT" ? "This job ID already exists with different content" : "The run could not be started"}
            />
          )}
        </div>
      )}

      {showIssues && current.length > 0 && (
        <div role="alert" className="mt-4 rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          <p className="font-medium">Complete this step to continue:</p>
          <ul className="mt-1 list-disc pl-5">
            {current.map((issue) => (
              <li key={issue}>{issue}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="mt-6 flex items-center justify-between border-t border-slate-200 pt-5">
        <Button variant="ghost" onClick={() => setStep(step - 1)} disabled={step === 0 || submitting}>
          <ArrowLeft className="size-4" aria-hidden />
          Back
        </Button>
        {step < 2 ? (
          <Button variant="primary" onClick={next} disabled={step === 0 && !resume}>
            Continue
            <ArrowRight className="size-4" aria-hidden />
          </Button>
        ) : (
          <Button variant="primary" size="lg" onClick={() => void start()} disabled={!consent} loading={submitting}>
            {!submitting && <Play className="size-4" aria-hidden />}
            Start analysis
          </Button>
        )}
      </div>
    </div>
  );
}
