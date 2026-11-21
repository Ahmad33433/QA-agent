"""Starts the real MCP server as a subprocess and talks to it like the agent does."""
import os
import sys

import pytest
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools

import config
import tools
from test_browser_tools import PAGE, site  # noqa: F401  (site is a fixture)


def server_config(tmp_path):
    env = dict(os.environ, QA_HEADLESS="true", QA_ARTIFACTS_DIR=str(tmp_path / "artifacts"))
    return {"qa": {
        "transport": "stdio",
        "command": sys.executable,
        "args": [str(config.BASE_DIR / "mcp_server.py")],
        "env": env,
    }}


async def test_server_publishes_every_tool(tmp_path):
    client = MultiServerMCPClient(server_config(tmp_path))
    async with client.session("qa") as session:
        names = {t.name for t in await load_mcp_tools(session)}
    assert names == {fn.__name__ for fn in tools.ALL_TOOLS}
    assert len(names) == 17


async def test_agent_style_session_keeps_browser_state(site, tmp_path):  # noqa: F811
    client = MultiServerMCPClient(server_config(tmp_path))
    async with client.session("qa") as session:
        by_name = {t.name: t for t in await load_mcp_tools(session)}
        await session.call_tool("set_original_url", {"url": site})
        await by_name["navigate_to"].ainvoke({"url": site})
        try:
            elements = await by_name["analyze_page"].ainvoke({})
        except Exception as exc:
            pytest.skip(f"Chromium not available: {exc}")
        assert "#go" in str(elements)

        # State from earlier calls (current page, typed text) must still be there.
        await by_name["type_text"].ainvoke({"selector": "#name", "text": "MCP"})
        await by_name["perform_click"].ainvoke({"selector": "#go"})
        await by_name["smart_click"].ainvoke({"text": "Next page"})
        url = await by_name["get_url"].ainvoke({})
        assert "second.html" in str(url)
        back = await by_name["navigate_to_original"].ainvoke({})
        assert "we reach this url" in str(back)

        await by_name["write_bug_report"].ainvoke({"report": "found via MCP"})
    assert "found via MCP" in (tmp_path / "artifacts" / "bug_report.txt").read_text()
