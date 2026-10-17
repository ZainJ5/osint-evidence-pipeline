import { EMAIL_PATTERN, isValidHandle, MAX_RESUME_CHARS } from "@/lib/domain";
import { SOURCES, type ClaimPreview, type ExtractorName, type Handles, type Source } from "@/lib/types";

export interface ResumeDraft {
  filename: string;
  text: string;
  name: string;
  email: string;
  detected: Handles;
  handles: Handles;
  visibleHandles: Source[];
  claims: ClaimPreview[];
  extractor: ExtractorName | null;
}

export interface JobDraft {
  title: string;
  text: string;
  skills: string[];
}

export function cleanHandles(handles: Handles): Handles {
  const result: Handles = {};
  for (const source of SOURCES) {
    const value = handles[source]?.trim();
    if (value) result[source] = value;
  }
  return result;
}

export function resumeIssues(resume: ResumeDraft | null): string[] {
  if (!resume) return ["Upload a resume or paste its text."];
  const issues: string[] = [];
  if (!resume.text.trim()) issues.push("The resume text is empty.");
  if (resume.text.length > MAX_RESUME_CHARS) {
    issues.push(`The resume text is longer than ${MAX_RESUME_CHARS.toLocaleString("en-US")} characters.`);
  }
  if (!resume.name.trim()) issues.push("Enter the candidate's name.");
  if (!EMAIL_PATTERN.test(resume.email.trim())) issues.push("Enter a valid email address.");
  const handles = cleanHandles(resume.handles);
  if (Object.keys(handles).length === 0) issues.push("Add at least one public profile handle.");
  for (const source of SOURCES) {
    const handle = handles[source];
    if (handle && !isValidHandle(source, handle)) issues.push(`Fix the ${source} handle.`);
  }
  return issues;
}

export function jobIssues(job: JobDraft): string[] {
  const issues: string[] = [];
  if (!job.title.trim()) issues.push("Enter a job title.");
  if (job.skills.length === 0) issues.push("Add at least one required skill.");
  if (job.skills.length > 50) issues.push("Use at most 50 required skills.");
  return issues;
}

export function resumeSkillSuggestions(claims: ClaimPreview[]): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  for (const claim of claims) {
    if (claim.kind !== "skill" || !claim.subject) continue;
    const key = claim.subject.toLowerCase();
    if (!seen.has(key)) {
      seen.add(key);
      out.push(claim.subject);
    }
  }
  return out;
}
