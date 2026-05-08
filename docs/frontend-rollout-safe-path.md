# Frontend Rollout Safe Path

Date: 2026-05-08

## Current state

- `https://grao-invest.vercel.app/` is serving the Grão Invest soul cockpit from `services/api/frontend_dist`.
- The root deploy is controlled by `vercel.json`, which rewrites every route to `/api/index.py`.
- The source for the deployed soul cockpit lives in `apps/grao-invest-cockpit`.
- `apps/thesis-lab-view` is a legacy/mobile-shell candidate and must not be used to refresh the backend artifact without an explicit consolidation decision.
- `apps/grao-invest-mobile-web` is a secondary frontend candidate, not the main source of truth.
- A preservation copy already exists in `backups/frontend-preservation-20260504_193740`.

## Source of truth

Treat `apps/grao-invest-cockpit` as the official web frontend from this point forward.

Deploy artifact:

- `services/api/frontend_dist` is the tracked build artifact that the FastAPI backend now serves at `/`.
- `services/api/static` remains as the legacy fallback and should not be deleted yet.

Why:

- It contains the current `UI rev soul-4` cockpit, including Dashboard, Teses, Mercado, Backtest, Risco, Alertas, Aprendizado, Método, and Saúde.
- It contains the current visual and product markers used by the quality gate: `A Grande Obra`, `Evolução do método`, `Partitura completa`, and `real-estate-score-hero`.
- It consumes the current backend endpoints directly and falls back only when a feed is unavailable.

## What not to do yet

- Do not delete `services/api/static`.
- Do not replace the backend deploy at the root until the new frontend is validated.
- Do not sync `apps/thesis-lab-view/dist` into `services/api/frontend_dist`; that would regress the public cockpit.
- Do not rely on `apps/grao-invest-mobile-web` as the primary UI without an explicit consolidation step.

## Safe rollout plan

1. Keep `grao-invest.vercel.app` as the backend/API host and main public host.
2. Build `apps/grao-invest-cockpit`.
3. Sync the build into `services/api/frontend_dist` with `powershell -ExecutionPolicy Bypass -File scripts/sync_thesis_lab_frontend.ps1`.
4. Validate the main flows:
   - `/`
   - `/teses`
   - `/mercado`
   - `/backtest`
   - `/risco`
   - `/alertas`
   - `/aprendizado`
   - `/metodo`
   - `/saude`
5. Deploy the backend project so `/api` stays in place and the modern frontend is served from `/`.

## Backend compatibility already confirmed

The cockpit adapts data from the current backend endpoints:

- `/health`
- `/api/dashboard/summary/{user_id}`
- `/api/theses/current-monitor/latest`
- `/api/real-estate/candidates`
- `/api/real-estate/strategy-territory-candidates`

The backend still includes CORS entries for legacy preview origins:

- `https://thesis-lab-view.vercel.app`
- `https://thesis-lab-view.lovable.app`
- local Vite preview origins

## Rollback posture

If the cockpit has any publication issue, the current backend deploy remains online and the legacy UI still works as fallback. The migration should only be considered complete after the tracked source, tracked artifact, API contract gate, and visual smoke all pass.

## Ongoing update workflow

Whenever `apps/grao-invest-cockpit` changes:

1. Run `npm ci` if dependencies changed.
2. Run `npm test` inside `apps/grao-invest-cockpit`.
3. Run a fresh production build inside `apps/grao-invest-cockpit`.
4. Run `scripts/sync_thesis_lab_frontend.ps1`.
5. Commit the source changes and, when intentionally refreshed, the files in `services/api/frontend_dist`.
6. Run the quality gate and visual smoke before deploying.

The sync script refuses to publish a build that does not contain the soul cockpit markers, so an accidental build from the legacy frontend cannot overwrite the current public app silently.
