# Frontend Rollout Safe Path

Date: 2026-05-04

## Current state

- `https://grao-invest.vercel.app/` is serving the legacy static UI from `services/api/static`.
- The root deploy is controlled by `vercel.json`, which rewrites every route to `/api/index.py`.
- The most evolved frontend lives in `apps/thesis-lab-view`.
- `apps/grao-invest-mobile-web` is a secondary frontend candidate, not the main source of truth.
- A preservation copy already exists in `backups/frontend-preservation-20260504_193740`.

## Source of truth

Treat `apps/thesis-lab-view` as the official web frontend from this point forward.

Deploy artifact:

- `services/api/frontend_dist` is the tracked build artifact that the FastAPI backend now serves at `/`.
- `services/api/static` remains as the legacy fallback and should not be deleted yet.

Why:

- It contains the latest layout, navigation, mobile shell, cockpit, lab, decisions, and configuration flows.
- It is already configured as its own Vercel project (`apps/thesis-lab-view/.vercel/project.json`).
- It can talk to the current backend through `VITE_API_BASE_URL` or runtime configuration in `/config`.

## What not to do yet

- Do not delete `services/api/static`.
- Do not replace the backend deploy at the root until the new frontend is validated.
- Do not rely on `apps/grao-invest-mobile-web` as the primary UI without an explicit consolidation step.

## Safe rollout plan

1. Keep `grao-invest.vercel.app` as the backend/API host and main public host.
2. Build `apps/thesis-lab-view`.
3. Sync the build into `services/api/frontend_dist` with `powershell -ExecutionPolicy Bypass -File scripts/sync_thesis_lab_frontend.ps1`.
4. Validate the main flows:
   - `/`
   - `/teses`
   - `/lab`
   - `/decisoes`
   - `/config`
5. Deploy the backend project so `/api` stays in place and the modern frontend is served from `/`.

## Backend compatibility already confirmed

The frontend can adapt data from the current backend endpoints:

- `/health`
- `/api/dashboard/summary/{user_id}`
- `/api/theses/current-monitor/latest`
- `/api/real-estate/candidates`
- `/api/assistant/decisions`
- `/api/microtrades/autopilot/latest`

The backend already includes CORS entries for:

- `https://thesis-lab-view.vercel.app`
- `https://thesis-lab-view.lovable.app`
- local Vite preview origins

## Rollback posture

If the new frontend has any publication issue, the current backend deploy remains online and the legacy UI still works as fallback. The migration should only be considered complete after the standalone frontend is validated in production.

## Ongoing update workflow

Whenever `apps/thesis-lab-view` changes:

1. Run a fresh production build inside `apps/thesis-lab-view`.
2. Run `scripts/sync_thesis_lab_frontend.ps1`.
3. Commit both the source changes and the refreshed files in `services/api/frontend_dist`.
4. Deploy the backend project.
