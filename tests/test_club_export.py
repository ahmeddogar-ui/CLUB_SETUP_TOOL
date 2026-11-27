"""GET /clubs/export.csv: the admin's filtered club list as a CSV download."""

import csv
import io
from datetime import UTC, datetime, timedelta

from app.models import Clubs, ClubStatus
from tests.conftest import auth, create_club

EXPECTED_HEADER = [
    "id",
    "name",
    "status",
    "owner",
    "documents_provided",
    "documents_total",
    "updated_at",
]
BASE = datetime(2026, 1, 1, tzinfo=UTC)


def set_state(db, club_id, status, days_ago):
    club = db.get(Clubs, club_id)
    club.status = status
    club.updated_at = BASE - timedelta(days=days_ago)
    db.commit()


def export_csv(client, user, params=()):
    return client.get("/api/clubs/export.csv", params=list(params), headers=auth(user))


def rows_of(response, ours):
    """Parsed rows for the clubs these tests created, in the order exported. An
    admin exports every club in the database, so ignore any others."""
    rows = list(csv.DictReader(io.StringIO(response.content.decode("utf-8-sig"))))
    return [row for row in rows if int(row["id"]) in ours]


def test_header_row_is_exact(client, admin):
    response = export_csv(client, admin)

    assert response.status_code == 200
    assert next(csv.reader(io.StringIO(response.content.decode("utf-8-sig")))) == EXPECTED_HEADER


def test_exports_club_fields(client, admin, lead):
    club = create_club(client, lead, name="Chess Club")

    [row] = rows_of(export_csv(client, admin), {club["id"]})

    assert row["name"] == "Chess Club"
    assert row["status"] == "drafting"
    assert row["owner"] == lead.name
    assert row["documents_provided"] == "0"
    assert row["documents_total"] == "4"
    assert datetime.fromisoformat(row["updated_at"]).tzinfo is not None


def test_respects_status_filter(client, db, admin, lead):
    drafting = create_club(client, lead, name="Drafty")["id"]
    submitted = create_club(client, lead, name="Sent")["id"]
    set_state(db, submitted, ClubStatus.submitted, days_ago=1)

    response = export_csv(client, admin, [("status", "submitted")])

    assert [row["id"] for row in rows_of(response, {drafting, submitted})] == [
        str(submitted)
    ]


def test_respects_search(client, admin, lead):
    chess = create_club(client, lead, name="Chess Club")["id"]
    film = create_club(client, lead, name="Film Club")["id"]

    response = export_csv(client, admin, [("q", "chess")])

    assert [row["id"] for row in rows_of(response, {chess, film})] == [str(chess)]


def test_respects_sort_and_order(client, db, admin, lead):
    first = create_club(client, lead, name="First")["id"]
    second = create_club(client, lead, name="Second")["id"]
    set_state(db, first, ClubStatus.submitted, days_ago=1)
    set_state(db, second, ClubStatus.submitted, days_ago=5)
    ours = {first, second}

    def exported_ids(sort, order):
        params = [("sort", sort), ("order", order)]
        return [row["id"] for row in rows_of(export_csv(client, admin, params), ours)]

    assert exported_ids("updated", "asc") == [str(second), str(first)]
    assert exported_ids("updated", "desc") == [str(first), str(second)]
    assert exported_ids("name", "asc") == [str(first), str(second)]
    assert exported_ids("name", "desc") == [str(second), str(first)]


def test_exports_every_matching_club_without_paging(client, admin, lead):
    created = {create_club(client, lead, name=f"Club {n}")["id"] for n in range(25)}

    assert len(rows_of(export_csv(client, admin), created)) == 25


def test_formula_like_text_is_prefixed_with_a_quote(client, admin, lead):
    club = create_club(client, lead, name='=HYPERLINK("http://evil")')

    [row] = rows_of(export_csv(client, admin), {club["id"]})

    assert row["name"] == '\'=HYPERLINK("http://evil")'


def test_is_sent_as_a_csv_attachment(client, admin):
    response = export_csv(client, admin)

    assert response.headers["content-type"] == "text/csv; charset=utf-8"
    assert response.headers["content-disposition"] == 'attachment; filename="clubs.csv"'


def test_club_lead_is_forbidden(client, lead):
    assert export_csv(client, lead).status_code == 403


def test_requires_auth(client):
    assert client.get("/api/clubs/export.csv").status_code == 401


def test_starts_with_a_byte_order_mark_for_excel(client, admin):
    """Without it Excel reads the UTF-8 file as Windows-1252 and garbles
    names like "Société de débat"."""
    response = client.get("/api/clubs/export.csv", headers=auth(admin))
    assert response.content.startswith(b"\xef\xbb\xbf")
