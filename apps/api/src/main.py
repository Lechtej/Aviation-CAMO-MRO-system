from __future__ import annotations

from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.openapi.utils import get_openapi
import yaml
from pathlib import Path
import os

from modules.core.security import build_auth_context, AuthError
from modules.core.tenant_context import build_tenant_context
from shared.db import current_schema

OPENAPI_YAML_PATH = Path("/app/openapi.yaml")

def load_openapi_yaml() -> dict:
    return yaml.safe_load(OPENAPI_YAML_PATH.read_text(encoding="utf-8"))

app = FastAPI(
    title="Aviation CAMO & MRO API",
    version="0.2.6",
    docs_url="/docs",
    redoc_url="/redoc",
)

_cached_schema: dict | None = None

PUBLIC_PATH_PREFIXES = ("/docs", "/openapi.json", "/redoc")
PUBLIC_PATHS = ("/health",)

def is_public_path(path: str) -> bool:
    if path in PUBLIC_PATHS:
        return True
    return any(path.startswith(p) for p in PUBLIC_PATH_PREFIXES)

def require_role(request: Request, role: str) -> None:
    auth = getattr(request.state, "auth", None)
    if not auth or role not in auth.roles:
        raise HTTPException(status_code=403, detail=f"Missing role: {role}")

@app.middleware("http")
async def tenant_context_middleware(request: Request, call_next):
    # Build auth context (JWT verified with JWKS if OIDC_ISSUER is set)
    try:
        auth = build_auth_context(request.headers.get("Authorization"))
    except AuthError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")
    request.state.auth = auth

    # Require token for /v1/* endpoints (except debug if enabled)
    path = request.url.path
    debug_enabled = os.environ.get("DEBUG_TENANT_HEADER", "false").lower() in ("1", "true", "yes")

    if path.startswith("/v1/"):
        if path == "/v1/_debug/context" and debug_enabled:
            pass
        else:
            if not auth.raw_token:
                raise HTTPException(status_code=401, detail="Missing bearer token")
            # If issuer configured, token must be verified; otherwise dev mode.
            if os.environ.get("OIDC_ISSUER") and not auth.claims:
                raise HTTPException(status_code=401, detail="Invalid token")

    # Tenant resolution rules:
    # 1) If PLATFORM_ADMIN and X-Tenant-Id header is provided => use it
    # 2) Else if token contains tenant_id claim => use it
    # 3) Else if X-Debug-Tenant-Id is provided AND debug enabled => use it
    tenant_id = None
    source = None

    x_tenant = request.headers.get("X-Tenant-Id")
    if x_tenant and ("PLATFORM_ADMIN" in auth.roles):
        tenant_id, source = x_tenant, "header(platform_admin)"

    if not tenant_id:
        tid_claim = auth.claims.get("tenant_id")
        if isinstance(tid_claim, str) and tid_claim:
            tenant_id, source = tid_claim, "token(tenant_id)"

    if not tenant_id and debug_enabled:
        x_debug = request.headers.get("X-Debug-Tenant-Id")
        if isinstance(x_debug, str) and x_debug:
            tenant_id, source = x_debug, "header(debug)"

    if tenant_id:
        ctx = build_tenant_context(tenant_id, source=source or "unknown")
        request.state.tenant = ctx
        current_schema.set(ctx.schema)
        response: Response = await call_next(request)
        response.headers["X-Tenant-Id"] = ctx.tenant_id
        response.headers["X-Tenant-Schema"] = ctx.schema
        response.headers["X-Tenant-Source"] = ctx.source
        return response

    # Default schema (public) if tenant not resolved (health, docs)
    current_schema.set("public")
    return await call_next(request)

@app.get("/health", tags=["Core"])
def health():
    return {"status": "ok"}

@app.get("/v1/_debug/context", tags=["Core"])
def debug_context(request: Request):
    debug_enabled = os.environ.get("DEBUG_TENANT_HEADER", "false").lower() in ("1", "true", "yes")
    if not debug_enabled:
        raise HTTPException(status_code=404, detail="Not found")
    tenant = getattr(request.state, "tenant", None)
    auth = getattr(request.state, "auth", None)
    return {
        "tenant": None if not tenant else {
            "tenant_id": tenant.tenant_id,
            "schema": tenant.schema,
            "source": tenant.source,
        },
        "auth": None if not auth else {
            "has_token": bool(auth.raw_token),
            "roles": auth.roles,
            "verified": auth.verified,
            "claims_keys": sorted(list(auth.claims.keys())),
        }
    }

# Minimal RBAC-protected endpoints to validate security plumbing
@app.get("/v1/tenants", tags=["Core"])
def list_tenants(request: Request):
    require_role(request, "PLATFORM_ADMIN")
    return [{"id": "00000000-0000-0000-0000-000000000000", "name": "DEMO", "status": "ACTIVE"}]

@app.post("/v1/tenants", tags=["Core"], status_code=201)
def create_tenant(request: Request):
    require_role(request, "PLATFORM_ADMIN")
    raise HTTPException(status_code=501, detail="Not implemented (contract-only)")

def custom_openapi():
    global _cached_schema
    if _cached_schema is not None:
        return _cached_schema

    try:
        schema = load_openapi_yaml()
        schema.setdefault("servers", [{"url": "http://localhost:8000", "description": "Local dev"}])
        _cached_schema = schema
        return _cached_schema
    except Exception:
        schema = get_openapi(
            title=app.title,
            version=app.version,
            routes=app.routes,
        )
        _cached_schema = schema
        return _cached_schema

app.openapi = custom_openapi
