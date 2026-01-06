// Minimal UI helper for AviationCAMO-MRO
// - Lets you ping the API
// - Send arbitrary requests with optional Bearer token

(function () {
  const $ = (id) => document.getElementById(id);

  const baseUrlEl = $("baseUrl");
  const pathEl = $("path");
  const methodEl = $("method");
  const tokenEl = $("token");
  const bodyEl = $("body");
  const btnSendEl = $("btnSend");
  const outEl = $("out");

  function normalizeBaseUrl(u) {
    return (u || "").trim().replace(/\/+$/, "");
  }

  function joinUrl(base, path) {
    const b = normalizeBaseUrl(base);
    const p = (path || "").trim();
    if (!p) return b;
    if (p.startsWith("http://") || p.startsWith("https://")) return p;
    return b + (p.startsWith("/") ? "" : "/") + p;
  }

  function setOut(text) {
    outEl.textContent = text;
  }

  function prettyJsonMaybe(text) {
    try {
      return JSON.stringify(JSON.parse(text), null, 2);
    } catch {
      return text;
    }
  }

  async function send() {
    const url = joinUrl(baseUrlEl.value, pathEl.value);
    const method = (methodEl.value || "GET").toUpperCase();
    const token = (tokenEl.value || "").trim();
    const rawBody = (bodyEl.value || "").trim();

    const headers = {
      Accept: "application/json",
    };
    if (token) headers.Authorization = `Bearer ${token}`;

    const opts = { method, headers };
    if (!["GET", "HEAD"].includes(method) && rawBody) {
      headers["Content-Type"] = "application/json";
      opts.body = rawBody;
    }

    setOut(`→ ${method} ${url}\n\n(sending...)`);

    try {
      const res = await fetch(url, opts);
      const ct = res.headers.get("content-type") || "";
      const text = await res.text();
      const isJson = ct.includes("application/json");
      const payload = isJson ? prettyJsonMaybe(text) : text;

      setOut(
        [
          `← HTTP ${res.status} ${res.statusText}`,
          `Content-Type: ${ct || "(none)"}`,
          `URL: ${url}`,
          "",
          payload || "(empty body)",
        ].join("\n")
      );
    } catch (e) {
      setOut(`✖ Request failed\n\n${String(e)}`);
    }
  }

  btnSendEl.addEventListener("click", (ev) => {
    ev.preventDefault();
    send();
  });

  // Small convenience: Ctrl+Enter sends
  document.addEventListener("keydown", (ev) => {
    if (ev.ctrlKey && ev.key === "Enter") {
      ev.preventDefault();
      send();
    }
  });
})();
