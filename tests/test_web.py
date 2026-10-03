"""Browser-facing pages: session login, CSRF, and the club lead's screens."""

import re

import pytest

from app.models import Clubs, ClubStatus, RequirementStatus
from tests.conftest import make_club, provide_all_documents, requirements_for

NO_FOLLOW = {"follow_redirects": False}


def _token(client, path="/login") -> str:
    html = client.get(path, **NO_FOLLOW).text
    match = re.search(r'name="csrf_token" value="([^"]+)"', html)
    assert match, f"no csrf token on {path}"
    return match.group(1)


def web_login(client, user, password="password"):
    return client.post(
        "/login",
        data={"email": user.email, "password": password, "csrf_token": _token(client)},
        **NO_FOLLOW,
    )


def post(client, path, data=None):
    """POST a form with a valid CSRF token (taken from /club/new, any logged-in page)."""
    return client.post(
        path, data={**(data or {}), "csrf_token": _token(client, "/club/new")}, **NO_FOLLOW
    )


@pytest.fixture
def lead_client(client, lead):
    assert web_login(client, lead).status_code == 303
    return client


# --- auth / session / csrf -------------------------------------------------


def test_login_success_redirects_and_opens_session(client, lead):
    response = web_login(client, lead)
    assert response.status_code == 303
    assert response.headers["location"] == "/dashboard"
    assert client.get("/dashboard", **NO_FOLLOW).status_code == 200


def test_login_wrong_password_shows_error(client, lead):
    response = web_login(client, lead, password="nope")
    assert response.status_code == 401
    assert "Incorrect email or password" in response.text
    assert client.get("/dashboard", **NO_FOLLOW).status_code == 303


def test_post_without_csrf_token_is_forbidden(client, lead):
    response = client.post("/login", data={"email": lead.email, "password": "password"}, **NO_FOLLOW)
    assert response.status_code == 403


def test_post_with_wrong_csrf_token_is_forbidden(client, lead):
    _token(client)
    response = client.post(
        "/login",
        data={"email": lead.email, "password": "password", "csrf_token": "forged"},
        **NO_FOLLOW,
    )
    assert response.status_code == 403


def test_logout_clears_session(lead_client):
    assert post(lead_client, "/logout").status_code == 303
    assert lead_client.get("/dashboard", **NO_FOLLOW).status_code == 303


def test_logged_out_pages_redirect_to_login(client):
    for path in ("/dashboard", "/club/new", "/club/1"):
        response = client.get(path, **NO_FOLLOW)
        assert (response.status_code, response.headers["location"]) == (303, "/login")


def test_register_then_login(client):
    response = client.post(
        "/register",
        data={"name": "Ada", "email": "ada@example.com", "password": "pw", "csrf_token": _token(client, "/register")},
        **NO_FOLLOW,
    )
    assert (response.status_code, response.headers["location"]) == (303, "/login?registered=1")


def test_admin_dashboard_redirects_to_queue(client, admin):
    web_login(client, admin)
    assert client.get("/dashboard", **NO_FOLLOW).headers["location"] == "/admin/queue"


# --- dashboard / new club --------------------------------------------------


def test_dashboard_lists_only_own_clubs(lead_client, db, lead, other_lead):
    make_club(db, lead, name="Mine")
    make_club(db, other_lead, name="Theirs")
    page = lead_client.get("/dashboard").text
    assert "Mine" in page and "Theirs" not in page


def test_new_club_creates_and_redirects_to_detail(lead_client, db):
    response = post(lead_client, "/club/new", {"name": "Go Club", "description": "Stones"})
    assert response.status_code == 303
    club = db.query(Clubs).filter(Clubs.name == "Go Club").one()
    assert response.headers["location"] == f"/club/{club.id}"


def test_new_club_blank_name_rerenders_with_error(lead_client, db):
    response = post(lead_client, "/club/new", {"name": "  ", "description": "x"})
    assert response.status_code == 422
    assert "required" in response.text
    assert db.query(Clubs).count() == 0


# --- club detail -----------------------------------------------------------


def test_detail_shows_requirements_blockers_and_history(lead_client, db, lead):
    club = make_club(db, lead)
    page = lead_client.get(f"/club/{club.id}").text
    assert "Chess Club" in page and "constitution" in page
    assert "Before you can submit" in page and "budget" in page
    assert "created" in page


def test_detail_of_someone_elses_club_is_403(lead_client, db, other_lead):
    club = make_club(db, other_lead)
    response = lead_client.get(f"/club/{club.id}")
    assert response.status_code == 403 and "Not your club" in response.text


def test_detail_of_missing_club_is_404(lead_client):
    assert lead_client.get("/club/99999").status_code == 404


# --- document links --------------------------------------------------------


def test_saving_a_link_marks_requirement_submitted(lead_client, db, lead):
    club = make_club(db, lead)
    response = post(
        lead_client, f"/club/{club.id}/requirements/constitution/link", {"link_url": "https://example.com/c"}
    )
    assert response.status_code == 303
    row = requirements_for(db, club.id)["constitution"]
    assert (row.link_url, row.status) == ("https://example.com/c", RequirementStatus.submitted)


def test_bad_link_is_rejected_with_message(lead_client, db, lead):
    club = make_club(db, lead)
    response = post(lead_client, f"/club/{club.id}/requirements/constitution/link", {"link_url": "not a url"})
    assert response.status_code == 422 and "http" in response.text
    assert requirements_for(db, club.id)["constitution"].link_url is None


def test_link_on_submitted_club_is_refused(lead_client, db, lead):
    club = make_club(db, lead, status=ClubStatus.submitted)
    response = post(
        lead_client, f"/club/{club.id}/requirements/constitution/link", {"link_url": "https://example.com/c"}
    )
    assert response.status_code == 409 and "already been submitted" in response.text


# --- submit / resubmit -----------------------------------------------------


def test_submit_blocked_names_missing_items(lead_client, db, lead):
    club = make_club(db, lead)
    response = post(lead_client, f"/club/{club.id}/submit")
    assert response.status_code == 409
    assert "missing" in response.text and "constitution" in response.text


def test_submit_succeeds_and_shows_in_history(lead_client, db, lead):
    club = make_club(db, lead)
    provide_all_documents(db, club.id)
    assert post(lead_client, f"/club/{club.id}/submit").status_code == 303
    db.refresh(club)
    assert club.status == ClubStatus.submitted
    assert "submitted" in lead_client.get(f"/club/{club.id}").text


def test_resubmit_from_changes_requested(lead_client, db, lead):
    club = make_club(db, lead, status=ClubStatus.changes_requested)
    provide_all_documents(db, club.id)
    assert post(lead_client, f"/club/{club.id}/submit").status_code == 303
    db.refresh(club)
    assert club.status == ClubStatus.submitted


# --- admin queue -----------------------------------------------------------


def test_queue_lists_waiting_clubs_oldest_first(client, db, admin, lead):
    first = make_club(db, lead, status=ClubStatus.submitted, name="Older Club")
    second = make_club(db, lead, status=ClubStatus.under_review, name="Newer Club")
    make_club(db, lead, status=ClubStatus.drafting, name="Draft Club")
    make_club(db, lead, status=ClubStatus.approved, name="Done Club")
    first.updated_at = second.updated_at.replace(year=2020)
    db.commit()
    web_login(client, admin)
    page = client.get("/admin/queue").text
    assert "Draft Club" not in page and "Done Club" not in page
    assert page.index("Older Club") < page.index("Newer Club")


def test_queue_is_admin_only(lead_client):
    assert lead_client.get("/admin/queue", **NO_FOLLOW).status_code == 403


def test_queue_requires_login(client):
    assert client.get("/admin/queue", **NO_FOLLOW).headers["location"] == "/login"


# --- admin review actions --------------------------------------------------


@pytest.fixture
def admin_client(client, admin):
    web_login(client, admin)
    return client


def test_admin_sees_review_controls(admin_client, db, lead):
    submitted = make_club(db, lead, status=ClubStatus.submitted)
    assert "Start review" in admin_client.get(f"/club/{submitted.id}").text
    reviewing = make_club(db, lead, status=ClubStatus.under_review)
    page = admin_client.get(f"/club/{reviewing.id}").text
    assert "Approve club" in page and "Request changes" in page


def test_club_lead_sees_no_review_controls(lead_client, db, lead):
    club = make_club(db, lead, status=ClubStatus.under_review)
    page = lead_client.get(f"/club/{club.id}").text
    assert "Approve club" not in page and "Start review" not in page


def test_admin_start_review(admin_client, db, lead):
    club = make_club(db, lead, status=ClubStatus.submitted)
    assert post(admin_client, f"/club/{club.id}/review/start").status_code == 303
    db.refresh(club)
    assert club.status == ClubStatus.under_review


def test_full_review_flow_to_approval(admin_client, db, lead):
    club = make_club(db, lead, status=ClubStatus.under_review, requirement_status=RequirementStatus.submitted)
    blocked = post(admin_client, f"/club/{club.id}/review/approve")
    assert blocked.status_code == 409 and "requirements not all approved" in blocked.text
    for requirement_type in requirements_for(db, club.id):
        post(admin_client, f"/club/{club.id}/requirements/{requirement_type}/approve")
    assert post(admin_client, f"/club/{club.id}/review/approve").status_code == 303
    db.refresh(club)
    assert club.status == ClubStatus.approved


def test_request_changes_needs_a_note_then_records_it(admin_client, db, lead):
    club = make_club(db, lead, status=ClubStatus.under_review)
    blocked = post(admin_client, f"/club/{club.id}/review/request-changes", {"note": "  "})
    assert blocked.status_code == 409 and "note is required" in blocked.text
    assert post(admin_client, f"/club/{club.id}/review/request-changes", {"note": "fix budget"}).status_code == 303
    db.refresh(club)
    assert club.status == ClubStatus.changes_requested
    assert "fix budget" in admin_client.get(f"/club/{club.id}").text


def test_reject_requirement_needs_note_and_shows_it_to_lead(admin_client, client, db, lead):
    club = make_club(db, lead, status=ClubStatus.under_review, requirement_status=RequirementStatus.submitted)
    url = f"/club/{club.id}/requirements/budget/reject"
    assert post(admin_client, url, {"note": ""}).status_code == 422
    assert post(admin_client, url, {"note": "numbers dont add up"}).status_code == 303
    assert requirements_for(db, club.id)["budget"].status == RequirementStatus.rejected
    post(admin_client, "/logout")
    web_login(client, lead)
    assert "numbers dont add up" in client.get(f"/club/{club.id}").text


def test_club_lead_cannot_use_review_routes(lead_client, db, lead):
    club = make_club(db, lead, status=ClubStatus.submitted)
    assert post(lead_client, f"/club/{club.id}/review/start").status_code == 403
    assert post(lead_client, f"/club/{club.id}/requirements/budget/approve").status_code == 403
    db.refresh(club)
    assert club.status == ClubStatus.submitted


def test_unknown_review_action_is_404(admin_client, db, lead):
    club = make_club(db, lead, status=ClubStatus.under_review)
    assert post(admin_client, f"/club/{club.id}/review/explode").status_code == 404


# --- the whole journey, through the browser pages only ---------------------


def test_full_journey_lead_submits_admin_approves(client, db, lead, admin):
    web_login(client, lead)
    post(client, "/club/new", {"name": "Robotics", "description": "We build robots"})
    club = db.query(Clubs).filter(Clubs.name == "Robotics").one()

    for requirement_type in ("constitution", "exec_list", "budget", "advisor_form"):
        post(client, f"/club/{club.id}/requirements/{requirement_type}/link",
             {"link_url": f"https://example.com/{requirement_type}"})
    assert post(client, f"/club/{club.id}/submit").status_code == 303
    post(client, "/logout")

    web_login(client, admin)
    assert "Robotics" in client.get("/admin/queue").text
    post(client, f"/club/{club.id}/review/start")
    for requirement_type in requirements_for(db, club.id):
        post(client, f"/club/{club.id}/requirements/{requirement_type}/approve")
    assert post(client, f"/club/{club.id}/review/approve").status_code == 303
    post(client, "/logout")

    web_login(client, lead)
    page = client.get(f"/club/{club.id}").text
    assert "approved" in page
    for event in ("created", "submitted", "review_started", "requirement_approved"):
        assert event in page
