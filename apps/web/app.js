
// BUILD_MARKER_2026-01-17_145813
// CANONICAL_UI_JS: PASS_UI_2026-01-17_143333
// DO NOT EDIT WITHOUT NEW BACKUP
// AviationCAMO-MRO — UI v1 + Auth (Keycloak OIDC code + PKCE)
// Views (read-only):
// - CAMO / Aircraft (list)            -> requires CAMO roles
// - CAMO / Maintenance Events (list)  -> requires CAMO or MRO roles (tenant access rules still apply in backend)
// - MRO  / Maintenance Events (list)  -> requires CAMO or MRO roles
//
// NOTE: UI communicates ONLY via API (REST). No backend bypass.
//
// Auth model:
// - Keycloak realm roles (realm_access.roles) are used for UI navigation and API RBAC.
// - Minimal role mapping for v0.2.44:
//     CAMO: CAMO_PLANNER, CAMO_ENGINEER (+ TENANT_ADMIN, PLATFORM_ADMIN)
//     MRO : MAINT_PLANNER, MECHANIC, CERTIFYING_STAFF (+ TENANT_ADMIN, PLATFORM_ADMIN)

function storeTenantFromResponse(r) {
  try {
    if (!r || !r.headers) return;
    const tid = r.headers.get("x-tenant-id");
    const tschema = r.headers.get("x-tenant-schema");
    if (tid) localStorage.setItem("tenant_uuid", tid);
    if (tschema) localStorage.setItem("tenant_schema", tschema);
  } catch (e) {}
}

(function () {
  const $ = (id) => document.getElementById(id);

  const baseUrlEl = $("baseUrl");
  const btnSaveEl = $("btnSave");
  const btnRefreshEl = $("btnRefresh");

  const btnLoginEl = $("btnLogin");
  const btnLogoutEl = $("btnLogout");
  const authUserEl = $("authUser");

  const viewTitleEl = $("viewTitle");
  const viewSubEl = $("viewSub");
  const apiDotEl = $("apiDot");
  const apiStatusEl = $("apiStatus");

  const contentMetaEl = $("contentMeta");
  const contentBodyEl = $("contentBody");
  const contentHintEl = $("contentHint");

  const navCamoAircraft = $("nav-camo-aircraft");
  const navCamoEvents = $("nav-camo-events");
  const navMroEvents = $("nav-mro-events");

  const DEFAULT_BASE_URL = "https://api.forgemotionsystems.com";
  const LS_KEY = "aviationcamo_ui_v1";
  const LS_AUTH_KEY = "aviationcamo_auth_v1";

  // Keycloak (defaults; can be overridden via localStorage settings if needed later)
  const KC = {
    baseUrl: "https://auth.forgemotionsystems.com",
    realm: "aviation",
    clientId: "aviation-ui",
  };

  // ---------------------------
  // Utilities
  // ---------------------------
  function safeJsonParse(s, fallback) {
    try { return JSON.parse(s); } catch { return fallback; }
  }

  function normalizeBaseUrl(v) {
    const s = (v || "").trim();
    if (!s) return DEFAULT_BASE_URL;
    return s.replace(/\/+$/, "");
  }

  function setApiStatus(ok, message) {
    apiDotEl.classList.remove("ok", "bad");
    if (ok === true) apiDotEl.classList.add("ok");
    if (ok === false) apiDotEl.classList.add("bad");
    apiStatusEl.textContent = message;
  }

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#39;"
    }[c]));
  }

  // JWT decode (no validation; API validates signature)
  function decodeJwt(token) {
    if (!token || token.split(".").length < 2) return null;
    try {
      const payload = token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
      const json = decodeURIComponent(atob(payload).split("").map(c => "%" + ("00" + c.charCodeAt(0).toString(16)).slice(-2)).join(""));
      return JSON.parse(json);
    } catch {
      return null;
    }
  }

  // ---------------------------
  // Auth (OIDC code + PKCE)
  // ---------------------------
  function randomString(len) {
    const charset = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~";
    const arr = new Uint8Array(len);
    crypto.getRandomValues(arr);
    return Array.from(arr, (x) => charset[x % charset.length]).join("");
  }

  async function sha256base64url(input) {
    const data = new TextEncoder().encode(input);
    const hash = await crypto.subtle.digest("SHA-256", data);
    const bytes = Array.from(new Uint8Array(hash));
    const b64 = btoa(String.fromCharCode.apply(null, bytes));
    return b64.replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  }

  function authEndpoints() {
    const base = KC.baseUrl.replace(/\/+$/, "");
    const realm = encodeURIComponent(KC.realm);
    return {
      auth: `${base}/realms/${realm}/protocol/openid-connect/auth`,
      token: `${base}/realms/${realm}/protocol/openid-connect/token`,
      logout: `${base}/realms/${realm}/protocol/openid-connect/logout`,
    };
  }

  function loadAuth() {
    return safeJsonParse(localStorage.getItem(LS_AUTH_KEY) || "null", null);
  }

  function saveAuth(auth) {
    localStorage.setItem(LS_AUTH_KEY, JSON.stringify(auth));
  }

  function clearAuth() {
    localStorage.removeItem(LS_AUTH_KEY);
  }

  function isTokenValid(auth) {
    if (!auth || !auth.access_token) return false;
    if (!auth.expires_at) return true; // fallback
    return Date.now() < auth.expires_at - 10_000; // 10s buffer
  }

  function rolesFromAuth(auth) {
    const claims = ((auth && auth.access_token) ? decodeJwt(auth.access_token) : null) || ((auth && auth.id_token) ? decodeJwt(auth.id_token) : null) || {};
    const ra = (claims && claims.realm_access) || {};
    const roles = Array.isArray(ra.roles) ? ra.roles.map(String) : [];
    return { roles: new Set(roles), claims };
  }

  function hasAny(roleSet, prefixesOrNames) {
    for (const r of roleSet) {
      for (const x of prefixesOrNames) {
        if (x.endsWith("_")) {
          if (r.startsWith(x)) return true;
        } else {
          if (r === x) return true;
        }
      }
    }
    return false;
  }

  function canSeeCamo(roleSet) {
    return hasAny(roleSet, ["CAMO_", "TENANT_ADMIN", "PLATFORM_ADMIN"]);
  }

  function canSeeMro(roleSet) {
    return hasAny(roleSet, ["MAINT_", "MECHANIC", "CERTIFYING_STAFF", "TENANT_ADMIN", "PLATFORM_ADMIN"]);
  }

  function setNavVisibility(roleSet) {
    const camo = canSeeCamo(roleSet);
    const mro = canSeeMro(roleSet);

    navCamoAircraft.style.display = camo ? "" : "none";
    navCamoEvents.style.display = camo ? "" : "none";
    navMroEvents.style.display = mro ? "" : "none";
  }

  function updateAuthUi() {
    const auth = loadAuth();
    const ok = isTokenValid(auth);
    btnLoginEl.style.display = ok ? "none" : "";
    btnLogoutEl.style.display = ok ? "" : "none";

    if (!ok) {
      authUserEl.textContent = "Not logged in";
      setNavVisibility(new Set()); // hide protected nav
      return;
    }

    const { roles, claims } = rolesFromAuth(auth);
    const user = ((claims && claims.preferred_username)) || ((claims && claims.name)) || "user";
    authUserEl.textContent = `${user}`;
    setNavVisibility(roles);
  }

  async function login() {
    const endpoints = authEndpoints();
    const redirectUri = window.location.origin + window.location.pathname; // keep hash routes
    const state = randomString(24);
    const verifier = randomString(64);
    const challenge = await sha256base64url(verifier);

    // Store transient data in sessionStorage
    sessionStorage.setItem("oidc_state", state);
    sessionStorage.setItem("oidc_verifier", verifier);
    sessionStorage.setItem("oidc_redirect", redirectUri);

    const params = new URLSearchParams({
      client_id: KC.clientId,
      response_type: "code",
      scope: "openid profile",
      redirect_uri: redirectUri,
      state,
      code_challenge: challenge,
      code_challenge_method: "S256",
    });

    window.location.href = `${endpoints.auth}?${params.toString()}`;
  }

  async function handleAuthCallbackIfPresent() {
    const u = new URL(window.location.href);
    const code = u.searchParams.get("code");
    const state = u.searchParams.get("state");
    const err = u.searchParams.get("error");
    const errDesc = u.searchParams.get("error_description");

    if (err) {
      // Cleanup URL
      u.searchParams.delete("error");
      u.searchParams.delete("error_description");
      window.history.replaceState({}, document.title, u.toString());
      throw new Error(`OIDC error: ${err}${errDesc ? " - " + errDesc : ""}`);
    }

    if (!code) return;

    const expectedState = sessionStorage.getItem("oidc_state");
    const verifier = sessionStorage.getItem("oidc_verifier");
    const redirectUri = sessionStorage.getItem("oidc_redirect") || (window.location.origin + window.location.pathname);

    if (!expectedState || !verifier || !state || state !== expectedState) {
      throw new Error("Invalid OIDC state");
    }

    const endpoints = authEndpoints();
    const body = new URLSearchParams({
      grant_type: "authorization_code",
      client_id: KC.clientId,
      code,
      redirect_uri: redirectUri,
      code_verifier: verifier,
    });

    const r = await fetch(endpoints.token, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: body.toString(),
    });

    if (!r.ok) {
      const t = await r.text();
      throw new Error(`Token exchange failed (${r.status}): ${t}`);
    }

    const tok = await r.json();
    const expiresIn = Number(tok.expires_in || 0);
    const auth = {
      access_token: tok.access_token,
      id_token: tok.id_token,
      refresh_token: tok.refresh_token,
      expires_at: Date.now() + expiresIn * 1000,
    };
    saveAuth(auth);

// === TENANT CONTEXT BOOTSTRAP (Incognito-safe) ===
// Ensure tenant_uuid exists right after login, before any data loads.
try {
  const baseUrl =
    (typeof getBaseUrl === "function" ? getBaseUrl() : "") ||
    (typeof baseUrlEl !== "undefined" && baseUrlEl ? normalizeBaseUrl(baseUrlEl.value) : "") ||
    normalizeBaseUrl(DEFAULT_BASE_URL);

  const already = localStorage.getItem("tenant_uuid") || localStorage.getItem("tenant_id");
  if (baseUrl && !already) {
    const r = await fetch(baseUrl + "/v1/tenants", {
      headers: { "Authorization": "Bearer " + auth.access_token },
    });

    if (r.ok) {
      const arr = await r.json();
      const pick =
        (arr || []).find(t => String((t && t.code) ? t.code : "").toLowerCase() !== "unk") ||
        (arr || [])[0];

      const tid = ((pick && pick.id)) || ((pick && pick.tenant_id)) || ((pick && pick.uuid));
      const schema = ((pick && pick.schema_name)) || ((pick && pick.schema)) || ((pick && pick.tenant_schema));

      if (tid) {
        localStorage.setItem("tenant_uuid", String(tid));   // SOURCE OF TRUTH
        localStorage.setItem("tenant_id", String(tid));     // compat
      }
      if (schema) localStorage.setItem("tenant_schema", String(schema));
    } else {
      console.warn("Tenant bootstrap: /v1/tenants not ok:", r.status);
    }
  }
} catch (e) {
  console.warn("Tenant bootstrap failed (non-fatal):", e);
}


    // Cleanup transient + URL params
    sessionStorage.removeItem("oidc_state");
    sessionStorage.removeItem("oidc_verifier");
    sessionStorage.removeItem("oidc_redirect");

    u.searchParams.delete("code");
    u.searchParams.delete("state");
    window.history.replaceState({}, document.title, u.toString());
  }

  async function logout() {
    const auth = loadAuth();
    clearAuth();
    updateAuthUi();

    // Optional: redirect to Keycloak logout (best effort)
    try {
      const endpoints = authEndpoints();
      const redirectUri = window.location.origin + window.location.pathname;
      const params = new URLSearchParams({
        post_logout_redirect_uri: redirectUri,
      });
      if (auth?.id_token) params.set("id_token_hint", auth.id_token);
      window.location.href = `${endpoints.logout}?${params.toString()}`;
    } catch {
      // ignore
    }
  }

  // ---------------------------
  // API calls
  // ---------------------------
  async function pingApi(baseUrl) {
    try {
      const r = await fetch(baseUrl + "/docs", { method: "GET" });
      if (r.ok) return true;
      return false;
    } catch {
      return false;
    }
  }


// Tenant discovery (Incognito-safe): when tenant_id is missing, ask API for /v1/tenants (Authorization-only)
async function discoverTenantFromTenantsEndpoint(baseUrl, accessToken) {
  try {
    const r = await fetch(baseUrl + "/v1/tenants", {
      method: "GET",
      headers: { "Authorization": "Bearer " + accessToken }
    });
    if (!r.ok) return null;

    const list = await r.json();
    if (!Array.isArray(list) || list.length === 0) return null;

    // Prefer non-UNK tenant if present, otherwise take first.
    const pick =
      list.find(t => (t?.code && String(t.code).toLowerCase() !== "unk") && (t?.status ? String(t.status).toLowerCase() === "active" : true)) ||
      list.find(t => (t?.code && String(t.code).toLowerCase() !== "unk")) ||
      list[0];

    const tid = ((pick && pick.tenant_id)) || ((pick && pick.id)) || ((pick && pick.uuid));
    const schema = ((pick && pick.schema_name)) || ((pick && pick.schema)) || ((pick && pick.tenant_schema));

    if (tid) {
      localStorage.setItem("tenant_id", String(tid));
      localStorage.setItem("tenant_uuid", String(tid)); // legacy fallback
    }
    if (schema) localStorage.setItem("tenant_schema", String(schema));

    return tid ? String(tid) : null;
  } catch (e) {
    return null;
  }
}


async function apiFetch(baseUrl, path) {
  const auth = loadAuth();
  const headers = {};

  if (isTokenValid(auth)) {
    headers["Authorization"] = "Bearer " + auth.access_token;
  }

  // Tenant context (UUID) — required by API
let tid =
  localStorage.getItem("tenant_id") ||
  localStorage.getItem("tenant_uuid"); // legacy fallback

// Incognito-safe: if missing tenant_id, discover it from /v1/tenants using Authorization only
if (!tid && isTokenValid(auth) && path !== "/v1/tenants") {
  await discoverTenantFromTenantsEndpoint(baseUrl, auth.access_token);
  tid = localStorage.getItem("tenant_id") || localStorage.getItem("tenant_uuid");
}

if (tid) headers["X-Tenant-Id"] = String(tid);

  const r = await fetch(baseUrl + path, { headers });

  // Bootstrap tenant context from response headers (best effort)
  try {
    const tid2 = r.headers.get("x-tenant-id");
    const tschema = r.headers.get("x-tenant-schema");
    if (tid2) localStorage.setItem("tenant_uuid", tid2);
    if (tschema) localStorage.setItem("tenant_schema", tschema);
  } catch (e) {}

  if (r.status === 401) {
    throw new Error("401 Unauthorized (login required)");
  }
  if (r.status === 403) {
    throw new Error("403 Forbidden (tenant context missing or missing role)");
  }
  if (!r.ok) {
    const t = await r.text();
    throw new Error(`${r.status} ${r.statusText}: ${t}`);
  }
  return r.json();
}

  // ---------------------------
  // Views / Routing (hash routes)
  // ---------------------------

  // ---------------------------
  // Aircraft context (URL first, localStorage fallback)
  // ---------------------------
  const LS_AIRCRAFT_KEY = "ui.aircraft_id.last";

  function isUuid(v) {
    return typeof v === "string" && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(v);
  }

  function splitHash() {
    const h = window.location.hash || "";
    const i = h.indexOf("?");
    if (i === -1) return { route: h, query: "" };
    return { route: h.slice(0, i), query: h.slice(i + 1) };
  }

  function getAircraftIdFromUrl() {
    const { query } = splitHash();
    if (!query) return null;
    const q = new URLSearchParams(query);
    const v = q.get("aircraft_id");
    return isUuid(v) ? v : null;
  }

  function setAircraftIdToUrl(aircraftId) {
    const { route, query } = splitHash();
    const q = new URLSearchParams(query || "");
    if (aircraftId) q.set("aircraft_id", aircraftId);
    else q.delete("aircraft_id");
    const next = route + (q.toString() ? "?" + q.toString() : "");
    if ((window.location.hash || "") !== next) window.location.hash = next;
  }

  function getAircraftIdFromStorage() {
    const v = localStorage.getItem(LS_AIRCRAFT_KEY);
    return isUuid(v) ? v : null;
  }

  function saveAircraftIdToStorage(aircraftId) {
    if (isUuid(aircraftId)) localStorage.setItem(LS_AIRCRAFT_KEY, aircraftId);
  }

  function resolveAircraftId() {
    const urlId = getAircraftIdFromUrl();
    if (urlId) return urlId;

    const lsId = getAircraftIdFromStorage();
    if (lsId) {
      const { route, query } = splitHash();
      const q = new URLSearchParams(query || "");
      q.set("aircraft_id", lsId);
      const next = route + "?" + q.toString();
      // promote storage → URL without creating history loop
      window.location.replace(window.location.pathname + window.location.search + next);
      return lsId;
    }
    return null;
  }

  function buildAircraftLabel(a) {
    const reg = (a && a.registration) ? String(a.registration) : "";
    const typ = (a && a.aircraft_type) ? String(a.aircraft_type) : "";
    const bits = [reg, typ].filter(Boolean).join(" • ");
    return bits || ((a && a.id) ? String(a.id) : "(unknown)");
  }

  function renderAircraftSelector(aircraftRows, selectedId) {
    const arr = Array.isArray(aircraftRows) ? aircraftRows : [];
    const opts = arr.map(a => {
      const id = (a && a.id) ? String(a.id) : "";
      if (!isUuid(id)) return "";
      const sel = (id === selectedId) ? " selected" : "";
      return `<option value="${esc(id)}"${sel}>${esc(buildAircraftLabel(a))}</option>`;
    }).filter(Boolean).join("");

    const cur = selectedId
      ? `<div class="muted" style="margin-top:6px;">aircraft_id: <code>${esc(selectedId)}</code></div>`
      : "";

    return `
      <div style="margin: 8px 0 10px 0;">
        <label class="muted" for="aircraft-selector">Aircraft</label><br/>
        <select id="aircraft-selector" style="margin-top:6px; min-width: 360px;">
          <option value="">— wybierz —</option>
          ${opts}
        </select>
        ${cur}
      </div>
    `;
  }

  function bindAircraftSelector() {
    const el = document.getElementById("aircraft-selector");
    if (!el) return;
    el.addEventListener("change", () => {
      const v = el.value;
      if (isUuid(v)) {
        saveAircraftIdToStorage(v);
        setAircraftIdToUrl(v);
      } else {
        localStorage.removeItem(LS_AIRCRAFT_KEY);
        setAircraftIdToUrl(null);
      }
    });
  }

  function renderSelectAircraftEmptyState(modeLabel) {
    return `
      <div class="error-title">Wybierz samolot</div>
      <div class="muted" style="margin-top:6px;">
        Aby wyświetlić <b>${esc(modeLabel)}</b>, wybierz jawnie aircraft_id (dropdown).
      </div>
    `;
  }

  async function loadEventsWithAircraftContext(baseUrl, modeLabel) {
    const ac = await apiFetch(baseUrl, "/v1/aircraft");
    const aircraft = Array.isArray(ac) ? ac : [];

    const selectedId = resolveAircraftId();
    if (!selectedId) {
      // IMPORTANT: no events request
      return { __ui: true, aircraft, selectedId: null, modeLabel, rows: null };
    }

    saveAircraftIdToStorage(selectedId);
    const rows = await apiFetch(baseUrl, `/v1/maintenance-events?aircraft_id=${encodeURIComponent(selectedId)}`);
    return { __ui: true, aircraft, selectedId, modeLabel, rows: Array.isArray(rows) ? rows : [] };
  }

  function renderEventsView(payload) {
    const selector = renderAircraftSelector(payload.aircraft, payload.selectedId);

    if (payload.rows === null) {
      return selector + renderSelectAircraftEmptyState(payload.modeLabel);
    }

    if (!payload.rows.length) {
      return selector + `
        <div class="muted">Brak eventów dla wybranego aircraft</div>
        <div class="muted" style="margin-top:6px;">Zmień samolot z listy powyżej.</div>
      `;
    }

    const table = renderTable(payload.rows, [
      { key: "id", label: "Event ID" },
      { key: "aircraft_id", label: "Aircraft" },
      { key: "event_type", label: "Type" },
      { key: "due_date", label: "Due Date" },
      { key: "status_tech", label: "Status" },
    ]);

    return selector + table;
  }


  const ROUTES = {
    "#/camo/aircraft": {
      title: "CAMO / Aircraft",
      sub: "Lista statków powietrznych (read-only)",
      load: async (baseUrl) => apiFetch(baseUrl, "/v1/aircraft"),
      render: (rows) => renderTable(rows, [
        { key: "registration", label: "Registration" },
        { key: "aircraft_type", label: "Type" },
        { key: "status_tech", label: "Status" },
      ]),
      hint: "GET /v1/aircraft",
    },
    "#/camo/maintenance-events": {
      title: "CAMO / Maintenance Events",
      sub: "Lista zdarzeń obsługowych (read-only)",
      load: async (baseUrl) => loadEventsWithAircraftContext(baseUrl, "Maintenance Events"),
      render: (payload) => renderEventsView(payload),
      hint: "GET /v1/maintenance-events",
    },
    "#/mro/maintenance-events": {
      title: "MRO / Maintenance Events",
      sub: "Lista zdarzeń obsługowych (read-only)",
      load: async (baseUrl) => loadEventsWithAircraftContext(baseUrl, "Maintenance Events"),
      render: (payload) => renderEventsView(payload),
      hint: "GET /v1/maintenance-events",
    },
  };

  function renderTable(rows, columns) {
    const arr = Array.isArray(rows) ? rows : [];
    if (!arr.length) {
      return `<div class="muted">Brak danych (0)</div>`;
    }

    // Build header
    const ths = columns.map(c => `<th>${esc(c.label)}</th>`).join("");
    const trs = arr.map((row) => {
      const tds = columns.map(c => `<td>${esc(((row && row[c.key] != null) ? row[c.key] : ""))}</td>`).join("");
      return `<tr>${tds}</tr>`;
    }).join("");

    return `
      <div class="table-wrap">
        <table>
          <thead><tr>${ths}</tr></thead>
          <tbody>${trs}</tbody>
        </table>
      </div>
    `;
  }

  function setView(routeKey) {
    const route = ROUTES[routeKey] || ROUTES["#/camo/aircraft"];
    viewTitleEl.textContent = route.title;
    viewSubEl.textContent = route.sub;
    contentHintEl.textContent = route.hint;
    return route;
  }
    async function refresh() {
      const baseUrl = normalizeBaseUrl(baseUrlEl.value);

      const apiOk = await pingApi(baseUrl);
      setApiStatus(apiOk, apiOk ? "API: OK" : "API: DOWN");

      const routeKey = window.location.hash || "#/camo/aircraft";
      const route = setView(routeKey);

      contentMetaEl.textContent = "";
      contentBodyEl.innerHTML = "";

      try {
        const started = performance.now();
        const rows = await route.load(baseUrl);
        const ms = Math.round(performance.now() - started);

        // rows meta: support both arrays and UI payload objects
        const rowCount = Array.isArray(rows) ? rows.length : (rows && rows.__ui && Array.isArray(rows.rows) ? rows.rows.length : 0);
        contentMetaEl.textContent = `${rowCount} rows • ${ms} ms`;

        contentBodyEl.innerHTML = route.render(rows);

        // bind dropdown after render (only for UI payload views)
        try { if (rows && rows.__ui) bindAircraftSelector(); } catch {}
      } catch (e) {
        const msg = (e && e.message) ? e.message : String(e);
        contentMetaEl.textContent = "error";
        contentBodyEl.innerHTML = `
          <div class="error-title">Nie udało się pobrać danych z API</div>
          <div class="muted" style="margin-top:6px;">${esc(msg)}</div>
          <div class="muted" style="margin-top:10px;">Sprawdź: login, role, tenant oraz /docs (HTTP 200).</div>
        `;
      }
    }


  function setActiveNav() {
    const h = window.location.hash || "#/camo/aircraft";
    const ids = ["nav-camo-aircraft", "nav-camo-events", "nav-mro-events"];
    ids.forEach((id) => {
      const el = $(id);
      if (!el) return;
      el.classList.toggle("active", el.getAttribute("href") === h);
    });
  }

  function loadSettings() {
    const s = safeJsonParse(localStorage.getItem(LS_KEY) || "{}", {});
    baseUrlEl.value = normalizeBaseUrl(s.baseUrl || DEFAULT_BASE_URL);
  }

  function saveSettings() {
    const baseUrl = normalizeBaseUrl(baseUrlEl.value);
    localStorage.setItem(LS_KEY, JSON.stringify({ baseUrl }));
  }

  // ---------------------------
  // Boot
  // ---------------------------
  async function boot() {
    loadSettings();

    btnSaveEl.addEventListener("click", () => {
      saveSettings();
      window.dispatchEvent(new Event("settings:changed"));
      refresh();
    });

    btnRefreshEl.addEventListener("click", () => refresh());

    btnLoginEl.addEventListener("click", () => login());
    btnLogoutEl.addEventListener("click", () => logout());

    window.addEventListener("hashchange", () => {
      setActiveNav();
      refresh();
    });

    try {
      await handleAuthCallbackIfPresent();
    } catch (e) {
      // show auth error but keep UI running
      setApiStatus(false, "Auth: ERROR");
      contentMetaEl.textContent = "auth error";
      contentBodyEl.innerHTML = `<div class="error-title">Błąd logowania</div><div class="muted" style="margin-top:6px;">${esc(e.message || String(e))}</div>`;
    }

   updateAuthUi();
   window.dispatchEvent(new Event("auth:changed"));
   setActiveNav();
   refresh();
  }

  boot();
})();

// ===========================
// UI #14.2 — Aircraft Context (embedded, because app serves only app.js)
// ===========================
(function () {
  const AUTH_LS_KEY = "aviationcamo_auth_v1";
  const CTX_LS_KEY = "aviationcamo_aircraft_ctx_v1";

  function $(id) { return document.getElementById(id); }

  function safeJsonParse(s, fallback) {
    try { return JSON.parse(s); } catch { return fallback; }
  }

  function decodeJwt(token) {
    if (!token || token.split(".").length < 2) return null;
    try {
      const payload = token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
      const json = decodeURIComponent(atob(payload).split("").map(c => "%" + ("00" + c.charCodeAt(0).toString(16)).slice(-2)).join(""));
      return JSON.parse(json);
    } catch { return null; }
  }


function getBaseUrl() {
    const __baseEl = $("baseUrl");
  const v = ((__baseEl && __baseEl.value) ? __baseEl.value : "").trim();
return (v || "").replace(/\/+$/, "");
}

function getAuth() {
  return safeJsonParse(localStorage.getItem(AUTH_LS_KEY) || "null", null);
}

function getCurrentTenantIdFromToken(auth) {
  const claims =
    ((auth && auth.access_token) ? decodeJwt(auth.access_token) : null) ||
    ((auth && auth.id_token) ? decodeJwt(auth.id_token) : null) ||
    {};
  return (
    claims.tenant_id ||
    claims.tenantId ||
    claims.tenant ||
    claims["x-tenant-id"] ||
    null
  );
}

  function isUnknownOwner(aircraft) {
    const vals = [
      aircraft?.owner_tenant_id,
      aircraft?.owner_tenant_key,
      aircraft?.owner,
      aircraft?.owner_code,
      aircraft?.owner_name,
    ].filter(Boolean).map(String);
    return vals.some(v => v.toUpperCase().includes("UNKNOWN"));
  }

  function computeAccess(aircraft, currentTenantId) {
    const unknownOwner = isUnknownOwner(aircraft);
    const ownerTenantId = ((aircraft && aircraft.owner_tenant_id != null) ? aircraft.owner_tenant_id : ((aircraft && aircraft.ownerTenantId != null) ? aircraft.ownerTenantId : null));
    const isOwner = !!(currentTenantId && ownerTenantId && String(ownerTenantId) === String(currentTenantId) && !unknownOwner);

    const badge = isOwner ? "OWNER" : "MRO";
    const perms = {
      can_edit: isOwner,
      can_create_events: isOwner,
      can_issue_parts: isOwner,
    };

    if (unknownOwner) {
      perms.can_edit = false;
      perms.can_create_events = false;
      perms.can_issue_parts = false;
    }
    return { badge, permissions: perms, unknownOwner, ownerTenantId };
  }

let __aircraftCtxFetchBlockUntil = 0;
let __aircraftCtxLastStatus = 0;

async function apiGetAircraftList(baseUrl, auth) {
  const now = Date.now();
  if (now < __aircraftCtxFetchBlockUntil) {
    throw new Error(`blocked: recent ${__aircraftCtxLastStatus || "401/403"} (cooldown)`);
  }

  const headers = { "Content-Type": "application/json" };
  if (auth?.access_token) headers.Authorization = "Bearer " + auth.access_token;



// --- TENANT CONTEXT (must exist) ---
// Source of truth: localStorage ("tenant_uuid") set by /v1/tenants discovery or response headers.
// MOCK policy: do NOT call /v1/aircraft here; only ensure tenant exists.

let tid = localStorage.getItem("tenant_uuid") || localStorage.getItem("tenant_id");

async function discoverTenantIfMissing(baseUrl, auth) {
  const existing =
    localStorage.getItem("tenant_uuid") ||
    localStorage.getItem("tenant_id");

  if (existing) return String(existing);
  if (!isTokenValid(auth)) return null;

  const r = await fetch(baseUrl + "/v1/tenants", {
    method: "GET",
    headers: { Authorization: "Bearer " + auth.access_token },
  });

  if (!r.ok) return null;

  const arr = await r.json();
  if (!Array.isArray(arr) || arr.length === 0) return null;

  // prefer non-UNK
  const pick =
    arr.find((t) => String((t && t.code) ? t.code : "").toLowerCase() !== "unk") || arr[0];

  const tid2 = ((pick && pick.id)) || ((pick && pick.tenant_id)) || ((pick && pick.uuid));
  const schema = ((pick && pick.schema_name)) || ((pick && pick.schema)) || ((pick && pick.tenant_schema));

  if (tid2) {
    const v = String(tid2);
    localStorage.setItem("tenant_uuid", v);
    localStorage.setItem("tenant_id", v); // friendly
    tid = v;
  }
  if (schema) localStorage.setItem("tenant_schema", String(schema));

  return tid2 ? String(tid2) : null;
}

// Incognito-safe: if missing tenant, do ONE discovery attempt via /v1/tenants
if (!tid) {
  try {
    const auth = loadAuth();
    await discoverTenantIfMissing(baseUrl, auth);
    tid = localStorage.getItem("tenant_uuid") || localStorage.getItem("tenant_id");
  } catch (_) {
    // ignore discovery errors; hard-fail below if still missing
  }
}

if (!tid) {
  __aircraftCtxLastStatus = 403;
  __aircraftCtxFetchBlockUntil = Date.now() + 60000; // 60s hard cooldown
  throw new Error("Tenant context missing (tenant_id/tenant_uuid not set)");
}

// OPTIONAL (safe): if schema exists, pass it too (does not change flow)
const ts = localStorage.getItem("tenant_schema");
if (ts) headers["X-Tenant-Schema"] = String(ts);

// --- AUTH GATE: do not call /v1/aircraft before login ---
const authNow = loadAuth();
if (!isTokenValid(authNow)) {
  __aircraftCtxLastStatus = 401;
  // Important: do NOT throw here; UI should show "login required" state.
  return [];
}

// Ensure Authorization exists (defensive)
headers["Authorization"] = "Bearer " + authNow.access_token;

// Send tenant header (API requires tenant context)
headers["X-Tenant-Id"] = String(tid);

const r = await fetch(baseUrl + "/v1/aircraft", { method: "GET", headers });

if (!r.ok) {
  const t = await r.text();
  __aircraftCtxLastStatus = r.status;

  // If token expired / missing, don't hard-fail as "API error"
  if (r.status === 401) {
    return [];
  }

  // HARD cooldown on 401/403 to prevent request storms (keep your existing logic if you have it)
  if (r.status === 403) {
    __aircraftCtxFetchBlockUntil = Date.now() + 60000; // 60s cooldown
  }

  throw new Error(`${r.status} ${r.statusText}: ${t}`);
}

__aircraftCtxLastStatus = 200;
return r.json();


  function readInitialAircraftId() {
    const u = new URL(window.location.href);
    const fromUrl = u.searchParams.get("aircraft_id");
    if (fromUrl) return fromUrl;

    const ctx = safeJsonParse(localStorage.getItem(CTX_LS_KEY) || "null", null);
    return ((ctx && ctx.aircraft_id)) || null;
  }

  function writeSelectionToUrl(aircraftId) {
    const u = new URL(window.location.href);
    if (aircraftId) u.searchParams.set("aircraft_id", aircraftId);
    else u.searchParams.delete("aircraft_id");
    window.history.replaceState({}, document.title, u.toString());
  }

  function persistCtx(ctx) {
    localStorage.setItem(CTX_LS_KEY, JSON.stringify(ctx));
  }

  function emitChanged(ctx) {
    window.dispatchEvent(new CustomEvent("aircraft:changed", { detail: ctx }));
  }

  function ensureMount() {
    let mount = $("aircraftCtxMount");
    if (!mount) {
      mount = document.createElement("div");
      mount.id = "aircraftCtxMount";

      const baseUrlInput = $("baseUrl");
      if (baseUrlInput && baseUrlInput.parentElement) {
        baseUrlInput.parentElement.insertBefore(mount, baseUrlInput.parentElement.firstChild);
      } else if ($("contentMeta") && $("contentMeta").parentElement) {
        $("contentMeta").parentElement.insertBefore(mount, $("contentMeta").parentElement.firstChild);
      } else if ($("contentBody")) {
        $("contentBody").insertBefore(mount, $("contentBody").firstChild);
      } else {
        document.body.insertBefore(mount, document.body.firstChild);
      }
    }

    mount.innerHTML = `
      <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap; margin-bottom:10px;">
        <label style="min-width:92px;">Aircraft</label>
        <select id="aircraftSelect"
          style="height:34px; padding:0 10px; border-radius:10px; border:1px solid rgba(255,255,255,.12);
                 background: rgba(15,23,48,.65); color:#e8ecff; outline:none; min-width: 280px;">
          <option value="">— Select aircraft —</option>
        </select>
        <span id="aircraftBadge"
          style="font-size:12px; border:1px solid rgba(255,255,255,.12); padding:2px 8px; border-radius:999px;
                 background: rgba(255,255,255,.03); color:#aeb8e6;">
        </span>
        <span id="aircraftPerm"
          style="font-size:12px; color:#aeb8e6;">
        </span>
      </div>
    `;

    return {
      select: $("aircraftSelect"),
      badge: $("aircraftBadge"),
      perm: $("aircraftPerm"),
    };
  }

  function setBadgeAndPerm(ui, access) {
    if (!ui || !ui.badge || !ui.perm) return;
    ui.badge.textContent = (access && access.badge) ? access.badge : "";
    const p = (access && access.permissions) || {};
    ui.perm.textContent = `can_edit=${!!p.can_edit} | can_create_events=${!!p.can_create_events} | can_issue_parts=${!!p.can_issue_parts}`;
  }

  async function initAircraftCtx() {
    const baseUrl = getBaseUrl();
    const auth = getAuth();
    if (!baseUrl || !auth?.access_token) return;

    const ui = ensureMount();
    if (!ui?.select) return;

    let list = [];

    try {
      list = await apiGetAircraftList(baseUrl, auth);
    } catch (e) {
      const msg = (e && (e.message || String(e))) || "error";
      ui.badge.textContent = "AIRCRAFT: ERROR";
      ui.perm.textContent = msg;
      throw new Error(msg);
    }

    const arr = Array.isArray(list) ? list : ((list && (list.items || list.data)) ? (list.items || list.data) : []);
    const currentTenantId = getCurrentTenantIdFromToken(auth);

    // reset options except placeholder
    ui.select.innerHTML = `<option value="">— Select aircraft —</option>`;

    for (const a of arr) {
      const id = String((a && a.id) || "");
      if (!id) continue;

      const reg = (a && a.registration) || a?.reg || a?.tail_number || "";
      const typ = (a && a.aircraft_type) || a?.type || a?.aircraftType || "";

      const opt = document.createElement("option");
      opt.value = id;
      opt.textContent = `${reg || id} ${typ ? "• " + typ : ""}`.trim();
      ui.select.appendChild(opt);
    }

    const initialId = readInitialAircraftId();
    if (initialId) {
      ui.select.value = initialId;
      const aircraft = arr.find(x => String(x?.id) === String(initialId)) || null;
      const access = computeAccess(aircraft, currentTenantId);
      const ctx = { aircraft_id: initialId, aircraft, ...access };
      persistCtx(ctx);
      writeSelectionToUrl(initialId);
      setBadgeAndPerm(ui, access);
      emitChanged(ctx);
    } else {
      ui.select.value = "";
      ui.badge.textContent = "";
      ui.perm.textContent = "";
      persistCtx({ aircraft_id: null });
      writeSelectionToUrl(null);
      emitChanged({ aircraft_id: null });
    }

    ui.select.onchange = () => {
      const id = (ui.select.value || "").trim() || null;
      const aircraft = id ? (arr.find(x => String((x && x.id) ? x.id : "") === String(id)) || null) : null;
      const access = computeAccess(aircraft, currentTenantId);
      const ctx = { aircraft_id: id, aircraft, ...access };
      persistCtx(ctx);
      writeSelectionToUrl(id);
      setBadgeAndPerm(ui, access);
      emitChanged(ctx);
    };
  }

let __aircraftCtxInitInFlight = false;
let __aircraftCtxInitOk = false;
let __aircraftCtxInitTimer = null;
let __aircraftCtxDisabledUntil = 0;
let __aircraftCtxTimer = null;
let __aircraftCtxLastRunAt = 0;

function scheduleAircraftCtxInit(retries = 6, delayMs = 0) {
  // coalesce calls (no storm)
  if (__aircraftCtxInitTimer) return;

  // hard disable window (e.g. after 401/403/tenant missing)
  const now = Date.now();
  if (__aircraftCtxDisabledUntil && now < __aircraftCtxDisabledUntil) return;

  // already OK -> nothing to do
  if (__aircraftCtxInitOk) return;

  const d = Math.max(0, Number(delayMs) || 0);
  __aircraftCtxInitTimer = setTimeout(() => {
    __aircraftCtxInitTimer = null;
    runAircraftCtxInit(retries).catch(() => {});
  }, d);
}

async function runAircraftCtxInit(retries = 6) {
  // prevent parallel init storms
  if (__aircraftCtxInitInFlight) return;
  __aircraftCtxInitInFlight = true;

  try {
    const ui = ensureMount();

    // if not logged in -> do not fetch
    const auth = loadAuth();
    if (!isTokenValid(auth)) {
      ui.badge.textContent = "AIRCRAFT: LOGIN";
      ui.perm.textContent = "login required";
      __aircraftCtxInitOk = false;
      return;
    }

    // tenant is required by backend
    const tenantUuid = localStorage.getItem("tenant_uuid");
    if (!tenantUuid) {
      ui.badge.textContent = "AIRCRAFT: TENANT";
      ui.perm.textContent = "tenant_uuid missing";
      // hard stop until auth/settings change (no retries)
      __aircraftCtxDisabledUntil = Date.now() + 60000;
      __aircraftCtxInitOk = false;
      return;
    }

    const baseUrl = getBaseUrl();
    let list = [];
    try {
      list = await apiGetAircraftList(baseUrl, auth);
    } catch (e) {
      const msg = (e && (e.message || String(e))) || "error";
      ui.badge.textContent = "AIRCRAFT: ERROR";
      ui.perm.textContent = msg;

      // HARD STOP on auth/tenant errors (no retry storm)
      if (/\b(401|403)\b|unauthorized|forbidden|tenant context missing|tenant_uuid missing|blocked:/i.test(msg)) {
        __aircraftCtxDisabledUntil = Date.now() + 60000; // 60s cooldown
        return;
      }

      // soft retry (network / transient)
      if (retries > 0) {
        __aircraftCtxNextDelayMs = Math.min(__aircraftCtxNextDelayMs * 2, 8000);
        scheduleAircraftCtxInit(retries - 1, __aircraftCtxNextDelayMs);
      }
      return;
    }

    const arr = Array.isArray(list) ? list : ((list && (list.items || list.data)) ? (list.items || list.data) : []);
    fillSelect(ui, arr);

    // mark OK only if we have at least one real option (placeholder + 1)
    if (ui.select && ui.select.options && ui.select.options.length > 1) {
      __aircraftCtxInitOk = true;
      __aircraftCtxNextDelayMs = 400;
      __aircraftCtxDisabledUntil = 0;
    } else {
      __aircraftCtxInitOk = false;
    }
  } finally {
    __aircraftCtxInitInFlight = false;
  }
}

// Boot hooks (single scheduler, debounced)
const kick = () => scheduleAircraftCtxInit(10, 0);

if (document.readyState === "complete" || document.readyState === "interactive") {
  setTimeout(kick, 0);
} else {
  window.addEventListener("DOMContentLoaded", kick, { once: true });
  window.addEventListener("load", kick, { once: true });
}

// On settings/auth change: reset disabled flag and re-init once (debounced)
window.addEventListener("settings:changed", () => {
  __aircraftCtxInitOk = false;
  __aircraftCtxNextDelayMs = 400;
  __aircraftCtxDisabledUntil = 0;
  if (__aircraftCtxInitTimer) { clearTimeout(__aircraftCtxInitTimer); __aircraftCtxInitTimer = null; }
  scheduleAircraftCtxInit(6, 100);
});

window.addEventListener("auth:changed", () => {
  __aircraftCtxInitOk = false;
  __aircraftCtxNextDelayMs = 400;
  __aircraftCtxDisabledUntil = 0;
  if (__aircraftCtxInitTimer) { clearTimeout(__aircraftCtxInitTimer); __aircraftCtxInitTimer = null; }
  scheduleAircraftCtxInit(6, 100);
});
}
})();
