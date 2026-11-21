import asyncio
import os
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools
from langchain_openai import ChatOpenAI

import config
import prompts
from browser_manager import status_store
from schemas import RunRequest

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# Names of the MCP tools (see tools.py / mcp_server.py) each kind of run may use.
BASE_TOOLS = [
    "navigate_to", "navigate_to_original", "get_url",
    "perform_click", "smart_click", "type_text", "press_key",
    "analyze_page", "get_accessibility_tree",
    "capture_screen", "capture_and_analyze_screen", "write_bug_report",
]
SCRIPT_TOOLS = BASE_TOOLS + ["write_ui_script", "run_ui_test"]
PERF_TOOLS = BASE_TOOLS + ["write_locust_script", "run_locust_test"]

MCP_SERVER = {
    "qa": {
        "transport": "stdio",
        "command": sys.executable,
        "args": [str(config.BASE_DIR / "mcp_server.py")],
        # Pass the whole environment: the server needs OPENAI_API_KEY and the QA_* settings.
        "env": dict(os.environ),
    }
}


@tool
async def update_status(step: str, message: str = "") -> str:
    """Update the current QA testing status shown in the Chrome extension."""
    status_store.update(status="running", step=step, message=message)
    return f"Status updated to: {step}"


# One MCP server (and browser) per run and one status store, so only one run at a time.
run_lock = asyncio.Lock()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    config.ensure_dirs()
    yield


app = FastAPI(title="QA Agent", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


def build_run(req: RunRequest) -> tuple[str, list[str], str]:
    """Pick the system prompt, MCP tool names and opening user message for a request."""
    if req.category == "performance_test":
        params = req.performance_params
        prompt = prompts.performance_prompt(
            req.url, req.mode, params.users or 10, params.duration or "30s"
        )
        return prompt, PERF_TOOLS, "Start the performance test."
    if req.mode == "scenario_test":
        return prompts.scenario_prompt(req.url), BASE_TOOLS, req.scenario_text
    if req.mode == "manual_test":
        return prompts.full_audit_prompt(req.url), BASE_TOOLS, "Start the audit."
    return prompts.script_prompt(req.url), SCRIPT_TOOLS, "Write and run the UI test script."


async def run_agent(req: RunRequest, system_prompt: str, tool_names: list[str], user_message: str) -> str:
    """Start the MCP tool server for this run, give the agent its tools, and return its report."""
    client = MultiServerMCPClient(MCP_SERVER)
    # One session for the whole run, so the browser state survives between tool calls.
    async with client.session("qa") as session:
        await session.call_tool("set_original_url", {"url": req.url})
        mcp_tools = await load_mcp_tools(session)
        by_name = {t.name: t for t in mcp_tools}
        missing = [name for name in tool_names if name not in by_name]
        if missing:
            raise RuntimeError(f"MCP server is missing tools: {missing}")
        agent_tools = [by_name[name] for name in tool_names] + [update_status]
        agent = create_agent(ChatOpenAI(model=config.AGENT_MODEL), agent_tools)
        result = await agent.ainvoke(
            {"messages": [SystemMessage(content=system_prompt), HumanMessage(content=user_message)]}
        )
    return result["messages"][-1].content


@app.get("/status")
async def get_status():
    return status_store


@app.post("/server")
async def run_automation_test(req: RunRequest):
    if run_lock.locked():
        raise HTTPException(status_code=409, detail="A test is already running")
    async with run_lock:
        system_prompt, tool_names, user_message = build_run(req)
        status_store.update(status="running", step="started", message="")
        try:
            report = await run_agent(req, system_prompt, tool_names, user_message)
        except Exception as exc:
            status_store.update(status="error", step="failed", message=str(exc)[:200])
            raise HTTPException(status_code=500, detail=f"Agent run failed: {exc}") from exc
        status_store.update(status="idle", step="finished", message="")
    return {"status": "Test Completed", "url": req.url, "report": report}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host=config.HOST, port=config.PORT, reload=False)
