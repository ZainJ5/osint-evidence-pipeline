import { ApiError } from "./api";
import type {
  Account,
  Claim,
  EvidenceNode,
  Failure,
  Health,
  JsonValue,
  ParsedResume,
  ProgressEvent,
  RawSnapshot,
  ReplayResult,
  Report,
  RunBody,
  RunDetail,
  RunSummary,
  Snapshot,
  StartRunResponse,
} from "./types";
import { STAGES } from "./types";

const RESUME = `Jane Doe
jane.doe@example.org · github.com/janedoe · leetcode.com/u/janedoe

Summary
Backend engineer with 4 years of Python and 2 years of Go, building data-heavy services.
Competitive programmer: Codeforces rating 1650, 500 problems solved on LeetCode.

Experience
Acme Analytics — Backend Engineer (2021–present)
- Built ingestion services in Python and PostgreSQL handling 2M events per day.
- Containerised the platform with Docker and introduced CI pipelines.

Skills
Python, Go, PostgreSQL, Docker, Rust
`;

const T0 = "2026-11-18T09:12:04Z";

function iso(base: string, plusSeconds: number): string {
  return new Date(new Date(base).getTime() + plusSeconds * 1000).toISOString();
}

function snapshots(runId: string): Snapshot[] {
  const rows: [string, Snapshot["source"], string, number][] = [
    ["github/users", "github", "janedoe", 1432],
    ["github/repos", "github", "janedoe", 18234],
    ["github/languages", "github", "janedoe", 212],
    ["github/commits", "github", "janedoe", 40211],
    ["codeforces/user.info", "codeforces", "jane_d", 611],
    ["codeforces/user.status", "codeforces", "jane_d", 96410],
    ["leetcode/profile", "leetcode", "janedoe", 2210],
    ["leetcode/profile", "leetcode", "jdoe-alt", 1904],
  ];
  return rows.map(([endpoint, source, handle, size], i) => ({
    id: `${runId}-snap-${i + 1}`,
    source,
    handle,
    endpoint,
    size,
    sha256: `9f2c${i}a81e4b7d03c5f6e2a19b8d4c7e0f3a6b5d2c1e9f8a7b6c5d4e3f2a1b0c9d8e7${i}`.slice(0, 64),
    fetched_at: iso(T0, 1 + i * 0.4),
  }));
}

function evidence(runId: string): EvidenceNode[] {
  const s = (n: number) => `${runId}-snap-${n}`;
  const node = (
    id: string,
    snap: number,
    source: EvidenceNode["source"],
    handle: string,
    kind: EvidenceNode["kind"],
    value: Record<string, unknown>,
    locator: string,
    linked = true,
  ): EvidenceNode => ({ id: `${runId}-ev-${id}`, snapshot_id: s(snap), source, handle, kind, value, locator, linked });
  return [
    node("py", 3, "github", "janedoe", "skill", { name: "Python", first_seen: "2020-02-11T10:00:00Z", last_seen: "2026-10-30T18:21:00Z", evidence: "repo language", repo: "ingest-service", bytes: 412330 }, "$['Python']"),
    node("go", 3, "github", "janedoe", "skill", { name: "Go", first_seen: "2023-05-02T08:00:00Z", last_seen: "2026-09-14T12:00:00Z", evidence: "repo language", repo: "edge-proxy", bytes: 90211 }, "$['Go']"),
    node("docker", 3, "github", "janedoe", "skill", { name: "Dockerfile", first_seen: "2021-06-01T08:00:00Z", last_seen: "2026-10-30T18:21:00Z", evidence: "repo language", repo: "ingest-service", bytes: 1203 }, "$['Dockerfile']"),
    node("p1", 2, "github", "janedoe", "project", { name: "ingest-service", description: "Event ingestion with PostgreSQL", language: "Python", stars: 42, url: "https://github.com/janedoe/ingest-service", created_at: "2020-02-11T10:00:00Z", pushed_at: "2026-10-30T18:21:00Z" }, "$[0]"),
    node("p2", 2, "github", "janedoe", "project", { name: "edge-proxy", description: "Small reverse proxy", language: "Go", stars: 7, url: "https://github.com/janedoe/edge-proxy", created_at: "2023-05-02T08:00:00Z", pushed_at: "2026-09-14T12:00:00Z" }, "$[3]"),
    node("c1", 4, "github", "janedoe", "contribution", { repo: "ingest-service", commits: 318, first: "2020-02-11T10:00:00Z", last: "2026-10-30T18:21:00Z" }, "$"),
    node("cf1", 5, "codeforces", "jane_d", "achievement", { platform: "codeforces", rating: 1588, max_rating: 1662, rank: "specialist", solved: null }, "$.result[0]"),
    node("cf2", 6, "codeforces", "jane_d", "skill", { name: "GNU C++17", first_seen: "2019-03-02T14:00:00Z", last_seen: "2026-08-01T16:00:00Z", evidence: "accepted submissions", submissions: 311 }, "$.result[0].programmingLanguage"),
    node("cf3", 6, "codeforces", "jane_d", "achievement", { platform: "codeforces", solved: 287, rating: null, max_rating: null, rank: null }, "$.result"),
    node("lc1", 7, "leetcode", "janedoe", "achievement", { platform: "leetcode", solved: 412, rating: 1820, max_rating: 1820 }, "$.data.matchedUser.submitStatsGlobal"),
    node("lc2", 7, "leetcode", "janedoe", "skill", { name: "Python3", first_seen: null, last_seen: null, evidence: "leetcode problems solved", solved: 301 }, "$.data.matchedUser.languageProblemCount[0]"),
    node("lc3", 8, "leetcode", "jdoe-alt", "achievement", { platform: "leetcode", solved: 35, rating: null, max_rating: null }, "$.data.matchedUser.submitStatsGlobal", false),
  ];
}

function accounts(): Account[] {
  return [
    { source: "github", handle: "janedoe", profile_url: "https://github.com/janedoe", confidence: 0.95, linked: true, rationale: ["cross_link (1.00) on resume~github:janedoe: resume links to github.com/janedoe", "name_match (0.92) on resume~github:janedoe: 'Jane Doe' ≈ 'Jane Doe'"] },
    { source: "codeforces", handle: "jane_d", profile_url: "https://codeforces.com/profile/jane_d", confidence: 0.71, linked: true, rationale: ["handle_similarity (0.71) on github:janedoe~codeforces:jane_d: handles share prefix 'jane'", "name_match (0.80) on resume~codeforces:jane_d: first name matches"] },
    { source: "leetcode", handle: "janedoe", profile_url: "https://leetcode.com/u/janedoe/", confidence: 0.88, linked: true, rationale: ["cross_link (1.00) on resume~leetcode:janedoe: resume links to leetcode.com/u/janedoe"] },
    { source: "leetcode", handle: "jdoe-alt", profile_url: "https://leetcode.com/u/jdoe-alt/", confidence: 0.31, linked: false, rationale: ["handle_similarity (0.31) on github:janedoe~leetcode:jdoe-alt: weak handle overlap"] },
  ];
}

function claims(runId: string): Claim[] {
  const e = (id: string) => `${runId}-ev-${id}`;
  return [
    { id: `${runId}-cl-1`, text: "4 years of Python", kind: "skill", subject: "Python", years: 4, rating: null, solved: null, verdict: { label: "supported", rationale: "Python evidence spans 6.7 years on GitHub (first seen Feb 2020), covering the claimed 4 years.", evidence_node_ids: [e("py"), e("p1"), e("lc2")] } },
    { id: `${runId}-cl-2`, text: "2 years of Go", kind: "skill", subject: "Go", years: 2, rating: null, solved: null, verdict: { label: "supported", rationale: "Go evidence spans 3.4 years on GitHub, covering the claimed 2 years.", evidence_node_ids: [e("go"), e("p2")] } },
    { id: `${runId}-cl-3`, text: "Codeforces rating 1650", kind: "rating", subject: "codeforces", years: null, rating: 1650, solved: null, verdict: { label: "partially_supported", rationale: "Current rating is 1588 (max 1662): the claim matches the peak rating but not the current one.", evidence_node_ids: [e("cf1")] } },
    { id: `${runId}-cl-4`, text: "500 problems solved on LeetCode", kind: "solved", subject: "leetcode", years: null, rating: null, solved: 500, verdict: { label: "partially_supported", rationale: "Linked LeetCode account shows 412 solved, 82% of the claimed 500. The unlinked account was not counted.", evidence_node_ids: [e("lc1")] } },
    { id: `${runId}-cl-5`, text: "Rust", kind: "skill", subject: "Rust", years: null, rating: null, solved: null, verdict: { label: "unsupported", rationale: "No Rust evidence was found in any linked account.", evidence_node_ids: [] } },
  ];
}

function report(runId: string): Report {
  const e = (id: string) => `${runId}-ev-${id}`;
  return {
    total: 72.5,
    components: [
      { name: "verified_skills", label: "Verified resume claims", weight: 0.35, value: 0.6, contribution: 21.0, formula: "mean of claim verdicts (supported = 1, partially supported = 0.5, unsupported = 0)", evidence_node_ids: [e("py"), e("go"), e("cf1"), e("lc1")] },
      { name: "requirement_coverage", label: "Requirement coverage", weight: 0.35, value: 0.8, contribution: 28.0, formula: "covered required skills / required skills", evidence_node_ids: [e("py"), e("go"), e("docker")] },
      { name: "activity", label: "Recent activity", weight: 0.15, value: 0.9, contribution: 13.5, formula: "share of linked sources with activity in the last 12 months", evidence_node_ids: [e("c1")] },
      { name: "competitive", label: "Competitive programming", weight: 0.15, value: 0.6667, contribution: 10.0, formula: "min(1, max rating / 2400) averaged over linked platforms", evidence_node_ids: [e("cf1"), e("lc1")] },
    ],
  };
}

function progressEvents(count: number, start: string): ProgressEvent[] {
  const details: Record<string, Record<string, unknown>> = {
    collect: { fetches: 8, sources: 3 },
    freeze: { snapshots: 8 },
    extract: { evidence: 12 },
    resolve: { accounts: 4, linked: 3 },
    match: { required: 5, covered: 4 },
    verify: { claims: 5, supported: 2 },
    score: { total: 72.5 },
  };
  const events: ProgressEvent[] = [];
  STAGES.forEach((stage, i) => {
    if (i * 2 >= count) return;
    events.push({ stage, status: "started", at: iso(start, i * 1.2), detail: {} });
    if (i * 2 + 1 < count) events.push({ stage, status: "done", at: iso(start, i * 1.2 + 1.1), detail: details[stage] });
  });
  return events;
}

function detail(runId: string, overrides: Partial<{ name: string; title: string; skills: string[]; failures: Failure[]; status: RunDetail["run"]["status"] }> = {}): RunDetail {
  const failures = overrides.failures ?? [];
  const droppedGithub = failures.some((f) => f.source === "github");
  return {
    run: { id: runId, status: overrides.status ?? "done", stage: "finished", started_at: T0, finished_at: iso(T0, 8.4), failures, config: { link_threshold: 0.5, max_repos: 50, max_requests_per_source: 2 } },
    progress: progressEvents(14, T0),
    candidate: { id: `${runId}-cand`, name: overrides.name ?? "Jane Doe", email_masked: "j***@example.org", handles: { github: "janedoe", codeforces: "jane_d", leetcode: "janedoe" }, resume_text: RESUME },
    job: { id: "backend-engineer-3f2a91c0", title: overrides.title ?? "Backend Engineer", text: "Design and operate backend services and APIs.", required_skills: overrides.skills ?? ["Python", "Go", "PostgreSQL", "Docker", "Kubernetes"] },
    accounts: accounts(),
    snapshots: snapshots(runId).filter((s) => !(droppedGithub && s.source === "github")),
    evidence: evidence(runId).filter((n) => !(droppedGithub && n.source === "github")),
    claims: claims(runId),
    matches: [
      { skill: "python", covered: true, similarity: 1.0, node_ids: [`${runId}-ev-py`, `${runId}-ev-lc2`] },
      { skill: "go", covered: true, similarity: 1.0, node_ids: [`${runId}-ev-go`] },
      { skill: "postgresql", covered: true, similarity: 0.82, node_ids: [`${runId}-ev-p1`] },
      { skill: "docker", covered: true, similarity: 0.91, node_ids: [`${runId}-ev-docker`] },
      { skill: "kubernetes", covered: false, similarity: 0.0, node_ids: [] },
    ],
    coverage: 0.8,
    report: report(runId),
  };
}

interface StartedRun {
  body: RunBody;
  startedAt: number;
}

const started = new Map<string, StartedRun>();
const deleted = new Set<string>();

const STATIC_RUNS: Record<string, () => RunDetail> = {
  "demo-run-0001": () => detail("demo-run-0001"),
  "demo-run-0002": () =>
    detail("demo-run-0002", {
      name: "Arjun Mehta",
      title: "Competitive Programmer",
      skills: ["C++", "Python", "Algorithms"],
      status: "partial",
      failures: [{ source: "github", code: "HTTP_403" }],
    }),
};

function delay<T>(value: T, ms = 250): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(value), ms));
}

export function mockHealth(): Promise<Health> {
  return delay({ status: "ok", storage: "memory", extractor: "rule-based" }, 100);
}

function summary(d: RunDetail): RunSummary {
  return {
    run_id: d.run.id,
    candidate_id: d.candidate.id,
    candidate_name: d.candidate.name,
    job_id: d.job.id,
    job_title: d.job.title,
    status: d.run.status,
    started_at: d.run.started_at,
    finished_at: d.run.finished_at,
    total: d.report?.total ?? null,
    sources: [...new Set(d.snapshots.map((s) => s.source))],
  };
}

export async function mockListRuns(): Promise<RunSummary[]> {
  const dynamic = [...started.keys()].map((id) => summary(buildStarted(id)));
  const fixed = Object.values(STATIC_RUNS).map((make) => summary(make()));
  return delay([...dynamic.reverse(), ...fixed].filter((r) => !deleted.has(r.candidate_id)));
}

const STAGE_MS = 1300;

function buildStarted(runId: string): RunDetail {
  const entry = started.get(runId);
  if (!entry) throw new ApiError(404, "RUN_NOT_FOUND", `run ${runId} not found`);
  const startIso = new Date(entry.startedAt).toISOString();
  const elapsed = Date.now() - entry.startedAt;
  const events = Math.min(14, Math.floor(elapsed / (STAGE_MS / 2)) + 1);
  const base = detail(runId, { name: entry.body.candidate.name, title: entry.body.job.title, skills: entry.body.job.required_skills });
  base.candidate = { ...base.candidate, handles: entry.body.candidate.handles, resume_text: entry.body.candidate.resume_text };
  base.job = entry.body.job;
  base.run.started_at = startIso;
  base.progress = progressEvents(events, startIso);
  if (events < 14) {
    const current = base.progress[base.progress.length - 1];
    return {
      ...base,
      run: { ...base.run, status: "running", stage: current.stage, finished_at: null, failures: events > 2 ? [{ source: "github", code: "RATE_LIMITED" }] : [] },
      accounts: events > 6 ? base.accounts : [],
      snapshots: events > 3 ? base.snapshots : [],
      evidence: events > 5 ? base.evidence : [],
      claims: [],
      matches: [],
      coverage: null,
      report: null,
    };
  }
  base.run.finished_at = iso(startIso, 9);
  base.run.status = "partial";
  base.run.failures = [{ source: "github", code: "RATE_LIMITED" }];
  return base;
}

export async function mockGetRun(runId: string): Promise<RunDetail> {
  const make = STATIC_RUNS[runId];
  const result = make ? make() : buildStarted(runId);
  if (deleted.has(result.candidate.id)) throw new ApiError(404, "RUN_NOT_FOUND", `run ${runId} not found`);
  return delay(result);
}

export async function mockStartRun(body: RunBody): Promise<StartRunResponse> {
  const id = `demo-${Math.random().toString(16).slice(2, 10)}`;
  started.set(id, { body, startedAt: Date.now() });
  return delay({ run_id: id }, 400);
}

export async function mockReplay(runId: string): Promise<ReplayResult> {
  const d = await mockGetRun(runId);
  if (!d.report) throw new ApiError(409, "RUN_NOT_FINISHED", "the run has no report yet");
  return delay({ report: d.report, evidence_identical: true, score_identical: true }, 900);
}

export async function mockSnapshotRaw(snapshotId: string): Promise<RawSnapshot> {
  const runId = snapshotId.replace(/-snap-\d+$/, "");
  const snap = snapshots(runId).find((s) => s.id === snapshotId);
  if (!snap) throw new ApiError(404, "SNAPSHOT_NOT_FOUND", `snapshot ${snapshotId} not found`);
  const repos: JsonValue = Array.from({ length: 140 }, (_, i) => ({
    id: 1000 + i,
    name: i === 0 ? "ingest-service" : `repo-${i}`,
    fork: i % 5 === 0 && i > 0,
    language: ["Python", "Go", "TypeScript", null][i % 4],
    stargazers_count: (i * 7) % 50,
    html_url: `https://github.com/janedoe/repo-${i}`,
    topics: ["data", "api"],
    owner: { login: "janedoe", type: "User" },
  }));
  const payload: JsonValue = snap.endpoint === "github/repos" ? repos : { status: "OK", source: snap.source, handle: snap.handle, endpoint: snap.endpoint, result: [{ handle: snap.handle, rating: 1588, maxRating: 1662, rank: "specialist" }] };
  return delay({ snapshot: snap, verified: true, payload }, 350);
}

export async function mockDeleteCandidate(candidateId: string): Promise<void> {
  deleted.add(candidateId);
  return delay(undefined, 400);
}

export async function mockParseResume(file: File, onProgress?: (fraction: number) => void): Promise<ParsedResume> {
  for (const step of [0.25, 0.6, 1]) {
    await delay(null, 200);
    onProgress?.(step);
  }
  const text = file.type.startsWith("text") || /\.(txt|md)$/i.test(file.name) ? await file.text() : RESUME;
  return delay({
    filename: file.name,
    text,
    name: "Jane Doe",
    email: "jane.doe@example.org",
    handles: { github: "janedoe", leetcode: "janedoe" },
    links: ["https://github.com/janedoe", "https://leetcode.com/u/janedoe/"],
    claims: claims("preview").map(({ text: t, kind, subject, years, rating, solved }) => ({ text: t, kind, subject, years, rating, solved })),
    extractor: "rule-based",
  });
}
