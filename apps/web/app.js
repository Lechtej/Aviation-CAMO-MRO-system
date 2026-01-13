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

(function () {
  const $ = (id) => document.getElementById(id);

  const baseUrlEl = $("baseUrl");
  const kcBaseUrlEl = $("kcBaseUrl");
  const kcRealmEl = $("kcRealm");
  const kcClientIdEl = $("kcClientId");
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

  const DEFAULT_BASE_URL = (location.origin || "http://localhost:3000").replace(":3000", ":8000");
  const LS_KEY = "aviationcamo_ui_v1";
  const LS_AUTH_KEY = "aviationcamo_auth_v1";

// Keycloak (defaults; can be overridden via UI settings stored in localStorage)
// Production: auth is served from https://auth.forgemotionsystems.com (SPA runs on https://app.forgemotionsystems.com)
const KC = {
  baseUrl: (location.hostname === "app.forgemotionsystems.com")
    ? "https://auth.forgemotionsystems.com"
    : (location.origin || "http://localhost:3000").replace(":3000", ":8080"),
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
    return String(s ?? "").replace(/[&<>"']/g, (c) => ({
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
    const claims = decodeJwt(auth?.access_token) || decodeJwt(auth?.id_token) || {};
    const ra = claims?.realm_access || {};
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
    const user = claims?.preferred_username || claims?.name || "user";
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
      scope: "openid profile email",
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
// Auth lifecycle (UI-side) — KROK 2
// ---------------------------
const AUTH_EXPIRED_CODE = "AUTH_EXPIRED";

function authExpiredError(message) {
  const e = new Error(message || "Session expired. Please login again.");
  e.code = AUTH_EXPIRED_CODE;
  return e;
}

function isProtectedPath(path) {
  // Current UI routes are all protected (API v1). Keep it explicit to avoid blocking /openapi.json ping.
  return String(path || "").startsWith("/v1/");
}

function ensureValidAuthFor(path) {
  if (!isProtectedPath(path)) return loadAuth();
  const auth = loadAuth();
  if (!isTokenValid(auth)) {
    // Deterministic: no API calls without a valid token
    clearAuth();
    updateAuthUi();
    throw authExpiredError("Session expired. Please login again.");
  }
  return auth;
}

function renderSessionExpired() {
  contentMetaEl.textContent = "auth required";
  contentBodyEl.innerHTML = `
    <div class="error-title">Session expired</div>
    <div class="muted" style="margin-top:6px;">
      Twoja sesja wygasła lub nie jesteś zalogowany. Kliknij <b>Login</b>, aby ponownie przejść przez Keycloak (PKCE).
    </div>
    <div style="margin-top:12px;">
      <button id="btnReLogin" class="btn primary">Login</button>
    </div>
  `;
  const b = document.getElementById("btnReLogin");
  if (b) b.addEventListener("click", () => login());
}

  // ---------------------------
  // API calls
  // ---------------------------
  async function pingApi(baseUrl) {
    try {
      const r = await fetch(baseUrl + "/openapi.json", { method: "GET" });
      if (r.ok) return true;
      return false;
    } catch {
      return false;
    }
  }

  
async function apiRequest(baseUrl, path, opts) {
  const headers = { "Content-Type": "application/json" };

  // Preflight token lifecycle (KROK 2): block protected calls if token is missing/expired
  const auth = ensureValidAuthFor(path);
  if (auth && isTokenValid(auth)) headers["Authorization"] = "Bearer " + auth.access_token;

  const r = await fetch(baseUrl + path, {
    method: (opts?.method || "GET"),
    headers,
    body: opts?.body ? JSON.stringify(opts.body) : undefined,
  });

  if (r.status === 401) {
    // Global 401 handler: clear auth and force controlled re-login UX (no loops, no silent retry)
    clearAuth();
    updateAuthUi();
    throw authExpiredError("401 Unauthorized (session expired)");
  }
  if (r.status === 403) {
    throw new Error("403 Forbidden");
  }
  if (!r.ok) {
    const t = await r.text();
    throw new Error(`${r.status} ${r.statusText}: ${t}`);
  }
  if (r.status === 204) return null;
  const ct = (r.headers.get("content-type") || "").toLowerCase();
  if (ct.includes("application/json")) return r.json();
  return r.text();
}

async function apiFetch(baseUrl, path) {
  return apiRequest(baseUrl, path, { method: "GET" });
}


  function renderEventsTable(rows, mode) {
    const arr = Array.isArray(rows) ? rows : [];
    if (!arr.length) return `<div class="muted">Brak danych (0)</div>`;

    const ths = [
      "Event ID", "Aircraft", "Type", "Status", "Updated", (mode === "mro" ? "Actions" : "")
    ].map(x => x ? `<th>${esc(x)}</th>` : "").join("");

    const trs = arr.map((r) => {
      const updated = r.updated_at ? String(r.updated_at) : "";
      const actions = (mode !== "mro") ? "" : `
        <div class="row-actions">
          <textarea class="notes" data-eid="${esc(r.id)}" placeholder="mro_notes (optional)">${esc(r.mro_notes || "")}</textarea>
          <div class="btns">
            <button class="btn" data-act="in_progress" data-eid="${esc(r.id)}" ${r.status !== "OPEN" ? "disabled" : ""}>IN_PROGRESS</button>
            <button class="btn" data-act="done" data-eid="${esc(r.id)}" ${r.status !== "IN_PROGRESS" ? "disabled" : ""}>DONE</button>
          </div>
        </div>
      `;
      return `
        <tr>
          <td>${esc(r.id)}</td>
          <td>${esc(r.aircraft_id)}</td>
          <td>${esc(r.event_type || "")}</td>
          <td><b>${esc(r.status || "")}</b></td>
          <td class="muted">${esc(updated)}</td>
          ${mode === "mro" ? `<td>${actions}</td>` : ""}
        </tr>
      `;
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

  function bindCamoCreate(baseUrl) {
    const btn = document.getElementById("btnCreateEvent");
    if (!btn) return;
    btn.addEventListener("click", async () => {
      const aircraftId = (document.getElementById("camoAircraftId")?.value || "").trim();
      const eventType = (document.getElementById("camoEventType")?.value || "").trim();
      const desc = (document.getElementById("camoDesc")?.value || "").trim();
      const msg = document.getElementById("camoCreateMsg");
      if (msg) msg.textContent = "";
      try {
        if (!aircraftId || !eventType) throw new Error("Aircraft ID and Event type are required");
        const r = await apiRequest(baseUrl, "/v1/maintenance-events", {
          method: "POST",
          body: { aircraft_id: aircraftId, event_type: eventType, description: desc || null },
        });
        if (msg) msg.textContent = `OK: created ${r.id}`;
        refresh();
      } catch (e) {
      if (e && e.code === AUTH_EXPIRED_CODE) {
        renderSessionExpired();
        return;
      }

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

  // Keycloak settings (optional overrides)
  const kcBase = String(s.kcBaseUrl || KC.baseUrl || "").trim();
  const kcRealm = String(s.kcRealm || KC.realm || "").trim();
  const kcClient = String(s.kcClientId || KC.clientId || "").trim();

  if (kcBaseUrlEl) kcBaseUrlEl.value = kcBase;
  if (kcRealmEl) kcRealmEl.value = kcRealm;
  if (kcClientIdEl) kcClientIdEl.value = kcClient;

  // Apply overrides to runtime config
  if (kcBase) KC.baseUrl = kcBase.replace(/\/+$/, "");
  if (kcRealm) KC.realm = kcRealm;
  if (kcClient) KC.clientId = kcClient;
}

function saveSettings() {
  const baseUrl = normalizeBaseUrl(baseUrlEl.value);

  const kcBaseUrl = (kcBaseUrlEl?.value || KC.baseUrl || "").trim().replace(/\/+$/, "");
  const kcRealm = (kcRealmEl?.value || KC.realm || "").trim();
  const kcClientId = (kcClientIdEl?.value || KC.clientId || "").trim();

  localStorage.setItem(LS_KEY, JSON.stringify({ baseUrl, kcBaseUrl, kcRealm, kcClientId }));
}

  // ---------------------------
  // Boot
  // ---------------------------
  async function boot() {
    loadSettings();

    btnSaveEl.addEventListener("click", () => {
      saveSettings();
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
    setActiveNav();
    refresh();
  }

  boot();
})();