# ADR-006: Brak bezpośredniego RBAC bridge z Keycloak

Status: Accepted
Data: 2026-01-10

## Kontekst
RBAC utrzymywany jest w bazie aplikacji. Keycloak pełni rolę IdP.

## Decyzja
Nie implementujemy bridge RBAC z Keycloak.

## Konsekwencje
- DB jako źródło prawdy
- KC tylko JWT
