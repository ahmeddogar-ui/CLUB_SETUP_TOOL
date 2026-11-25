from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

# Where `npm run build` puts the React app. In development Vite serves it instead.
FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"


def mount_frontend(app: FastAPI, dist: Path) -> None:
    """Serves the built React app from the same origin as the API: real files
    as they are, and index.html for every other path, so a reload on a
    client-side route such as /clubs/3 still loads the app. Register it after
    every other route; it matches everything they don't."""
    dist = dist.resolve()

    @app.get("/{path:path}", include_in_schema=False)
    def serve_frontend(path: str) -> FileResponse:
        if path.startswith("api/"):
            raise HTTPException(status_code=404)
        requested = (dist / path).resolve()
        # is_relative_to: a path like ../app/core/config.py must not escape dist.
        if requested.is_file() and requested.is_relative_to(dist):
            return FileResponse(requested)
        return FileResponse(dist / "index.html")
