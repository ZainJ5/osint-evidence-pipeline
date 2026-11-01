export type Source = "github" | "codeforces" | "leetcode";

export const SOURCES: Source[] = ["github", "codeforces", "leetcode"];

export type Handles = Partial<Record<Source, string>>;

export type ClaimKind = "skill" | "rating" | "solved" | (string & {});

export interface ClaimPreview {
  text: string;
  kind: ClaimKind;
  subject: string | null;
  years: number | null;
  rating: number | null;
  solved: number | null;
}

export type ExtractorName = "rule-based" | "claude";

export interface ParsedResume {
  filename: string;
  text: string;
  name: string | null;
  email: string | null;
  handles: Handles;
  links: string[];
  claims: ClaimPreview[];
  extractor: ExtractorName;
}

export interface CandidateInput {
  name: string;
  email: string;
  resume_text: string;
  handles: Handles;
}

export interface JobInput {
  id: string;
  title: string;
  text: string;
  required_skills: string[];
}

export interface RunBody {
  candidate: CandidateInput;
  job: JobInput;
}

export interface StartRunResponse {
  run_id: string;
}

export type RunStatus = "running" | "partial" | "done" | "failed";

export interface RunSummary {
  run_id: string;
  candidate_id: string;
  candidate_name: string | null;
  job_id: string;
  job_title: string;
  status: RunStatus;
  started_at: string;
  finished_at: string | null;
  total: number | null;
  sources: Source[];
}

export type Stage = "collect" | "freeze" | "extract" | "resolve" | "match" | "verify" | "score";

export const STAGES: Stage[] = ["collect", "freeze", "extract", "resolve", "match", "verify", "score"];

export interface Failure {
  source: string;
  code: string;
  message?: string;
}

export interface RunInfo {
  id: string;
  status: RunStatus;
  stage: Stage | "finished";
  started_at: string;
  finished_at: string | null;
  failures: Failure[];
  config: Record<string, unknown>;
}

export interface ProgressEvent {
  stage: Stage;
  status: "started" | "done";
  at: string;
  detail: Record<string, unknown>;
}

export interface CandidateDetail {
  id: string;
  name: string | null;
  email_masked: string | null;
  handles: Handles;
  resume_text: string;
}

export interface Account {
  source: Source;
  handle: string;
  profile_url: string | null;
  confidence: number;
  linked: boolean;
  rationale: string[];
}

export interface Snapshot {
  id: string;
  source: Source;
  handle: string;
  endpoint: string;
  sha256: string;
  size: number;
  fetched_at: string;
}

export type EvidenceKind = "skill" | "project" | "contribution" | "achievement";

export type EvidenceValue = Record<string, unknown>;

export interface EvidenceNode {
  id: string;
  snapshot_id: string;
  source: Source;
  handle: string;
  kind: EvidenceKind;
  value: EvidenceValue;
  locator: string;
  linked: boolean;
}

export type VerdictLabel = "supported" | "partially_supported" | "unsupported";

export interface Verdict {
  label: VerdictLabel;
  rationale: string;
  evidence_node_ids: string[];
}

export interface Claim extends ClaimPreview {
  id: string;
  verdict: Verdict | null;
}

export interface Match {
  skill: string;
  covered: boolean;
  similarity: number;
  node_ids: string[];
}

export interface ScoreComponent {
  name: string;
  label: string;
  weight: number;
  value: number;
  contribution: number;
  formula: string;
  evidence_node_ids: string[];
}

export interface Report {
  total: number;
  components: ScoreComponent[];
}

export interface RunDetail {
  run: RunInfo;
  progress: ProgressEvent[];
  candidate: CandidateDetail;
  job: JobInput;
  accounts: Account[];
  snapshots: Snapshot[];
  evidence: EvidenceNode[];
  claims: Claim[];
  matches: Match[];
  coverage: number | null;
  report: Report | null;
}

export type JsonValue = string | number | boolean | null | JsonValue[] | { [key: string]: JsonValue };

export interface RawSnapshot {
  snapshot: Snapshot;
  verified: boolean;
  payload: JsonValue;
}

export interface ReplayResult {
  report: Report;
  evidence_identical: boolean;
  score_identical: boolean;
}

export interface Health {
  status: string;
  storage: string;
  extractor: string;
}

export interface ApiErrorBody {
  code: string;
  message: string;
}
