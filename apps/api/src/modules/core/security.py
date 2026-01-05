from __future__ import annotations

"""Security (v0.2.6)

Fix:
- Do NOT require 'aud' claim unless OIDC_AUDIENCE is explicitly set.
- Provide clear auth errors so API returns 401/403 instead of 500.

Env:
- OIDC_ISSUER (required for verification)
- OIDC_JWKS_URL (optional override for JWKS fetch)
- OIDC_AUDIENCE (optional; if set, aud is enforced)
"""

from dataclasses import dataclass
from typing import Any, Dict, List
import os
import jwt
from jwt import PyJWKClient

class AuthError(Exception):
    pass

@dataclass(frozen=True)
class AuthContext:
    raw_token: str | None
    claims: Dict[str, Any]
    roles: List[str]
    verified: bool

def parse_bearer_token(auth_header: str | None) -> str | None:
    if not auth_header:
        return None
    parts = auth_header.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    return None

def extract_roles(claims: Dict[str, Any]) -> List[str]:
    roles: List[str] = []
    ra = claims.get("realm_access") or {}
    r = ra.get("roles") or []
    if isinstance(r, list):
        roles.extend([str(x) for x in r])
    return roles

class JwtVerifier:
    def __init__(self) -> None:
        self.issuer = os.environ.get("OIDC_ISSUER", "").strip()
        self.audience = os.environ.get("OIDC_AUDIENCE", "").strip() or None
        jwks_override = os.environ.get("OIDC_JWKS_URL", "").strip() or None

        if not self.issuer:
            self.jwks_client = None
            self.verified = False
            return

        jwks_url = jwks_override or (self.issuer.rstrip("/") + "/protocol/openid-connect/certs")
        self.jwks_client = PyJWKClient(jwks_url)
        self.verified = True

    def verify(self, token: str) -> Dict[str, Any]:
        if not self.jwks_client:
            return jwt.decode(token, options={
                "verify_signature": False,
                "verify_aud": False,
                "verify_iss": False,
                "verify_exp": False,
            })

        signing_key = self.jwks_client.get_signing_key_from_jwt(token).key

        options = {"require": ["exp", "iat"]}
        kwargs: Dict[str, Any] = {
            "key": signing_key,
            "algorithms": ["RS256"],
            "issuer": self.issuer,
            "options": options,
        }

        if self.audience:
            # Enforce aud only when explicitly configured
            kwargs["audience"] = self.audience
        else:
            kwargs["options"] = {**options, "verify_aud": False}

        try:
            return jwt.decode(token, **kwargs)
        except jwt.PyJWTError as e:
            raise AuthError(str(e)) from e

_verifier = JwtVerifier()

def build_auth_context(auth_header: str | None) -> AuthContext:
    token = parse_bearer_token(auth_header)
    if not token:
        return AuthContext(raw_token=None, claims={}, roles=[], verified=False)

    claims = _verifier.verify(token)
    roles = extract_roles(claims)
    return AuthContext(raw_token=token, claims=claims, roles=roles, verified=_verifier.verified)
