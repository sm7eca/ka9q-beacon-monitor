from __future__ import annotations

import json
from dataclasses import dataclass

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, Response


@dataclass(frozen=True, slots=True)
class WebUiConfig:
    api_base_url: str = ""
    refresh_seconds: int = 30
    title: str = "KA9Q Beacon Monitor"

    def __post_init__(self) -> None:
        if not self.title.strip():
            raise ValueError("title must not be empty")
        if self.refresh_seconds < 5 or self.refresh_seconds > 3600:
            raise ValueError("refresh_seconds must be between 5 and 3600")
        if self.api_base_url.endswith("/") and self.api_base_url != "/":
            object.__setattr__(self, "api_base_url", self.api_base_url.rstrip("/"))


def _html(config: WebUiConfig) -> str:
    title = config.title.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    ui_config = json.dumps({"apiBaseUrl": config.api_base_url, "refreshSeconds": config.refresh_seconds}).replace("<", "\\u003c")
    return f"""<!doctype html>
<html lang=\"sv\">
<head>
  <meta charset=\"utf-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
  <title>{title}</title>
  <link rel=\"stylesheet\" href=\"/assets/styles.css\">
</head>
<body>
  <header><h1>{title}</h1><p id=\"last-updated\">Väntar på data…</p></header>
  <main>
    <section aria-labelledby=\"overview-heading\">
      <h2 id=\"overview-heading\">Fyröversikt</h2>
      <div id=\"error\" role=\"alert\" hidden></div>
      <div id=\"beacons\" class=\"grid\" aria-live=\"polite\"></div>
    </section>
  </main>
  <noscript>JavaScript krävs för att visa aktuell hörbarhet.</noscript>
  <script id=\"web-ui-config\" type=\"application/json\">{ui_config}</script>
  <script src=\"/assets/app.js\" defer></script>
</body>
</html>"""


_STYLES = """
:root { font-family: system-ui, sans-serif; color-scheme: light dark; }
body { margin: 0; background: Canvas; color: CanvasText; }
header, main { max-width: 1100px; margin: auto; padding: 1rem; }
header { display: flex; justify-content: space-between; gap: 1rem; align-items: baseline; }
.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 1rem; }
.card { border: 1px solid color-mix(in srgb, CanvasText 25%, transparent); border-radius: .75rem; padding: 1rem; }
.state { font-weight: 700; }
.meta { opacity: .75; font-size: .9rem; }
#error { border: 1px solid currentColor; padding: .75rem; margin-bottom: 1rem; }
""".strip()


_SCRIPT = r"""
(() => {
  'use strict';
  const config = JSON.parse(document.getElementById('web-ui-config').textContent);
  const base = config.apiBaseUrl || '';
  const container = document.getElementById('beacons');
  const errorBox = document.getElementById('error');
  const updated = document.getElementById('last-updated');
  const text = (value) => value == null ? '—' : String(value);

  async function fetchJson(path) {
    const response = await fetch(base + path, { headers: { Accept: 'application/json' } });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  }

  function card(beacon, summary) {
    const article = document.createElement('article');
    article.className = 'card';
    const title = document.createElement('h3');
    title.textContent = beacon.callsign || beacon.beacon_id;
    const state = document.createElement('p');
    state.className = 'state';
    state.textContent = summary ? text(summary.final_state) : 'no_data';
    const snr = document.createElement('p');
    snr.textContent = `Median SNR: ${summary && summary.median_effective_snr_db != null ? summary.median_effective_snr_db + ' dB' : '—'}`;
    const meta = document.createElement('p');
    meta.className = 'meta';
    meta.textContent = `${text(beacon.frequency_hz)} Hz · ${text(beacon.description)}`;
    article.append(title, state, snr, meta);
    return article;
  }

  async function refresh() {
    try {
      const beacons = await fetchJson('/beacons');
      const summaries = await Promise.all(beacons.map(async beacon => {
        const page = await fetchJson(`/beacons/${encodeURIComponent(beacon.beacon_id)}/summaries?limit=1`);
        return [beacon.beacon_id, page.items[0] || null];
      }));
      const byId = new Map(summaries);
      container.replaceChildren(...beacons.map(beacon => card(beacon, byId.get(beacon.beacon_id))));
      errorBox.hidden = true;
      updated.textContent = `Uppdaterad ${new Date().toLocaleString('sv-SE')}`;
    } catch (error) {
      errorBox.textContent = `Kunde inte hämta data: ${error.message}`;
      errorBox.hidden = false;
    }
  }

  refresh();
  window.setInterval(refresh, config.refreshSeconds * 1000);
})();
""".strip()


def create_web_app(config: WebUiConfig | None = None) -> FastAPI:
    """Create a read-only web UI that consumes the approved REST API."""
    active = config or WebUiConfig()
    app = FastAPI(title=f"{active.title} Web UI", version="1.0.0", docs_url=None, redoc_url=None)

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    def index() -> HTMLResponse:
        return HTMLResponse(_html(active), headers={"Cache-Control": "no-store"})

    @app.get("/assets/styles.css", include_in_schema=False)
    def styles() -> Response:
        return Response(_STYLES, media_type="text/css", headers={"Cache-Control": "public, max-age=3600"})

    @app.get("/assets/app.js", include_in_schema=False)
    def script() -> Response:
        return Response(_SCRIPT, media_type="application/javascript", headers={"Cache-Control": "public, max-age=3600"})

    @app.get("/health", include_in_schema=False)
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app
