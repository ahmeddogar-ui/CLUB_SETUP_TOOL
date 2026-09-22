# Edge Case / Test Checklist — compiled from every ticket to date

No tests have been written yet. This is every edge case that was specified when each
piece was originally built, pulled from the ticket history, organized by feature in
build order. Treat this as the source list for writing real pytest cases — each bullet
should become at least one test, some should become several.

---

## Auth — Register (`POST /auth/register`)
- [ ] Missing a required field (e.g. no name/email/password) → `422`, not a crash.
- [ ] Registering the same email twice → second attempt returns `409`, not `500`, and does not silently create a duplicate row.
- [ ] Response body contains no `password` or `password_hash` field, under any circumstance.
- [ ] Direct DB check: `password_hash` is a real hashed string (not the plaintext password); `role` defaults correctly for a public registration.

## Auth — Login (`POST /auth/login`)
- [ ] Correct email + password → `200`, response is exactly `{"access_token": ..., "token_type": "bearer"}`.
- [ ] Wrong password for a real email → `401` with a **generic** message ("Incorrect email or password") — must not reveal that the email itself was valid.
- [ ] Nonexistent email → same generic `401` message as above (the two failure modes must be indistinguishable to the caller).
- [ ] Email matching is case-sensitivity-safe — confirm registering with one case and logging in with another either both work or both fail consistently, not silently mismatched.

## Auth — Protected routes / `get_current_user`
- [ ] Valid, unexpired token on a protected route → correctly resolves to the right user.
- [ ] Missing `Authorization` header → `401`.
- [ ] Malformed or tampered token → `401`.
- [ ] Expired token → `401` (this only means anything once the access-token expiry is actually short — confirm the expiry claim is being enforced, not just present).
- [ ] After "logout" (clearing/discarding the token client-side) → the same protected route now returns `401`.

## Auth — `require_role`
- [ ] User with the correct role → request proceeds normally.
- [ ] User with the wrong role → `403`.

## Clubs — Create (`POST /clubs`)
- [ ] Missing a required field (e.g. no `name`) → `422`.
- [ ] Creating two separate clubs as the same user → each club gets its own independent, complete set of requirement rows — not shared, not duplicated across clubs.
- [ ] Direct DB check after creation: the club row, all requirement rows (full fixed set — every document-kind and checklist-kind type), and exactly one `created` event row all exist, correctly linked by foreign key.
- [ ] Response body never includes fields beyond what `ClubOut` declares.

## Clubs — List (`GET /clubs`)
- [ ] Club rep with zero clubs → empty list, not an error.
- [ ] Club rep with other users' clubs also existing in the DB → only their own are returned.
- [ ] Admin → clubs from multiple different submitters are all returned.
- [ ] Both branches (admin vs. club_rep) explicitly tested — not just whichever role you happened to be logged in as during dev.

## Clubs — Detail (`GET /clubs/{id}`)
- [ ] Nonexistent club id → `404`.
- [ ] Real club id belonging to a different user, requested as a club_rep → `403`, and the response body leaks none of that club's actual data.
- [ ] Owner or admin requesting the same id → success, full detail returned.
- [ ] Confirm the check order: existence (`404`) is checked before ownership (`403`) — reversing this would leak whether an id exists at all to someone who shouldn't be looking.

## Clubs — Update (`PATCH /clubs/{id}`)
- [ ] Editing a club still in `draft` → succeeds; only the fields actually sent change, everything else stays untouched.
- [ ] Editing a club that's no longer in `draft` → `409`, and a direct DB check afterward confirms nothing actually changed.
- [ ] Submitting an empty body (no fields at all) → succeeds as a harmless no-op, not an error.
- [ ] Attempting to edit someone else's club → `403`, and confirm the `409` status-check logic never even runs in that case (ownership must be checked first).

## Transition service — `attempt_transition` (core state machine)
- [ ] Every legal `(from_status, to_status)` pair succeeds and produces exactly one event row with the correct `from_status`/`to_status`.
- [ ] At least three different **illegal** transitions are rejected — e.g. `draft → approved` (skipping steps), `approved → submitted` (moving out of a terminal state), `rejected → under_review` (moving out of a terminal state).
- [ ] A user whose role doesn't match what a transition requires is rejected, even when the transition itself would otherwise be legal for someone else.
- [ ] Full resubmit loop: `changes_requested → submitted → under_review → changes_requested` a second time — confirm events keep accumulating correctly and nothing gets overwritten or lost.
- [ ] Atomicity: if the event-row write fails for any reason, the status change must not have taken effect either — the two are never allowed to disagree.

## Transition service — guard conditions (`_check_guards`)
- [ ] `draft → submitted` blocked when core info (e.g. `name`) is missing — error message names the specific missing field.
- [ ] `draft → submitted` blocked when a **document-kind** requirement is still unfulfilled (no link provided) — error names that specific requirement type.
- [ ] `draft → submitted` **succeeds** even when **checklist-kind** requirements are still pending — this is the case most likely to be accidentally over-guarded; test it deliberately, don't skip it.
- [ ] `under_review → approved` blocked when any single requirement — document or checklist — isn't yet approved. Test both a requirement that's merely "submitted but not approved" and one that's "rejected" as two separate cases.
- [ ] `under_review → changes_requested` blocked when no note is provided.
- [ ] `under_review → rejected` blocked when no note is provided.
- [ ] A whitespace-only note (e.g. `"   "`) is treated the same as no note — blocked, not accepted.
- [ ] (Once note-handling is wired into the routes) confirm a note is correctly stored on the event row for that specific transition round, and an earlier round's note is never overwritten by a later one.

## Submit endpoint (`POST /clubs/{id}/submit`)
- [ ] A fully-complete draft submits successfully; status becomes `submitted`; an event row exists.
- [ ] An incomplete draft is rejected with the specific missing-item message from the guard check.
- [ ] Submitting an already-submitted club (calling the route a second time) → `409` (an invalid transition, since `submitted → submitted` isn't legal).
- [ ] Attempting to submit someone else's club → `403`, and this check happens before any transition logic runs at all.

## General authorization (applies across every protected route)
- [ ] Any request with no `Authorization` header at all on a protected route → `401`.
- [ ] A club_rep can never fetch or act on another user's club by guessing its id — applies to every club-scoped route, not just the ones already tested above.
- [ ] Attempting to modify a `Requirement`'s `link_url` on a **checklist-kind** row → rejected (checklist items don't have a link field to set; this action doesn't make sense for that kind).

## Refresh tokens (once built — see plan doc's dedicated auth-upgrade session)
- [ ] Login sets the refresh token as an httpOnly cookie (not present in the JSON response body).
- [ ] `POST /auth/refresh` with a valid, unexpired, unrevoked cookie → succeeds, returns a new access token.
- [ ] `POST /auth/refresh` with an expired token → `401`.
- [ ] `POST /auth/refresh` with a revoked token → `401`.
- [ ] `POST /auth/refresh` with no cookie at all → `401`.
- [ ] `POST /auth/logout` → the corresponding row's `revoked` flag is set; a subsequent `/auth/refresh` attempt with that same (now-revoked) token fails.

---

## Notes for whoever runs these (Claude Code)
- Use FastAPI's `TestClient` for anything going through the HTTP layer (routes); call the transition service's functions directly for the pure state-machine/guard tests — no need to go through HTTP for those.
- Use a dedicated test database with a per-test transaction rollback fixture, so tests don't pollute each other or the real dev database.
- Where a bullet says "confirm X happens before Y" (ownership before status checks, existence before ownership, etc.), write that as its own explicit test — don't just infer the ordering is correct because the individual checks pass separately.
- This list reflects what was *specified* when each piece was built. If the actual code has drifted from spec anywhere (a genuine possibility across a multi-session build — flag any place a test reveals a mismatch with what's described here) rather than assuming the code is correct and adjusting the test to match.
