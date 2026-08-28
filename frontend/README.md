# Frontend — Enterprise Support Agent

Next.js 14 (App Router) + TypeScript + Tailwind CSS UI for the FastAPI
backend in `../backend`. Five screens: Profile → Discover → Investigate →
Mentor Workspace → PR Review, each depending on state (profile id,
workspace id, session id) produced by the one before it.

## Running against a local backend

1. Start the backend first (from `backend/`):

   ```bash
   uvicorn app.main:app --reload --app-dir src
   ```

   This serves the API at `http://localhost:8000`.

2. In a separate terminal, start the frontend (from `frontend/`):

   ```bash
   npm install
   npm run dev
   ```

   This serves the UI at `http://localhost:3000`. It talks to the
   backend at `http://localhost:8000` by default; override with
   `NEXT_PUBLIC_API_BASE_URL` if the backend runs elsewhere.

3. Open `http://localhost:3000/profile` and work through the flow in
   order — Profile, Discover, Investigate, Mentor, PR Review. Each
   screen stores what the next one needs (profile id, workspace id,
   session id) in `localStorage`, since there's no auth system yet and
   this is a single-user demo.

## Verification

```bash
npm run build   # next build — TypeScript strict mode, zero errors
npm run test    # vitest run — all component tests, API mocked with msw
npm run lint    # next lint — ESLint, Next.js default config
```

See `TESTING.md` for the TDD log — the failing-test-first discipline
followed for every interactive component, including the bugs it caught
along the way.
