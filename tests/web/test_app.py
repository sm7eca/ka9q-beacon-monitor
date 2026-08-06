import json
import re

import pytest
from fastapi.testclient import TestClient

from ka9q_beacon_monitor.web import WebUiConfig, create_web_app


def test_index_contains_accessible_dashboard_and_config() -> None:
    client = TestClient(create_web_app(WebUiConfig(api_base_url="/api", refresh_seconds=30)))
    response = client.get("/")
    assert response.status_code == 200
    assert 'id="beacons"' in response.text
    assert 'aria-live="polite"' in response.text
    match = re.search(r'<script id="web-ui-config" type="application/json">(.*?)</script>', response.text)
    assert match is not None
    assert json.loads(match.group(1)) == {"apiBaseUrl": "/api", "refreshSeconds": 30}
    assert response.headers["cache-control"] == "no-store"


def test_title_is_html_escaped() -> None:
    client = TestClient(create_web_app(WebUiConfig(title="<Beacon & Monitor>")))
    response = client.get("/")
    assert "&lt;Beacon &amp; Monitor&gt;" in response.text
    assert "<Beacon & Monitor>" not in response.text


def test_assets_are_served_with_expected_types() -> None:
    client = TestClient(create_web_app())
    css = client.get("/assets/styles.css")
    js = client.get("/assets/app.js")
    assert css.status_code == 200 and css.headers["content-type"].startswith("text/css")
    assert js.status_code == 200 and js.headers["content-type"].startswith("application/javascript")
    assert "textContent" in js.text
    assert "innerHTML" not in js.text


def test_health_is_read_only_and_available() -> None:
    client = TestClient(create_web_app())
    assert client.get("/health").json() == {"status": "ok"}
    assert client.post("/").status_code == 405


def test_config_normalizes_api_base_url() -> None:
    config = WebUiConfig(api_base_url="https://example.test/api/")
    assert config.api_base_url == "https://example.test/api"


@pytest.mark.parametrize("seconds", [0, 4, 3601])
def test_refresh_interval_is_bounded(seconds: int) -> None:
    with pytest.raises(ValueError):
        WebUiConfig(refresh_seconds=seconds)


def test_empty_title_is_rejected() -> None:
    with pytest.raises(ValueError):
        WebUiConfig(title="   ")


def test_embedded_config_json_blocks_script_tag_breakout() -> None:
    attack = "</script><script>alert(1)</script>"
    client = TestClient(create_web_app(WebUiConfig(api_base_url=attack)))
    response = client.get("/")
    assert response.status_code == 200
    assert attack not in response.text
    assert "\\u003c/script>\\u003cscript>alert(1)\\u003c/script>" in response.text
    match = re.search(r'<script id="web-ui-config" type="application/json">(.*?)</script>', response.text)
    assert match is not None
    assert json.loads(match.group(1))["apiBaseUrl"] == attack
