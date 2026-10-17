# Evidence Pipeline — web UI

Next.js (App Router, TypeScript strict) front end for the OSINT Evidence Pipeline. A recruiter uploads a resume and a job
requirement. The UI starts a run, follows it live and then presents an auditable report: score breakdown, claim verdicts,
requirement coverage, identity resolution, evidence nodes and the raw, hash-verified snapshots behind them.

## Setup

Requires Node 22 and npm 10.

```bash
cd ui
npm install
npm run dev          # http://localhost:3000
```

The app calls `/api/*`, and Next.js rewrites those calls to the backend (`next.config.ts`). The browser therefore never
needs CORS.

| Variable               | Default                 | Purpose                                                        |
| ---------------------- | ----------------------- | -------------------------------------------------------------- |
| `API_URL`              | `http://localhost:8000` | Backend base URL used by the `/api/*` rewrite (server side).   |
| `NEXT_PUBLIC_DEMO_DATA`| unset                   | Set to `1` to serve built-in demo data instead of the backend. |

```bash
API_URL=http://backend:8000 npm run dev
NEXT_PUBLIC_DEMO_DATA=1 npm run dev     # no backend needed
npm run build && npm start              # production
npm run lint
```

`API_URL` is read when the dev server or build starts, so restart after you change it.

Demo mode (`src/lib/mock.ts`) is loaded only when the flag is set. It holds two finished runs (one partial, with a GitHub
HTTP 403) and simulates a live run for anything you start from the wizard.

## Pages

| Route        | What it does                                                                                              |
| ------------ | --------------------------------------------------------------------------------------------------------- |
| `/`          | Recent runs: candidate, job, sources, status, score and start time. Refreshes while any run is running.   |
| `/new`       | Three-step wizard: resume (upload or paste), job requirement (presets and tag input), review with consent. |
| `/runs/[id]` | Live pipeline timeline while running, then tabs: Overview, Claims, Requirements, Identity, Evidence, Raw data. |

## How the UI maps to the API

All calls live in `src/lib/api.ts`. Response types mirror `docs/api-contract.md` in `src/lib/types.ts`.

| UI action                          | Endpoint                                   |
| ---------------------------------- | ------------------------------------------ |
| Health indicator (top bar, 30 s)   | `GET /health`                              |
| Dashboard table                    | `GET /runs?limit=50`                       |
| Wizard step 1: read resume         | `POST /resumes/parse` (multipart `file`)   |
| Wizard step 3: start analysis      | `POST /runs/start` → navigate to `/runs/{run_id}` |
| Run page (polls every 1.5 s while `running`) | `GET /runs/{run_id}`             |
| Raw data drawer                    | `GET /snapshots/{snapshot_id}/raw`         |
| Replay                             | `POST /runs/{run_id}/replay`               |
| Delete candidate data              | `DELETE /candidates/{candidate_id}`        |
| Export JSON                        | Client-side download of the `GET /runs/{id}` payload |

Pasted resume text is sent to `POST /resumes/parse` as a `pasted-resume.txt` file, so pasted text and uploaded files
go through the same extractor.

`job.id` is `slug(title) + "-" + fnv1a32(title|text|sorted skills)` as 8 hex characters (`src/lib/job.ts`). The same
job reuses one id, and a changed job gets a new one instead of a `JOB_CONFLICT`.

Errors: the client reads `{code, message}` domain errors and FastAPI `{detail}` errors, and shows the code and message in
place. A 404 on a run shows the not-found state.

## Validation

The client checks the same rules as the backend (`pipeline/core/inputs.py`): file type and 5 MB limit, resume text up
to 20,000 characters, email format, per-platform handle patterns, and 1–50 required skills. Profile URLs pasted into a
handle field are reduced to the handle.

## Layout

```
src/app/                 routes (layout, dashboard, /new, /runs/[id], not-found)
src/components/ui/       primitives: Button, Card, Badge, Tabs, Meter, Table, Tooltip, Dialog, Toast, EmptyState, Skeleton, Field, CopyButton, ErrorPanel
src/components/shell/    sidebar, top bar, health indicator
src/components/status/   status, verdict, linked and source badges
src/components/dashboard runs table
src/components/wizard/   new-analysis wizard and its steps
src/components/run/      run page: timeline, tabs, score ring, contribution bar, JSON viewer, snapshot drawer
src/lib/                 api client, types, format helpers, domain helpers, job id, demo data
```
