# Frontend architecture

React single-page app (Vite + React + TypeScript + Tailwind), built on the
TailAdmin template. It talks to the FastAPI backend in the repo root over JSON.

## Running it

| What     | Command (from repo root)          | URL                   |
| -------- | --------------------------------- | --------------------- |
| Backend  | `uv run uvicorn app.main:app --reload` | http://localhost:8000 |
| Frontend | `cd frontend && npm run dev`      | http://localhost:5173 |

## Request flow

```
browser → React page (src/pages/…) → fetch("/api/…")
        → Vite dev proxy (strips /api) → FastAPI JSON route → Postgres
        ← JSON ← React stores it in state → screen re-renders
```

The proxy lives in `vite.config.ts` (`server.proxy`). Example:
`/api/clubs/3` → `http://localhost:8000/clubs/3`. Frontend code always calls
`/api/...`; it never hard-codes the backend's address.

## Where things live

| Path                              | Role                                         |
| --------------------------------- | -------------------------------------------- |
| `src/main.tsx`                    | Entry point; wraps the app in providers      |
| `src/App.tsx`                     | The only route table (URL → page)            |
| `src/components/ui/`              | TailAdmin building blocks (button, table, …) |
| `src/components/layout/app-layout/` | Sidebar + header shell around every page   |
| `src/pages/`                      | One folder per screen                        |
| `src/lib/api.ts`                  | `apiFetch()`: the only way to call the backend; throws `ApiError` |
| `src/lib/types.ts`                | Shapes of the backend's JSON; mirrors `app/schemas.py` + `app/models.py` |

## Fetching data

TanStack Query (`@tanstack/react-query`) manages all data from the backend:
`useQuery` for reading, `useMutation` for changes. One `QueryClient` (its
cache) is created in `src/main.tsx` and shared with every page through
`QueryClientProvider`. Query functions call `apiFetch` from `src/lib/api.ts`.

## Auth

`src/contexts/auth-context.tsx` provides `AuthProvider` (mounted in
`main.tsx`) and `useAuth()` → `{ user, isLoading, signIn, signOut }`.

- The JWT lives in `localStorage` under `access_token` (`TOKEN_KEY` in `api.ts`).
- `apiFetch` sends it as `Authorization: Bearer <token>` on every call.
- With a token, `AuthProvider` loads the user from `GET /auth/me`
  (query key `["me", token]`); without one, it makes no request.
- `signOut()` deletes the token and clears the whole query cache.
- Sign-in (`src/pages/others/auth/sign-in/form.tsx`): `useMutation` posts
  `username` + `password` as a form (`URLSearchParams`, which FastAPI's
  `OAuth2PasswordRequestForm` requires) to `/auth/login`, then
  `signIn(access_token)` and navigates to `/`. Failures show the backend's
  `detail` in a destructive `Alert`.
- Sign-up (`src/pages/others/auth/sign-up/form.tsx`): `useMutation` posts
  JSON `{ name: "<first> <last>", email, password }` to `/auth/register`
  (always creates a `club_lead`), then navigates to `/signin?registered=1`,
  where the sign-in form shows a success `Alert`. Admins are created
  directly in the database, never through sign-up.
- Route guard: `RequireAuth` (`src/components/shared/require-auth.tsx`) wraps
  every `AppLayout` route in `App.tsx`. Spinner while `/auth/me` loads;
  no user → `<Navigate to="/signin" replace />`. Auth pages stay public.
- Header (`src/components/shared/header/user-dropdown/index.tsx`) shows the
  user's initials, name and email from `useAuth()`. "Sign out" calls
  `signOut()`; `RequireAuth` then redirects to `/signin`.
- If `/auth/me` answers 401 (expired/invalid token), the token is deleted
  and the user is treated as logged out.
- Not yet: a 401 from other data requests mid-session (added with the first
  data page, step 13); admin-only guard (added with the first admin page).

## Conventions

- Build screens only from `src/components/ui` and the app layout; no extra UI libraries.
- Reuse existing Tailwind classes; no new colours, fonts, shadows or spacing.
- New page text is plain English; only sidebar labels go through i18n (`en.json`).
