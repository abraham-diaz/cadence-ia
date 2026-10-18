"""Serve the compiled React app (apps/frontend/dist) from FastAPI.

In production a single service answers both the API and the web app.
"""

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse


def mount_frontend(app: FastAPI, static_dir: Path) -> None:
    """Serve files from `static_dir`, falling back to index.html.

    The fallback lets React Router handle URLs like /sesion/123 when they are
    opened directly. Must be called after every API route is registered,
    because this catch-all route would otherwise shadow them.
    """
    root = static_dir.resolve()
    index = root / "index.html"
    if not index.is_file():
        raise RuntimeError(f"No index.html in {root}: build the frontend first")

    @app.get("/{path:path}", include_in_schema=False)
    def frontend(path: str) -> FileResponse:
        if path == "api" or path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found")

        file = (root / path).resolve()
        if path and file.is_file() and file.is_relative_to(root):
            # Vite puts a content hash in asset names, so they can be cached forever.
            cache = "public, max-age=31536000, immutable" if path.startswith("assets/") else "no-cache"
            return FileResponse(file, headers={"Cache-Control": cache})
        # index.html must not be cached, or the phone keeps an old version.
        return FileResponse(index, headers={"Cache-Control": "no-cache"})
