# PO Guide — AviationCAMO-MRO (v0.2.34)

## 1) Co to jest (3 zdania)
AviationCAMO-MRO to system do zarządzania obsługą techniczną floty (MRO) oraz danymi operacyjnymi (np. części, samoloty, zlecenia).  
System jest „wielofirmowy” — wiele organizacji korzysta z jednej instalacji, ale **każda widzi tylko swoje dane**.  
To jest krytyczne dla bezpieczeństwa i zgodności: dane jednej firmy nie mogą „wyciekać” do innej.

## 2) Najprostsze definicje
- **Tenant**: „firma / organizacja” w systemie (np. linia lotnicza albo firma MRO).  
- **Token**: cyfrowy „bilet wstępu” — potwierdza kim jesteś i jakie masz uprawnienia. Token ma krótki czas ważności (np. 5 minut w testach).  
- **Izolacja tenantów**: zasada, że tenant A nie widzi danych tenant B.  
- **DEV / TEST / PROD**:
  - **DEV**: dla zespołu — szybkie zmiany, częste restarty.
  - **TEST (UAT)**: dla biznesu — testy scenariuszy, stabilniejsze dane.
  - **PROD**: produkcja — realne dane i użytkownicy.

## 3) Jak to działa w praktyce (token + tenant)
W testach zwykle pracujesz na jednym użytkowniku administracyjnym i wskazujesz tenant (np. „Tenant A” albo „Tenant B”).  
Na produkcji wybór tenant jest naturalny: użytkownik loguje się do swojej organizacji, a system automatycznie wie, w jakim tenant działa.

## 4) Uruchomienie systemu (Windows, PO-level)
### Wymagania
- Docker Desktop (z docker compose v2)
- Wolne porty lokalnie: 8000 (API), 8080 (Keycloak)

### Najprościej: start 1 kliknięciem
Uruchom plik:
- `start_and_test_v0.2.34.bat`

Co robi:
1. Buduje i uruchamia kontenery (API, DB, auth, worker)
2. Czeka aż API odpowie na `/health`
3. Wypisuje wynik health

Jeśli coś nie działa:
- uruchom `start_and_test_DIAG_v0.2.34.bat` (pokazuje status i ostatnie logi API)

Uwaga: w v0.2.34 pliki .bat **nie zamykają się automatycznie** — zostają otwarte, żebyś widział komunikaty.

## 5) Co zostało naprawione w tym cyklu (dla biznesu)
Naprawiliśmy błąd krytyczny: tenant B widział rekordy utworzone przez tenant A w Inventory/Parts.  
Po poprawce dane są zapisywane i wyświetlane wyłącznie w obrębie danego tenant.  
Test A vs B został wykonany i przeszedł (brak „wycieku” danych).

## 6) Aircraft: „własność” vs „obsługa” (zrobione w v0.2.30)
- Samolot **należy do linii lotniczej** — to jest tenant „właściciela” (1 tenant, źródło prawdy o samolocie).
- Ten sam samolot może być **obsługiwany przez wiele firm MRO** (różne tenanty MRO).

W tej wersji dodaliśmy prostą funkcjonalność:
1) Właściciel tworzy samolot w swoim tenant.
2) Właściciel „nadaje dostęp” (MRO access) wybranym tenantom MRO.
3) Tenant MRO widzi samolot na liście i może edytować tylko dane techniczne (status / notatki).

### Jak to testować (PowerShell, skrót)
1) Utwórz tenanty (przykład: `ta` i `tb`) tak jak w poprzednim teście.
2) Uruchom bootstrap tabel (raz): `POST /v1/aircraft/_admin/bootstrap` (Platform Admin).
3) Tenant A (owner) tworzy aircraft przez `POST /v1/aircraft` z nagłówkiem `X-Tenant-Id = <tenantA_id>`.
4) Tenant A nadaje dostęp tenantowi B: `POST /v1/aircraft/{aircraft_id}/mro-access`.
5) Tenant B (MRO) robi `GET /v1/aircraft` i widzi samolot (ale nie może go skasować i nie może zmienić rejestracji/typu/SN).

## 7) Maintenance Events (zrobione w v0.2.34)
Cel biznesowy: właściciel (linia lotnicza) rejestruje zdarzenia utrzymaniowe dla samolotu, a przypisane MRO mogą je przeglądać i aktualizować status / notatki MRO.

### Zasady dostępu
- **Owner tenant** może:
  - tworzyć zdarzenia (`POST /maintenance-events`)
  - przeglądać zdarzenia
  - aktualizować wszystkie pola zdarzenia
- **MRO tenant z aktywnym dostępem** może:
  - przeglądać zdarzenia
  - aktualizować tylko: `status`, `mro_notes` (endpoint `PUT`)

### Endpointy
- `GET /v1/aircraft/{aircraft_id}/maintenance-events` — lista zdarzeń (owner lub MRO z dostępem)
- `POST /v1/aircraft/{aircraft_id}/maintenance-events` — tworzenie zdarzenia (tylko owner)
- `PUT /v1/aircraft/{aircraft_id}/maintenance-events/{event_id}` — aktualizacja (owner lub MRO z dostępem; MRO tylko status/mro_notes)

### Wskazówka praktyczna (token)
Token w testach jest krótko ważny. Gdy zobaczysz błąd typu `Invalid token: Signature has expired`, pobierz nowy token i ponów zapytanie.
