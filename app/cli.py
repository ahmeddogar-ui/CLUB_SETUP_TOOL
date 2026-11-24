"""Operator commands, run against the database in DATABASE_URL.

    uv run python -m app.cli make-admin someone@example.com
"""

import argparse
import sys

from app.database import SessionLocal
from app.services.auth import make_admin


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    commands = parser.add_subparsers(dest="command", required=True)
    make_admin_command = commands.add_parser(
        "make-admin", help="give an existing user the admin role"
    )
    make_admin_command.add_argument("email")
    args = parser.parse_args(argv)

    with SessionLocal() as db:
        user = make_admin(db, args.email)
    if user is None:
        print(f"No user with email {args.email}", file=sys.stderr)
        return 1
    print(f"{user.email} is now an admin")
    return 0


if __name__ == "__main__":
    sys.exit(main())
