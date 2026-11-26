# Club Setup v2 (UX polish, admin features, requests) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (native: one implementer, one review per batch). Steps use checkbox (`- [ ]`) syntax.

**Goal:** Polish the UX, add the admin/profile features, and build a generic request engine (funding, room booking) on top of approved clubs.

**Architecture:** Existing layering (routers → services → models) and the club pattern (row lock, one commit per action, append-only event row per action) are reused. Requests get one data-defined engine: a type registry (details schema + ordered approval roles) and one action table. Room double-booking is prevented by a Postgres exclusion constraint on the `requests` row itself.

**Tech Stack:** FastAPI, SQLAlchemy 2, Alembic, Postgres 16 (btree_gist), React 19, TanStack Query, React Hook Form + Zod, sonner (toasts, the one new dependency).

**Spec:** the user's v2 request in this session (three batches); this plan restates every requirement it fixes.

## Global Constraints

- Routers HTTP only; services raise `NotFound`/`Forbidden`/`Conflict`/`Unauthorized`, never HTTP errors.
- Every list that can grow is paginated `{items, total}` with `limit` (1–100, default 20) and `offset`; filtering, sorting and search on the server.
- Every frequent query has an index; no N+1 (one query per page plus count).
- Every write to a club or request locks its row (`SELECT … FOR UPDATE`) first and commits once with its event row.
- Frontend data via TanStack Query only; types in `src/lib/types.ts` mirror `app/schemas.py` names exactly.
- One Alembic migration per batch.
- Each non-obvious decision gets a one-line "why" in ARCHITECTURE.md.
- Demo password `demo-password`; keep the 16 demo clubs.

## Review Focus

1. Approving the same request step twice concurrently: exactly one succeeds (row lock + unique `(request_id, round, step)`). Test in `test_request_concurrency.py`.
2. Back-to-back bookings (10:00–11:00 and 11:00–12:00) must both succeed: ranges are `[)`. Test in `test_room_bookings.py`.
3. A booking edited during `changes_requested` into a taken slot gets the same clear 409 as a submit. Test in `test_room_bookings.py`.
4. CSV cells starting with `= + - @` are neutralised (spreadsheet formula injection). Test in `test_club_export.py`.
5. Wrong current password on password change is 403, not 401 (a 401 would trigger the frontend's refresh-and-sign-out flow). Test in `test_profile.py`.

---

## Batch 1: UX polish (commit: "Polish the UI: toasts, confirmations, skeletons, sorting")

### Task 1.1: Server-side sort and the two deferred indexes

**Files:** Modify `app/services/clubs.py`, `app/routers/clubs.py`, `app/models.py`; Create `alembic/versions/<rev>_add_club_owner_and_recency_indexes.py`; Test `tests/test_list_clubs.py`.

**Interfaces:** Produces `GET /api/clubs?sort={name|owner|status|updated}&order={asc|desc}` (default `updated`, `desc`). Replaces `oldest`/`newest` (only our frontend uses them; review queue becomes `sort=updated&order=asc`). Status sorts in lifecycle order (Postgres enum order). Ties break on `id` in the same direction.

- [ ] Tests: `test_sort_by_name_asc_and_desc`, `test_sort_by_owner`, `test_sort_by_status_follows_lifecycle_order`, `test_sort_updated_asc_is_oldest_first`, `test_unknown_sort_is_422`; update existing oldest/newest tests to the new params.
- [ ] Implement `ClubSortField` and `SortOrder` enums; `_ordered(query, field, order)`.
- [ ] Indexes: `idx_clubs_submitter_updated (submitter_id, updated_at)` (a lead's list: filter + sort), `idx_clubs_updated (updated_at, id)` (the All tab, newest first, backward scan).

### Task 1.2: Toasts, confirmations, validation, skeletons, titles, favicon, mobile

**Files:** Create `frontend/src/lib/query-client.ts` (`createQueryClient()` with a `MutationCache` that toasts `mutation.meta.successMessage`), `frontend/src/components/shared/table-skeleton.tsx`, `empty-state.tsx`, move `pager.tsx` to `components/shared/`, `frontend/public/favicon.svg`; Modify `main.tsx`, `test/render-app.tsx`, `App.tsx` (`<Toaster />`), `page-meta.tsx` (appends ` · Club Setup`), every page's `PageMeta`, `note-action-dialog.tsx` (confirm step), `link-dialog.tsx` (RHF + Zod, `<form>` so Enter submits), `clubs-table.tsx` (sortable headers, skeleton rows while loading or while a placeholder page shows, secondary columns hidden below `md`), `club-detail-page.tsx` and `require-auth.tsx` (skeletons), `index.html`.

- [ ] Tests (Vitest): success toast after submit; reject asks to confirm, shows the note, posts only after "Yes, reject"; link dialog shows "Enter a valid URL" inline and Enter submits a valid one; clicking the Club header sorts by name (request carries `sort=name&order=asc`), clicking again flips order; next page shows skeleton rows while loading; document title is "Review queue · Club Setup".
- [ ] Implement. Mutation meta typed via TanStack `Register` augmentation.

### Batch 1 close
- [ ] Full check suite; requesting-code-review on the batch diff; fix; commit.

---

## Batch 2: Product features (commit: "Add user management, comments, activity log, CSV export, profile and landing page")

Migration (one): rename `club_events` → `events` (model `Event`), `club_id` and `to_status` nullable, add `subject_user_id` FK users, CHECK `club_id IS NOT NULL OR subject_user_id IS NOT NULL`, indexes `idx_events_time (created_at DESC, id DESC)`, `idx_events_actor_time (actor_id, created_at DESC)`, `idx_events_type_time (event_type, created_at DESC)`, `idx_users_name (lower(name))` not needed (search is ILIKE, documented trade-off). `EventType(str, Enum)` in `models.py` names the whole vocabulary; column stays a string.

### Task 2.1: User management
**Files:** Create `app/services/users.py`, `app/routers/users.py`, `tests/test_users.py`; frontend `pages/main/users/users-page.tsx` + test.
**Interfaces:** `GET /api/users?q=&role=&limit=&offset=` → `{items: UserListItemOut[], total}` (admin; q matches name or email). `PATCH /api/users/{id}/role {role}` → `UserOut`; event `role_changed` with `subject_user_id`, note `"Club lead → Admin"`.
- [ ] Tests: admin lists/searches/paginates; non-admin 403; change role writes one event; `test_admin_cannot_change_own_role_409`; `test_cannot_change_role_of_user_who_owns_clubs_409` (their clubs could never be submitted again); unknown user 404.

### Task 2.2: Comments (as events)
**Interfaces:** `GET /api/clubs/{id}/comments?limit&offset` → `{items: CommentOut[], total}` newest first; `POST /api/clubs/{id}/comments {body}` (1–2000 chars) → `CommentOut`. Stored as `event_type=comment_posted`, `note=body`. `/clubs/{id}/events` excludes comments and request events.
- [ ] Tests: owner and admin can read/post; other lead 403 on both; blank body 422; club history excludes comments.

### Task 2.3: Activity log
**Interfaces:** `GET /api/activity?actor_id&club_id&event_type&since&until&limit&offset` (admin) → `{items: ActivityOut[], total}`, newest first; each item has `actor_name`, `club_id`, `club_name`, `subject_user_name`, `request_id`. Unknown `event_type` 422.
- [ ] Tests: each filter narrows; date range inclusive of `since`, exclusive of `until`; non-admin 403; one query per page (no per-row lookups).
- [ ] Frontend: `/activity` table; clicking an actor or club name filters by it (scales without a user picker), type select and date inputs, all in the URL.

### Task 2.4: CSV export
**Interfaces:** `GET /api/clubs/export.csv` with the list filters (status, q, sort, order), admin only, columns `id,name,status,owner,documents_provided,documents_total,updated_at`. Service reuses the list's filter/sort query; CSV rendering in the router. `apiDownload(path, filename)` in `api.ts` shares the refresh logic with `apiFetch`.
- [ ] Tests: respects filters; formula-like cells prefixed with `'`; lead 403.

### Task 2.5: Profile
**Interfaces:** `PATCH /api/auth/me {name}` → `UserOut`; `POST /api/auth/me/password {current_password, new_password}` → 204, revokes the user's other refresh tokens.
- [ ] Tests: rename; wrong current password 403 and hash unchanged; success lets the new password log in and revokes other sessions but not the current one.

### Task 2.6: Landing page
- [ ] `/welcome` page (what it does, Sign in, Sign up). Signed-out visit to `/` redirects to `/welcome`; any other protected path still to `/signin`. Vitest for both redirects.

### Batch 2 close
- [ ] Full check suite; code review; fix; commit.

---

## Batch 3: Requests (commit: "Add the request engine with funding and room booking requests")

Migration (one): `userrole` gains `finance_approver`; `CREATE EXTENSION btree_gist`; tables `rooms` (seeded with four UTM-style rooms), `requests`, `funding_line_items`, `request_approvals`; `events.request_id` FK.

- `requests`: `id, club_id FK RESTRICT, request_type (enum funding|room_booking), title, status (enum draft|submitted|in_review|changes_requested|approved|rejected|cancelled), round int, awaiting_role userrole NULL, created_by_id, room_id NULL, booked_during tstzrange NULL, created_at, updated_at`.
  - CHECK booking columns present iff `request_type = 'room_booking'`.
  - CHECK `awaiting_role IS NOT NULL` iff status in (submitted, in_review).
  - EXCLUDE USING gist `(room_id WITH =, booked_during WITH &&) WHERE status IN ('submitted','in_review','changes_requested','approved')`.
  - Indexes `(club_id, updated_at)`, `(awaiting_role, updated_at)`.
- `funding_line_items`: `id, request_id FK CASCADE, position, description, amount_cents CHECK > 0`.
- `request_approvals`: `id, request_id, round, step, approver_id, approved_at, note`, UNIQUE `(request_id, round, step)`.

### Task 3.1: Engine (`app/request_types.py`, `app/services/requests.py`)
**Interfaces:**
- `REQUEST_TYPES: dict[RequestType, RequestTypeDefinition]`, `RequestTypeDefinition(label, details_schema: type[BaseModel], approval_steps: tuple[UserRole, ...])`: funding = (admin, finance_approver); room_booking = (admin,).
- `RequestAction` enum and `ACTIONS: dict[RequestAction, tuple[frozenset[RequestStatus], Actor]]`: submit {draft, changes_requested} owner; start_review {submitted} approver; approve/reject/request_changes {in_review} approver; cancel {draft, submitted, in_review, changes_requested, approved} owner. Approver = the user whose role equals `awaiting_role`.
- `create_request(db, club_id, user, request_type, title, details) -> Request` (owner, club approved); `update_request(...)` (owner, draft or changes_requested); `act_on_request(db, request_id, user, action, note) -> Request`; `list_requests(db, user, filters) -> RequestPage`; `get_request_detail(db, request_id, user)`.
- Visibility: admin all; finance approver requests whose type has a finance step; lead their clubs'.
- Submit starts a new round (`round += 1`) at step 0. Approve inserts a `request_approvals` row for `(round, step=len(approvals this round))`; last step → approved, `awaiting_role = NULL`; else `awaiting_role = next role`.
- [ ] TDD tests (write first): full funding happy path admin → finance; finance cannot act at admin step (403); admin cannot approve finance step (403); approve before start_review 409; reject/request_changes need a note; resubmit after changes starts round 2 and needs both steps again; cancel from approved; rejected/cancelled are final (409); lead of another club 403; requests on an unapproved club 409; every action writes one event with `request_id`; funding total = sum of line items.

### Task 3.2: Room booking
- [ ] Tests: overlapping submit 409 "… is already booked …"; touching ranges OK; rejected or cancelled frees the slot; draft does not hold a slot; edit during changes_requested into a taken slot 409; ends before starts 422; longer than 12 hours 422.
- [ ] `tests/test_request_concurrency.py`: N = 20 drafts for the same room and slot submitted in parallel → exactly 1 succeeds, 19 get Conflict. Also two parallel approvals of one step → one succeeds.

### Task 3.3: Routes and frontend
- Routes: `POST /api/clubs/{id}/requests`, `GET /api/requests` (`club_id`, `status`, `awaiting_me`, `sort=oldest|newest`, paging), `GET/PATCH /api/requests/{id}`, `POST /api/requests/{id}/{submit|start-review|approve|reject|request-changes|cancel}`, `GET /api/requests/{id}/events`, `GET /api/rooms`.
- Frontend: club detail gets Overview/Requests tabs (Requests: table + New request for the owner of an approved club); `/clubs/:id/requests/new` (type picker, title, funding line items with live total or room + start/end); `/requests/:id` (details, approval steps with who/when/note, actions with confirmations, history); review queue gets a Requests card ("awaiting me"); finance approvers land on `/review`; activity log links request events; users page offers Finance approver.
- [ ] Vitest: funding form total; slot-taken 409 shown; finance sees only the requests card; Requests tab hides New request for non-approved clubs.

### Batch 3 close, then wrap-up
- [ ] Seed: rooms from the migration; requests in every status for both types, comments, role change; `demo-finance@example.com`.
- [ ] README + ARCHITECTURE updates; full suite; code review; fix; commit.
- [ ] Restart the app on :8000 from a built frontend; screenshots of every page as each role.
