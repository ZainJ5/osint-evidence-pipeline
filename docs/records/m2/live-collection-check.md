# Live collection check (M1 collectors + M2 parsers)

Date: 2026-11-18/19 (UTC 22:50-23:10). Method: the real `HttpAdapter(token="")` (no token used) +
`CollectorFactory.create(source, ...).collect(handle)`, frozen into `SnapshotStore(InMemoryBlobStore,
InMemoryRepository)`, then `EvidenceExtractor(default_parsers())` run twice (4 workers and 1 worker).
Every evidence value was compared by hand against the raw JSON. Public accounts only; no raw data committed.

## Requests

| Source | Account | Endpoints | Requests |
|---|---|---|---|
| GitHub (unauthenticated) | `octocat`, `RunConfig(max_repos=2)` | users/{h}, users/{h}/repos, repos/{h}/{r}/languages x2, repos/{h}/{r}/commits?author=x2 | 6 (+1 refused 403 while the quota was exhausted, see below) |
| Codeforces | `tourist` | user.info, user.rating, user.status (count=1000, then 10000), user.status full via curl; unknown handle and bad parameter probes | 2 x 3 collector runs + 4 probes |
| LeetCode | `lee215` | POST /graphql (profile query); unknown-user probe | 2 |

The GitHub quota was at 0/60 when the check started (spent earlier on this IP). The 403 we got back was used as
the real rate-limit shape. The check ran after the reset at 23:00 UTC.

## What was compared (raw field -> evidence value)

GitHub
- repos[i].{name, description, language, stargazers_count, html_url, created_at, pushed_at, topics} -> `project`
  value {name, description, language, stars, url, created_at, pushed_at, topics}, locator `$[i]` (raw index, so
  the forks at `$[2]` and `$[5]` leave gaps). Forks (`linguist`, `boysenberry-repo-1`) were skipped. All 8 repos had
  `topics` (empty lists for octocat).
- languages {"HTML":355,"CSS":256} -> 2 `skill` nodes, first_seen=repo.created_at (2011-01-27), last_seen=repo.pushed_at
  (2024-08-21), bytes as given, locator `$['CSS']`. Hello-World returned `{}`, so it has no skills (correct).
- commits?author=octocat -> `contribution` {commits, first, last}. Spoon-Knife: 3 commits, all authored by octocat.
  Commit bb4cc8d has author date 2014-02-04 but committer date 2014-02-12. The parser uses `commit.author.date`, so
  first=2014-02-04T22:38:24Z and last=2014-02-12T23:20:44Z (correct for authorship).
- users/octocat: name, email (null), blog, twitter_username (null), html_url are present as identity expects.

Codeforces
- user.info result[0].{rating 3408, maxRating 4009, rank, maxRank "tourist"} -> `achievement`. maxRank was dropped
  before this check.
- user.status: verdict "OK" = accepted ("PARTIAL", 838 of them, is correctly not accepted). Skill per raw
  `programmingLanguage`, first/last from `creationTimeSeconds` of accepted submissions only.
- Full history: 5,519 submissions, 3,379 accepted, 3,060 distinct problems, 3.2 MB, 2-6 s. With count=1000 the
  pipeline saw only 676 solved and skills starting in 2024. With count=10000 it sees 3,060 solved, 26 language skills
  starting in 2010, and capped=false.
- Unknown handle: HTTP 400 `{"status":"FAILED","comment":"handles: User with handle x not found"}`. Bad parameter: HTTP
  400 `{"status":"FAILED","comment":"count: Field should contain integer value"}`.

LeetCode
- The query works unchanged against the live endpoint, with no Referer, CSRF or cookie needed (UA
  `osint-evidence-pipeline`). acSubmissionNum "All" 704 -> solved; languageProblemCount (7 entries) -> 7 skills;
  userContestRanking.rating float -> int (2204). Unknown user: HTTP 200, `errors[...]` + `data.matchedUser: null`,
  which gives NOT_FOUND (correct).

Determinism: node ids were identical with 4 workers and 1 worker for all three sources. Snapshot ids are uuid5(run,
source, endpoint, sha256), so they are stable for the same bytes.

## Findings and fixes

1. Codeforces user.status was capped at 1000, which badly undercounted active users (676 vs 3,060 solved for tourist).
   Fix: `STATUS_COUNT = 10000` (bounded, about 6 MB at most). The status achievement now has `capped` (true when a full
   page came back).
2. Codeforces treated every FAILED envelope as NOT_FOUND, so a bad parameter would be reported as "handle not found".
   Fix: NOT_FOUND only when the comment says "not found". Other cases keep their HTTP code (HTTP_400).
3. Codeforces solved count was keyed by (contestId, index, name). A renamed statement counted twice, and acmsguru
   problems keyed on (None, index). Fix: key is (contestId or problemsetName, index).
4. Codeforces maxRank was not kept. Fix: `max_rank` was added to both Codeforces achievements (None on the status one).
5. GitHub project nodes lacked `topics`. Fix: `topics` (list of str, [] when absent).
6. GitHub commits: one page of 100 commits. Kept single page, and the contribution now has `capped` (true at 100,
   meaning "at least 100"). Author date confirmed as the right field.
7. GitHub rate limit 403 was a generic HTTP_403. Fix: new code `RATE_LIMITED` (not retried) for a 403 whose message
   mentions the rate limit (primary "API rate limit exceeded ..." and secondary limits). 429 is still retried.
   `HttpResponse` has no headers, so `x-ratelimit-remaining` cannot be read (see the open items).
8. No issues found in: fork skipping, archived repos (kept as projects), the empty-repo 409 skip, languages and dates,
   LeetCode parsing, or locators.

## Added evidence value keys
- `project.topics` (GitHub)
- `contribution.capped` (GitHub)
- `achievement.max_rank` (Codeforces, both achievement nodes)
- `achievement.capped` (Codeforces user.status achievement only)

## Open items (outside M1/M2 files)
- `pipeline/core/ports.py` HttpResponse plus `pipeline/adapters/http.py`: adding response headers would let RATE_LIMITED
  use `x-ratelimit-remaining: 0` and report `x-ratelimit-reset` to the UI.
- LeetCode `max_rating` equals the current contest rating: the query has no historical maximum.
