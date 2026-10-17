import type {
  Health,
  ParsedResume,
  RawSnapshot,
  ReplayResult,
  RunBody,
  RunDetail,
  RunSummary,
  StartRunResponse,
} from "./types";

const BASE = "/api";

export const DEMO_MODE = process.env.NEXT_PUBLIC_DEMO_DATA === "1";

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }

  get isNotFound(): boolean {
    return this.status === 404;
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function describeDetail(detail: unknown): string | null {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const parts = detail
      .map((item) => {
        if (!isRecord(item)) return null;
        const loc = Array.isArray(item.loc) ? item.loc.filter((p) => p !== "body").join(".") : "";
        const msg = typeof item.msg === "string" ? item.msg : "";
        return loc ? `${loc}: ${msg}` : msg;
      })
      .filter((part): part is string => Boolean(part));
    return parts.length ? parts.join("; ") : null;
  }
  return null;
}

export function errorFromBody(status: number, body: unknown, fallback: string): ApiError {
  if (isRecord(body)) {
    if (typeof body.code === "string") {
      return new ApiError(status, body.code, typeof body.message === "string" ? body.message : fallback);
    }
    const detail = describeDetail(body.detail);
    if (detail) return new ApiError(status, status === 404 ? "NOT_FOUND" : `HTTP_${status}`, detail);
  }
  return new ApiError(status, status === 0 ? "NETWORK" : `HTTP_${status}`, fallback);
}

function parseJson(text: string): unknown {
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${BASE}${path}`, {
      ...init,
      headers: { Accept: "application/json", ...(init?.body ? { "Content-Type": "application/json" } : {}), ...init?.headers },
      cache: "no-store",
    });
  } catch {
    throw new ApiError(0, "NETWORK", "The backend could not be reached.");
  }
  const text = await response.text();
  const body = parseJson(text);
  if (!response.ok) {
    throw errorFromBody(response.status, body, `${response.status} ${response.statusText}`.trim());
  }
  return body as T;
}

async function mock() {
  return import("./mock");
}

export async function getHealth(): Promise<Health> {
  if (DEMO_MODE) return (await mock()).mockHealth();
  return request<Health>("/health");
}

export async function listRuns(limit = 50): Promise<RunSummary[]> {
  if (DEMO_MODE) return (await mock()).mockListRuns();
  return request<RunSummary[]>(`/runs?limit=${limit}`);
}

export async function getRun(runId: string): Promise<RunDetail> {
  if (DEMO_MODE) return (await mock()).mockGetRun(runId);
  return request<RunDetail>(`/runs/${encodeURIComponent(runId)}`);
}

export async function startRun(body: RunBody): Promise<StartRunResponse> {
  if (DEMO_MODE) return (await mock()).mockStartRun(body);
  return request<StartRunResponse>("/runs/start", { method: "POST", body: JSON.stringify(body) });
}

export async function replayRun(runId: string): Promise<ReplayResult> {
  if (DEMO_MODE) return (await mock()).mockReplay(runId);
  return request<ReplayResult>(`/runs/${encodeURIComponent(runId)}/replay`, { method: "POST" });
}

export async function getSnapshotRaw(snapshotId: string): Promise<RawSnapshot> {
  if (DEMO_MODE) return (await mock()).mockSnapshotRaw(snapshotId);
  return request<RawSnapshot>(`/snapshots/${encodeURIComponent(snapshotId)}/raw`);
}

export async function deleteCandidate(candidateId: string): Promise<void> {
  if (DEMO_MODE) return (await mock()).mockDeleteCandidate(candidateId);
  await request<null>(`/candidates/${encodeURIComponent(candidateId)}`, { method: "DELETE" });
}

export function parseResume(file: File, onProgress?: (fraction: number) => void): Promise<ParsedResume> {
  if (DEMO_MODE) return mock().then((m) => m.mockParseResume(file, onProgress));
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    const form = new FormData();
    form.append("file", file);
    xhr.open("POST", `${BASE}/resumes/parse`);
    xhr.setRequestHeader("Accept", "application/json");
    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable && onProgress) onProgress(event.loaded / event.total);
    };
    xhr.onload = () => {
      const body = parseJson(xhr.responseText);
      if (xhr.status >= 200 && xhr.status < 300) resolve(body as ParsedResume);
      else reject(errorFromBody(xhr.status, body, `${xhr.status} ${xhr.statusText}`.trim()));
    };
    xhr.onerror = () => reject(new ApiError(0, "NETWORK", "The backend could not be reached."));
    xhr.send(form);
  });
}

export function toApiError(error: unknown): ApiError {
  if (error instanceof ApiError) return error;
  if (error instanceof Error) return new ApiError(0, "CLIENT_ERROR", error.message);
  return new ApiError(0, "CLIENT_ERROR", "Unexpected error");
}
