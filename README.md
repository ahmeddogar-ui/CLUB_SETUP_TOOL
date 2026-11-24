# Club Setup Tool

[![CI](https://github.com/ahmeddogar-ui/CLUB_SETUP_TOOL/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/ahmeddogar-ui/CLUB_SETUP_TOOL/actions/workflows/ci.yml)

FastAPI backend (`app/`) and React frontend (`frontend/`) for registering student
clubs and reviewing their paperwork.

Anyone who signs up is a club lead. To make someone an admin (reviewer), have them sign
up, then run:

```sh
uv run python -m app.cli make-admin their@email.com
```

See [TESTING.md](TESTING.md) for how the tests are organised and how to run them.
