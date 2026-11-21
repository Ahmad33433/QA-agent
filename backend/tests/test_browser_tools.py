"""Runs the real Playwright tools against a tiny local page (no LLM, no internet).

Skipped when Chromium is not installed: run `uv run playwright install chromium`.
"""
import functools
import http.server
import threading

import pytest

import config
import tools
from browser_manager import browser

PAGE = """<!doctype html><title>Demo</title>
<input id="name" aria-label="Name">
<button id="go" onclick="document.getElementById('out').textContent='Hello ' + document.getElementById('name').value">Greet</button>
<p id="out"></p>
<a href="/second.html">Next page</a>
"""


@pytest.fixture
def site(tmp_path):
    (tmp_path / "index.html").write_text(PAGE)
    (tmp_path / "second.html").write_text("<title>Two</title>second")
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(tmp_path))
    handler.log_message = lambda *a, **k: None
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()


async def test_agent_tools_drive_a_real_page(site, tmp_path, monkeypatch):
    monkeypatch.setattr(config, "HEADLESS", True)
    monkeypatch.setattr(config, "SCREENSHOTS_DIR", tmp_path / "shots")
    try:
        await browser.init_browser()
    except Exception as exc:
        pytest.skip(f"Chromium not available: {exc}")
    try:
        tools.set_original_url(site)
        await tools.navigate_to.ainvoke({"url": site})

        elements = await tools.analyze_page.ainvoke({})
        assert "#go" in elements and "#name" in elements and "/second.html" in elements

        await tools.type_text.ainvoke({"selector": "#name", "text": "Ahmad"})
        await tools.perform_click.ainvoke({"selector": "#go"})
        page = await browser.init_browser()
        assert await page.inner_text("#out") == "Hello Ahmad"

        assert "Failed" in await tools.perform_click.ainvoke({"selector": "#missing"})

        await tools.smart_click.ainvoke({"text": "Next page"})
        await page.wait_for_url("**/second.html")
        assert "second.html" in await tools.get_url.ainvoke({})
        await tools.navigate_to_original.ainvoke({})
        assert (await tools.get_url.ainvoke({})).rstrip("/").endswith(site.split("//")[1])

        assert '"nodes"' in await tools.get_accessibility_tree.ainvoke({})
        await tools.capture_screen.ainvoke({"filename": "shot.png"})
        assert (tmp_path / "shots" / "shot.png").stat().st_size > 0
    finally:
        await browser.close()
