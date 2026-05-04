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

Why:

- It contains the latest layout, navigation, mobile shell, cockpit, lab, decisions, and configuration flows.
- It is already configured as its own Vercel project (`apps/thesis-lab-view/.vercel/project.json`).
- It can talk to the current backend through `VITE_API_BASE_URL` or runtime configuration in `/config`.

## What not to do yet

- Do not delete `services/api/static`.
- Do not replace the backend deploy at the root until the new frontend is validated.
- Do not rely on `apps/grao-invest-mobile-web` as the primary UI without an explicit consolidation step.

## Safe rollout plan

1. Keep `grao-invest.vercel.app` as the backend/API host for now.
2. Publish `apps/thesis-lab-view` as a standalone frontend project.
3. Set `VITE_API_BASE_URL=https://grao-invest.vercel.app` for that frontend, or configure the same value in `/config`.
4. Validate the main flows:
   - `/`
   - `/teses`
   - `/lab`
   - `/decisoes`
   - `/config`
5. Only after validation, decide whether to:
   - keep separate frontend/backend domains, or
   - move the main public domain to the new frontend.

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
