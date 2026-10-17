import type { Claim, ClaimPreview, EvidenceNode, Failure, Source, Stage, VerdictLabel } from "./types";
import { formatDate, formatNumber } from "./format";

export const SOURCE_LABEL: Record<Source, string> = {
  github: "GitHub",
  codeforces: "Codeforces",
  leetcode: "LeetCode",
};

export function sourceLabel(source: string): string {
  return SOURCE_LABEL[source as Source] ?? source;
}

export const HANDLE_RULES: Record<Source, { pattern: RegExp; hint: string; example: string }> = {
  github: {
    pattern: /^[A-Za-z0-9](?:[A-Za-z0-9]|-(?=[A-Za-z0-9])){0,38}$/,
    hint: "Up to 39 letters, digits or single hyphens; cannot start with a hyphen.",
    example: "janedoe",
  },
  codeforces: {
    pattern: /^[A-Za-z0-9_.-]{3,24}$/,
    hint: "3–24 letters, digits, underscores, dots or hyphens.",
    example: "jane_d",
  },
  leetcode: {
    pattern: /^[A-Za-z0-9_-]{1,30}$/,
    hint: "Up to 30 letters, digits, underscores or hyphens.",
    example: "janedoe",
  },
};

const PROFILE_URL_PATTERNS: Record<Source, RegExp> = {
  github: /github\.com\/([^/?#\s]+)/i,
  codeforces: /codeforces\.com\/profile\/([^/?#\s]+)/i,
  leetcode: /leetcode\.com\/(?:u\/)?([^/?#\s]+)/i,
};

export function normalizeHandle(source: Source, input: string): string {
  const trimmed = input.trim().replace(/^@/, "");
  const match = PROFILE_URL_PATTERNS[source].exec(trimmed);
  return match ? match[1] : trimmed;
}

export function isValidHandle(source: Source, handle: string): boolean {
  return HANDLE_RULES[source].pattern.test(handle);
}

export const EMAIL_PATTERN = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

export const MAX_RESUME_CHARS = 50_000;

export const STAGE_INFO: Record<Stage, { label: string; description: string }> = {
  collect: { label: "Collect", description: "Fetch public data from each source concurrently" },
  freeze: { label: "Freeze", description: "Store every raw response as an immutable SHA-256 snapshot" },
  extract: { label: "Extract", description: "Turn snapshots into typed evidence nodes" },
  resolve: { label: "Resolve", description: "Decide which accounts belong to the candidate" },
  match: { label: "Match", description: "Match required skills to linked evidence" },
  verify: { label: "Verify", description: "Check each resume claim against evidence" },
  score: { label: "Score", description: "Compute the weighted, explainable score" },
};

export const VERDICT_INFO: Record<VerdictLabel, { label: string; tone: "supported" | "partial" | "unsupported" }> = {
  supported: { label: "Supported", tone: "supported" },
  partially_supported: { label: "Partially supported", tone: "partial" },
  unsupported: { label: "Unsupported", tone: "unsupported" },
};

export function explainFailure(failure: Failure): string {
  const name = sourceLabel(failure.source);
  const code = failure.code;
  const tail = "the run continued with the other sources.";
  if (code === "RATE_LIMITED" || code === "HTTP_429") return `${name} rate limit reached — ${tail}`;
  if (code === "HTTP_403") return `${name} refused the request (HTTP 403, usually a rate limit) — ${tail}`;
  if (code === "NOT_FOUND" || code === "HTTP_404") return `${name} has no account with this handle — ${tail}`;
  if (code === "TIMEOUT") return `${name} did not respond in time — ${tail}`;
  if (code === "NETWORK") return `${name} could not be reached — ${tail}`;
  if (code === "MALFORMED_BODY" || code === "UNEXPECTED_SHAPE") return `${name} returned data in an unexpected format — ${tail}`;
  if (/^HTTP_5\d\d$/.test(code)) return `${name} had a server error (${code.replace("_", " ")}) — ${tail}`;
  return `${name} failed with ${code}${failure.message ? `: ${failure.message}` : ""} — ${tail}`;
}

export function describeClaim(claim: ClaimPreview): string {
  const subject = claim.subject ? displaySubject(claim.subject) : claim.text;
  if (claim.kind === "rating" && claim.rating !== null) return `${subject} · ${claim.rating}`;
  if (claim.kind === "solved" && claim.solved !== null) return `${subject} · ${formatNumber(claim.solved)} solved`;
  if (claim.years !== null) return `${subject} · ${formatYears(claim.years)}`;
  return subject;
}

export function formatYears(years: number): string {
  const rounded = Number.isInteger(years) ? years : Number(years.toFixed(1));
  return `${rounded} ${rounded === 1 ? "yr" : "yrs"}`;
}

function displaySubject(subject: string): string {
  const known = SOURCE_LABEL[subject.toLowerCase() as Source];
  return known ?? subject;
}

export const CLAIM_KIND_LABEL: Record<string, string> = {
  skill: "Skills",
  rating: "Competitive rating",
  solved: "Problems solved",
};

export function groupClaims<T extends ClaimPreview>(claims: T[]): [string, T[]][] {
  const groups = new Map<string, T[]>();
  for (const claim of claims) {
    const list = groups.get(claim.kind) ?? [];
    list.push(claim);
    groups.set(claim.kind, list);
  }
  return [...groups.entries()];
}

export interface EvidenceSummary {
  title: string;
  facts: { label: string; value: string }[];
}

function str(value: unknown): string | null {
  if (value === null || value === undefined || value === "") return null;
  if (typeof value === "number") return Math.abs(value) >= 10000 ? formatNumber(value) : String(value);
  if (Array.isArray(value)) return value.length ? value.map(String).join(", ") : null;
  return String(value);
}

function fact(label: string, value: unknown, format?: (v: string) => string) {
  const text = typeof value === "string" && format ? format(value) : str(value);
  return text && text !== "—" ? { label, value: text } : null;
}

export function summarizeEvidence(node: EvidenceNode): EvidenceSummary {
  const v = node.value;
  const facts = (() => {
    switch (node.kind) {
      case "skill":
        return [
          fact("First seen", v.first_seen, formatDate),
          fact("Last seen", v.last_seen, formatDate),
          fact("Source", v.evidence),
          fact("Repo", v.repo),
          fact("Submissions", v.submissions),
          fact("Solved", v.solved),
        ];
      case "project":
        return [fact("Language", v.language), fact("Stars", v.stars), fact("Topics", v.topics), fact("Pushed", v.pushed_at, formatDate)];
      case "contribution":
        return [fact("Commits", v.commits), fact("First", v.first, formatDate), fact("Last", v.last, formatDate)];
      case "achievement":
        return [
          fact("Rating", v.rating),
          fact("Max rating", v.max_rating),
          fact("Rank", v.rank),
          fact("Solved", v.solved),
        ];
      default:
        return Object.entries(v).slice(0, 4).map(([key, value]) => fact(key, value));
    }
  })().filter((f): f is { label: string; value: string } => f !== null);

  const title = (() => {
    if (node.kind === "contribution") return str(v.repo) ?? "Contribution";
    if (node.kind === "achievement") return `${sourceLabel(String(v.platform ?? node.source))} profile`;
    return str(v.name) ?? node.kind;
  })();

  return { title, facts };
}

export function findClaimSpans(text: string, claims: Claim[]): { start: number; end: number; claim: Claim }[] {
  const lower = text.toLowerCase();
  const spans: { start: number; end: number; claim: Claim }[] = [];
  for (const claim of claims) {
    const needle = claim.text.trim().toLowerCase();
    if (!needle) continue;
    let from = 0;
    while (from <= lower.length) {
      const index = lower.indexOf(needle, from);
      if (index === -1) break;
      const end = index + needle.length;
      if (!spans.some((s) => index < s.end && end > s.start)) {
        spans.push({ start: index, end, claim });
        break;
      }
      from = index + 1;
    }
  }
  return spans.sort((a, b) => a.start - b.start);
}
