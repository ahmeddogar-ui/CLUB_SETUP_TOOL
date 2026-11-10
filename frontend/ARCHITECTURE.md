# Frontend architecture

React single-page app (Vite + React + TypeScript + Tailwind), built on the
TailAdmin template. It talks to the FastAPI backend in the repo root over JSON.

## Running it

| What     | Command (from repo root)               | URL                   |
| -------- | -------------------------------------- | --------------------- |
| Backend  | `uv run uvicorn app.main:app --reload` | http://localhost:8000 |
| Frontend | `cd frontend && npm run dev`           | http://localhost:5173 |

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

| Path                                | Role                                                                     |
| ----------------------------------- | ------------------------------------------------------------------------ |
| `src/main.tsx`                      | Entry point; wraps the app in providers                                  |
| `src/App.tsx`                       | The only route table (URL → page)                                        |
| `src/components/ui/`                | TailAdmin building blocks (button, table, …)                             |
| `src/components/layout/app-layout/` | Sidebar + header shell around every page                                 |
| `src/pages/main/clubs/`             | All club screens and their dialogs (see "Screens")                       |
| `src/pages/others/auth/`            | Sign-in / sign-up (`AuthLayout` redirects signed-in users to `/`)        |
| `src/lib/api.ts`                    | `apiFetch()`: the only way to call the backend; throws `ApiError`        |
| `src/lib/types.ts`                  | Shapes of the backend's JSON; mirrors `app/schemas.py` + `app/models.py` |
| `src/lib/labels.ts`                 | Display labels, badge colours, `EDITABLE_STATUSES`, date formatting      |

## Fetching data

TanStack Query (`@tanstack/react-query`) manages all data from the backend:
`useQuery` for reading, `useMutation` for changes. One `QueryClient` (its
cache) is created in `src/main.tsx` and shared with every page through
`QueryClientProvider`. Query functions call `apiFetch` from `src/lib/api.ts`.

- Query keys: `["clubs"]` (list), `["clubs", "review-queue"]`, `["clubs", id]`,
  `["clubs", id, "requirements"]`, `["clubs", id, "events"]`.
- Every club mutation goes through `useClubMutation`
  (`src/pages/main/clubs/use-club-mutation.ts`), which invalidates `["clubs"]`
  so all club data refetches after any change.
- 4xx errors are not retried; 5xx/network errors retry up to 3 times.
- A 401 from any query or mutation while a token is stored deletes the token
  and refetches `["me"]`, so `RequireAuth` sends the user to `/signin`.

## Screens

| URL              | Who            | Page / data                                                      |
| ---------------- | -------------- | ---------------------------------------------------------------- |
| `/`              | everyone       | `clubs-page.tsx` — `GET /clubs` (leads: own clubs; admins: all)  |
| `/clubs/new`     | club leads     | `new-club-page.tsx` — `POST /clubs`                              |
| `/clubs/:clubId` | owner or admin | `club-detail-page.tsx` — club, requirements, events              |
| `/review`        | admins         | `review-queue-page.tsx` — submitted + under review, oldest first |

Club detail page actions (the backend enforces every rule; the UI only hides
buttons that would be refused):

- Owner, while drafting / changes requested: edit (`PATCH`), provide document
  links (`PUT …/requirements/{type}/link`), submit / resubmit. Submit errors
  (e.g. `missing: constitution`) come from the backend and show in an `Alert`.
- Admin, submitted: start review. Under review: approve / reject each
  requirement (`NoteActionDialog`; reject needs a note), approve club,
  request changes, reject club (note required).

Backend endpoints added for this frontend (read-only, no business-logic
change): `GET /clubs/{id}/requirements` and `GET /clubs/{id}/events`, with the
same owner-or-admin check as `GET /clubs/{id}`. Tests:
`tests/test_club_read_routes.py`.

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
- No social login, "remember me", password reset or terms checkbox: the
  backend has none of these, so the template's versions were removed.
- Admin-only routes are wrapped in `RequireAdmin`
  (`src/components/shared/require-admin.tsx`); the sidebar hides items marked
  `isAdminOnly` in `sidebar/data.tsx`.

## Template leftovers

All TailAdmin demo pages, sample images and fake header widgets (search,
notifications, language switcher) have been removed. Still from the template
and intentionally kept: `components/ui`, the app layout, the 404 page, theme
toggle, and four images in `public/images` (logo icon, auth grid, 404 art).

## Conventions

- Build screens only from `src/components/ui` and the app layout; no extra UI libraries.
- Reuse existing Tailwind classes; no new colours, fonts, shadows or spacing.
- New page text is plain English; only sidebar labels go through i18n (all four `src/messages/*.json`).
