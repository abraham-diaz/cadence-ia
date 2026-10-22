"""The frontend's TypeScript types are generated from apps/frontend/openapi.json."""

import json
from pathlib import Path

from cadence_ia.cli import main

FRONTEND_SCHEMA = Path(__file__).parents[2] / "frontend" / "openapi.json"


def test_frontend_schema_is_up_to_date(tmp_path):
    """If this fails, run: cadence-ia openapi ../frontend/openapi.json
    and then, in apps/frontend: npm run gen:api"""
    fresh = tmp_path / "openapi.json"
    assert main(["openapi", str(fresh)]) == 0
    assert json.loads(FRONTEND_SCHEMA.read_text(encoding="utf-8")) == json.loads(
        fresh.read_text(encoding="utf-8")
    )
