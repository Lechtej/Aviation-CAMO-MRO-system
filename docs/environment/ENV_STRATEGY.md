# ENV Strategy — Local-first + Server as Remote (backup/DR)

## Cel (decyzja)
- **Repo = jedyne źródło prawdy** (compose, kod, migracje, docs, realm JSON, seed).
- **Local-first = kanon** (praca nie może zależeć od dostępności dostawcy).
- **Server-dev = profil routingu** (hosty/domeny), a nie osobny „inny system”.

## Definicje
- **Environment profile**: zestaw wartości w `.env.<profile>` (poza repo) + sposób uruchomienia.
- **Stateful data**: DB + Keycloak realm/config + seed. Odtwarzalne skryptami/artefaktami.
- **Deterministyczny bootstrap**: 0 klików, 0 ręcznych zmian, 0 „pamięci plemiennej”.

## Twarde reguły
1) **Nie kopiujemy sekretów** między środowiskami. Każdy profil ma własny `.env.*`.
2) **Nie kopiujemy danych 1:1** (chyba że kontrolowany snapshot do testów).
3) **Keycloak realm jest importowany** (JSON w repo) + ewentualne nadpisania per env tylko przez jawne kroki.
4) **Naming stability**:
   - `KC_REALM=aviation`
   - `OIDC_CLIENT_ID=aviation-api`
   - API ścieżki nie zależą od env
   - env różni się tylko `*_BASE_URL` (routing) i sekretami.

## Profile (MVP)
### local (kanon)
- API: `http://localhost:8000`
- Keycloak: `http://localhost:8080`
- UI: `http://localhost:3000`
- Compose: `infra/docker/docker-compose.yml`
- Keycloak bootstrap: import `infra/docker/keycloak/realm-aviation.json`

### server-dev (remote)
- identyczny kod/compose, różne `*_BASE_URL` (host/domena).
- różne sekrety (`DB_PASSWORD`, `KC_ADMIN_PASSWORD` itd.)
- po powrocie serwera: reconcile (patrz niżej)

## Kontrakt konfiguracji (.env)
- `.env.local`, `.env.server-dev` → **gitignored**
- `.env.example` → **w repo** (kanoniczne klucze)

| Klucz | Znaczenie | Przykład (local) |
|---|---|---|
| `ENV_PROFILE` | identyfikator profilu | `local` |
| `API_BASE_URL` | base URL API | `http://localhost:8000` |
| `KC_BASE_URL` | base URL Keycloak | `http://localhost:8080` |
| `KC_REALM` | realm | `aviation` |
| `UI_BASE_URL` | base URL UI (redirect_uri) | `http://localhost:3000` |
| `OIDC_CLIENT_ID` | clientId do tokenów | `aviation-api` |
| `TENANT_MODE` | tryb multi-tenant | `schema-per-tenant` |

Sekrety (tylko w `.env.*`): `DB_PASSWORD`, `KC_ADMIN_PASSWORD`, `OIDC_TEST_USERNAME`, `OIDC_TEST_PASSWORD`.

## Odtwarzalność (bootstrap)
Minimalny deterministic bootstrap:
1) `docker compose up -d` (local)
2) Keycloak realm import (w kontenerze, `--import-realm`)
3) seed: **przez API** endpointem bootstrap (jeśli dostępny): `POST /v1/admin/bootstrap`
4) smoke tests: token → `/v1/roles` → `/v1/tenants`

Skrypty referencyjne:
- `scripts/bootstrap_local.sh`
- `scripts/smoke_auth.sh`
- `scripts/smoke_api.sh`

## Reconcile po outage / powrocie serwera (bez „rzeźby”)
Cel: dopasować „jak jest na serwerze” do kanonu repo, **bez kopiowania sekretów**.

1) Z serwera pozyskać (bez sekretów):
   - `docker compose config` (wygenerowana konfiguracja)
   - export realm JSON
   - lista hostów/domen (API/KC/UI)
2) Diff vs repo:
   - jeśli różnią się tylko URL → aktualizujemy `.env.server-dev`
   - jeśli różni się realm/clients → decyzja: ujednolicić do `aviation`/`aviation-api` lub utrzymać osobny client i mapować w `.env.server-dev`
3) Smoke testy na server-dev (jak na local).

