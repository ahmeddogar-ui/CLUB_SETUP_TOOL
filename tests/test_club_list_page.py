"""GET /api/clubs as a page: owner and progress per club, search, pagination,
and the per-status counts behind the admin's summary cards."""

import pytest
from sqlalchemy import event

from app.models import ClubStatus, RequirementStatus, UserRole
from tests.conftest import auth, make_club, make_user


def get_page(client, user, **params):
    response = client.get("/api/clubs", params=params, headers=auth(user))
    assert response.status_code == 200, response.text
    return response.json()


def names(page):
    return [club["name"] for club in page["items"]]


# --- what each club carries ---------------------------------------------------


def test_each_club_carries_its_owner_and_last_update(client, db, lead, admin):
    club = make_club(db, lead, name="Owner Check Club")
    [item] = get_page(client, admin, q="Owner Check Club")["items"]
    assert item["owner_name"] == lead.name
    assert item["updated_at"].startswith(club.updated_at.date().isoformat())


def test_document_progress_counts_provided_documents_only(client, db, lead):
    # make_club with requirement_status=submitted marks all six requirements
    # submitted; only the four documents count towards progress.
    make_club(db, lead, name="Ready", requirement_status=RequirementStatus.submitted)
    make_club(db, lead, name="Fresh")
    page = get_page(client, lead)
    progress = {
        club["name"]: (club["documents_provided"], club["documents_total"])
        for club in page["items"]
    }
    assert progress == {"Ready": (4, 4), "Fresh": (0, 4)}


def test_rejected_documents_do_not_count_as_provided(client, db, lead):
    make_club(db, lead, requirement_status=RequirementStatus.rejected)
    [club] = get_page(client, lead)["items"]
    assert club["documents_provided"] == 0


# --- search --------------------------------------------------------------------


def test_search_matches_part_of_the_name_in_any_case(client, db, lead):
    make_club(db, lead, name="Chess Club")
    make_club(db, lead, name="Film Society")
    assert names(get_page(client, lead, q="CHESS")) == ["Chess Club"]
    assert names(get_page(client, lead, q="soc")) == ["Film Society"]


@pytest.mark.parametrize("wildcard", ["%", "_"])
def test_search_treats_sql_wildcards_literally(client, db, lead, wildcard):
    make_club(db, lead, name="Chess Club")
    make_club(db, lead, name=f"100{wildcard} Club")
    assert names(get_page(client, lead, q=wildcard)) == [f"100{wildcard} Club"]


def test_search_longer_than_the_maximum_is_422(client, lead):
    response = client.get("/api/clubs", params={"q": "a" * 101}, headers=auth(lead))
    assert response.status_code == 422


# --- pagination ------------------------------------------------------------------


def test_pages_split_the_list_and_report_the_total(client, db, lead):
    for number in range(5):
        make_club(db, lead, name=f"Club {number}")
    first = get_page(client, lead, limit=2, offset=0)
    second = get_page(client, lead, limit=2, offset=2)
    last = get_page(client, lead, limit=2, offset=4)
    assert first["total"] == second["total"] == last["total"] == 5
    assert names(first) + names(second) + names(last) == [
        f"Club {number}" for number in range(5)
    ]


def test_a_page_past_the_end_is_empty_but_keeps_the_total(client, db, lead):
    make_club(db, lead)
    page = get_page(client, lead, limit=10, offset=10)
    assert page["items"] == []
    assert page["total"] == 1


def test_total_counts_only_the_filtered_clubs(client, db, lead):
    make_club(db, lead, name="Chess Club", status=ClubStatus.submitted)
    make_club(db, lead, name="Chess Society")
    make_club(db, lead, name="Film Society", status=ClubStatus.submitted)
    assert get_page(client, lead, q="chess")["total"] == 2
    assert get_page(client, lead, status="submitted")["total"] == 2
    assert get_page(client, lead, q="chess", status="submitted")["total"] == 1


@pytest.mark.parametrize("params", [{"limit": 0}, {"limit": 101}, {"offset": -1}])
def test_out_of_range_paging_is_422(client, lead, params):
    response = client.get("/api/clubs", params=params, headers=auth(lead))
    assert response.status_code == 422


def test_a_page_takes_the_same_number_of_queries_however_many_clubs_it_holds(
    client, db, engine, lead
):
    statements: list[str] = []

    def count(conn, cursor, statement, *args):
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", count)
    try:
        make_club(db, lead)
        statements.clear()
        get_page(client, lead)
        with_one_club = len(statements)

        for _ in range(4):
            make_club(db, lead)
        statements.clear()
        get_page(client, lead)
        with_five_clubs = len(statements)
    finally:
        event.remove(engine, "before_cursor_execute", count)

    assert with_five_clubs == with_one_club


# --- status counts -----------------------------------------------------------------


def test_status_counts_cover_every_status_for_a_lead(client, db, lead, other_lead):
    make_club(db, lead, status=ClubStatus.submitted)
    make_club(db, lead, status=ClubStatus.submitted)
    make_club(db, lead, status=ClubStatus.approved)
    make_club(db, other_lead, status=ClubStatus.rejected)

    counts = get_page(client, lead)["status_counts"]

    assert counts == {
        "drafting": 0,
        "submitted": 2,
        "under_review": 0,
        "changes_requested": 0,
        "approved": 1,
        "rejected": 0,
    }


def test_status_counts_ignore_the_search_and_status_filters(client, db, lead):
    make_club(db, lead, name="Chess Club", status=ClubStatus.submitted)
    make_club(db, lead, name="Film Society")
    counts = get_page(client, lead, q="chess", status="submitted")["status_counts"]
    assert counts["drafting"] == 1
    assert counts["submitted"] == 1


def test_admin_status_counts_include_every_owner(client, db, lead, other_lead, admin):
    before = get_page(client, admin)["status_counts"]
    make_club(db, lead, status=ClubStatus.under_review)
    make_club(db, other_lead, status=ClubStatus.under_review)
    after = get_page(client, admin)["status_counts"]
    assert after["under_review"] - before["under_review"] == 2


def test_admin_sees_other_owners_in_the_list(client, db, admin):
    owner = make_user(db, UserRole.club_lead)
    make_club(db, owner, name="Someone Else's Club")
    [club] = get_page(client, admin, q="Someone Else's Club")["items"]
    assert club["owner_name"] == owner.name
