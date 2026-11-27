"""Operator commands, run against the database in DATABASE_URL.

uv run python -m app.cli make-admin someone@example.com
uv run python -m app.cli seed-demo
"""

import argparse
import sys

from app.database import SessionLocal
from app.exceptions import Conflict
from app.seed import (
    DEMO_ADMIN_EMAIL,
    DEMO_FINANCE_EMAIL,
    DEMO_LEAD_EMAIL,
    DEMO_PASSWORD,
    demo_data_exists,
    seed_demo,
)
from app.services.auth import make_admin


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    commands = parser.add_subparsers(dest="command", required=True)
    make_admin_command = commands.add_parser(
        "make-admin", help="give an existing user the admin role"
    )
    make_admin_command.add_argument("email")
    commands.add_parser(
        "seed-demo", help="create a demo admin, a demo club lead and their clubs"
    )
    args = parser.parse_args(argv)

    if args.command == "seed-demo":
        return _seed_demo()
    return _make_admin(args.email)


def _make_admin(email: str) -> int:
    with SessionLocal() as db:
        try:
            user = make_admin(db, email)
        except Conflict as error:
            print(error, file=sys.stderr)
            return 1
    if user is None:
        print(f"No user with email {email}", file=sys.stderr)
        return 1
    print(f"{user.email} is now an admin")
    return 0


def _seed_demo() -> int:
    with SessionLocal() as db:
        if demo_data_exists(db):
            print("Demo data already exists", file=sys.stderr)
            return 1
        seed_demo(db)
    print(f"Admin:     {DEMO_ADMIN_EMAIL} / {DEMO_PASSWORD}")
    print(f"Finance:   {DEMO_FINANCE_EMAIL} / {DEMO_PASSWORD}")
    print(f"Club lead: {DEMO_LEAD_EMAIL} / {DEMO_PASSWORD}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
