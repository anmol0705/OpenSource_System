# TDD Log

Every interactive component in this app was built test-first: a failing
RTL/Vitest spec was written and run to confirm it failed for the right
reason (missing component / missing behavior, not a typo), and only then
was the implementation written to make it pass. This file is the running
log of that discipline, in commit-message style, one entry per component.

The API layer is mocked with `msw` (`test/mocks/server.ts`) so no test
requires a live backend. Every screen has at minimum a loading-state test,
a success-path test, and an error-state test.

---

## components/profile/ProfileForm

- **Red**: wrote `ProfileForm.test.tsx` (renders fields, loading state,
  success stores profile + shows confirmation, error shows a readable
  `role="alert"` message) against a component that did not exist yet.
  Ran `vitest run` — failed with "Failed to resolve import './ProfileForm'"
  — confirms the test fails because the implementation is missing, not
  because of a typo in the test.
- **Green**: implemented `ProfileForm.tsx` — controlled form for name,
  addable language/proficiency pairs, a fixed multi-select of domains,
  and an overall-proficiency selector (persisted client-side only, since
  `POST /profiles` has no field for it — see README) — until all 4 tests
  passed.
- Bug caught by the red step's *sibling* runs: three tests initially
  called a shared `fillMinimalValidForm()` helper without first calling
  `render()`, producing an empty `<body />`. Fixed in the test file
  before touching the component, per TDD discipline (fix the test's own
  bug, re-run red, then implement).

## components/discover/DiscoverView

- **Red**: wrote `DiscoverView.test.tsx` covering the repo-search loading
  state, a success render that asserts all four repo score-breakdown
  fields are individually visible (not just the aggregate score),
  a repo-search error state, and the full select-repo → load scored
  issues → select issue → create sandbox → `router.push("/investigate")`
  flow, mocking `next/navigation` and the backend via `msw`. Ran against
  a nonexistent `DiscoverView` — failed on the unresolved import.
- **Green**: implemented `DiscoverView.tsx` plus the pure-layout
  `ScoreBreakdown.tsx` (no dedicated test — display-only, no branching
  logic) until all 4 tests passed on the first implementation attempt.
- `ScoreBreakdown` is reused unchanged for both repo and issue cards —
  the backend's two breakdown shapes are structurally compatible
  (`Record<string, number>`), so one component covers both without
  fabricating a shared type that doesn't exist server-side.

## components/investigate/InvestigateView

- **Red**: wrote `InvestigateView.test.tsx` (loading state, success
  timeline + final confidence meter + target file + "Start Mentoring
  Session" CTA, error state, "no context" state, and the full start-
  mentoring flow: fetch file content via `/run`, call `/mentor/start`,
  navigate to `/mentor/[sessionId]`). Ran against a nonexistent
  `InvestigateView` — failed on the unresolved import.
- **Green**: implemented `InvestigateView.tsx`. One assertion bug
  surfaced during the first green run: `findByText(/src\/retry\.py/)`
  matched two elements (the target-file paragraph and the "files
  inspected: src/retry.py, src/client.py" summary line, which contains
  it as a substring), so RTL threw. Fixed by asserting an exact string
  match instead of a substring regex — a test bug, not a component bug.
  All 5 tests passed after that fix.
- **Honest data limitation, not fabrication**: `POST /sandboxes/{id}/investigate`
  only returns the *final* hypothesis/confidence/target_file plus a flat
  `history: string[]` of per-iteration reasoning text (extended server-side
  in `sandboxes.py` to also return `files_with_history_checked`, since the
  investigator graph already tracks that in `file_histories` but the
  endpoint wasn't surfacing it). The backend does **not** expose a
  confidence score or inspected-file attribution per individual iteration
  — only in aggregate. Rather than inventing per-step confidence numbers,
  the timeline shows each iteration's real reasoning text, and the
  confidence meter is honestly labeled "Final confidence" attached to the
  concluding summary, with the aggregate files-inspected / history-checked
  lists shown alongside it.
- The Mentor Workspace needs the target file's real source (`original_content`),
  but `sandboxes.py` has no dedicated file-read endpoint — only
  `POST /sandboxes/{id}/run`, which executes an arbitrary shell command in
  the sandbox. `handleStartMentoring` uses that endpoint with `cat "<target_file>"`
  to retrieve real content, rather than fabricating placeholder source.

## components/mentor/MentorWorkspace (hero screen)

- **Red**: wrote `MentorWorkspace.test.tsx` — initial render (issue,
  first hint, "Hint 1 of 4" counter, Monaco preloaded with
  `original_content`), a submit-loading state, a failing attempt
  (test output shown, new hint animated in, Run Tests disabled until
  acknowledged), a passing attempt (success state, PR context saved,
  "Proceed to PR Review" link), and a submit error state. `@monaco-editor/react`
  is mocked as a plain `<textarea>` since Monaco doesn't mount under
  jsdom — the mock exposes the same `value`/`onChange` contract the
  real editor uses, so the component under test is unchanged. Ran
  against a nonexistent `MentorWorkspace` — failed on the unresolved import.
- **Green**: implemented `MentorWorkspace.tsx`. The first green run
  exposed a real product decision the tests hadn't accounted for: the
  *initial* hint delivered by `/mentor/start` was being gated exactly
  like a hint from `/submit-attempt` (Run Tests stays disabled until
  acknowledged) — correct per the "never skip reading a hint" requirement,
  but 3 of the tests clicked Run Tests immediately after mount without
  acknowledging it first, so the disabled button silently ate the click
  and the assertions timed out. Fixed the tests (added the
  acknowledge-hint click before each Run Tests click) rather than
  weakening the gating in the component — the gating is the point.
- Hint gating uses a single `hasUnreadHint` boolean that's set on every
  hint arrival (including the very first one) and cleared only by the
  explicit "I've read this hint" click — Run Tests stays disabled the
  entire time in between, and there's no auto-scroll or auto-dismiss
  that would let a hint go past unread.

## components/pr-review/PrReviewView

- **Red**: wrote `PrReviewView.test.tsx` (no-context message, diff
  render, approve-and-push loading state, success with a clickable real
  PR URL, an approval error state, and change-request feedback as an
  alternative to approving blind). Ran against a nonexistent
  `PrReviewView` — failed on the unresolved import.
- **Green**: implemented `PrReviewView.tsx` using `react-diff-viewer-continued`
  for the original-vs-final diff. Two test bugs surfaced during the
  first green run, both fixed in the test file rather than the component:
  1. `getByText(/return true/)` failed case-sensitively against the
     rendered `"return True"` — fixed with a case-insensitive regex.
  2. `react-diff-viewer-continued` computes its diff in an effect after
     mount (`tbody` is empty on the synchronous render, with an
     `act(...)` warning confirming the async update), so the diff rows
     aren't there yet for a synchronous `getByText` — switched to
     `findByText` to wait for them.
  3. The change-request feedback confirmation text collided with
     `getByText` matching the still-mounted `<textarea>` alongside the
     confirmation `<p>` ("Found multiple elements") — fixed by giving
     the confirmation paragraph `data-testid="saved-feedback"` and
     querying by that instead of a text regex.
- **Honest design decision on "Request changes"**: the backend has no
  endpoint to persist PR review comments — `PRManagerState` has a
  `latest_comments` field but no router wires anything into it. Rather
  than fabricating a fake "comment saved" success, `handleRequestChanges`
  calls the real `request-approval` endpoint (so `awaiting_human_approval`
  status is genuinely recorded) but explicitly never calls `approve`,
  and the UI labels the feedback text as recorded locally only, not
  sent to the backend — no screen here pretends data went somewhere it
  didn't.
- **PR URL**: `POST /sandboxes/pr/{id}/approve` returns only `pr_number`
  and `status`, no URL. The link shown is built from real data —
  `https://github.com/{repo_full_name}/pull/{pr_number}` — rather than
  inventing a URL field the backend doesn't have.

## Backend changes made to support this frontend

Two small, additive changes to `backend/src/app/`, both required for the
UI to work against a real running backend rather than just mocks:

1. `routers/sandboxes.py` — `/sandboxes/{workspace_id}/investigate` now
   also returns `history` and `files_with_history_checked`. Both values
   already existed in the investigator graph's final state
   (`InvestigationState["history"]` and `["file_histories"]`) but the
   endpoint wasn't surfacing them, so the Investigation timeline had no
   real reasoning trail to render. No behavior changed, only the
   response shape gained two fields.
2. `main.py` — added `CORSMiddleware` allowing `http://localhost:3000`.
   Without it, every fetch from the Next.js dev server is blocked by the
   browser's CORS policy before it reaches the API, regardless of how
   correct the frontend code is.
