"""MCP server that exposes the QA tools over stdio.

The FastAPI backend starts it for each run and the agent calls the tools through it. Because it
is a normal MCP server, any MCP client can use the same tools too, for example Claude Desktop or
Cursor (see the README).

Run by hand:  uv run python mcp_server.py
Never print to stdout here: stdout carries the MCP protocol.
"""
from contextlib import asynccontextmanager

from mcp.server.fastmcp import FastMCP

import config
import tools
from browser_manager import browser


@asynccontextmanager
async def lifespan(_server: FastMCP):
    config.ensure_dirs()
    try:
        yield
    finally:
        await browser.close()


mcp = FastMCP("qa-agent-tools", lifespan=lifespan)
for tool_fn in tools.ALL_TOOLS:
    mcp.tool()(tool_fn)

if __name__ == "__main__":
    mcp.run()
