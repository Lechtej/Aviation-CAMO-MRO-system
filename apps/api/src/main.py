from __future__ import annotations

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
import yaml
from pathlib import Path

OPENAPI_YAML_PATH = Path(__file__).resolve().parent.parent.parent / "openapi.yaml"
# In the container we copy openapi.yaml into /app/openapi.yaml, so fall back:
if not OPENAPI_YAML_PATH.exists():
    OPENAPI_YAML_PATH = Path("/app/openapi.yaml")

def load_openapi_yaml() -> dict:
    data = yaml.safe_load(OPENAPI_YAML_PATH.read_text(encoding="utf-8"))
    return data

app = FastAPI(
    title="Aviation CAMO & MRO API",
    version="0.2.1",
    docs_url="/docs",
    redoc_url="/redoc",
)

_cached_schema: dict | None = None

@app.get("/health", tags=["Core"])
def health():
    return {"status": "ok"}

def custom_openapi():
    global _cached_schema
    if _cached_schema is not None:
        return _cached_schema

    # Prefer the contract file as the source of truth for endpoints & schemas.
    try:
        schema = load_openapi_yaml()
        # Ensure server URL matches runtime
        schema.setdefault("servers", [{"url": "http://localhost:8000", "description": "Local dev"}])
        _cached_schema = schema
        return _cached_schema
    except Exception:
        # Fallback to auto-generated schema if contract can't be loaded
        schema = get_openapi(
            title=app.title,
            version=app.version,
            routes=app.routes,
        )
        _cached_schema = schema
        return _cached_schema

app.openapi = custom_openapi
