import asyncio
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

import config
import prompts
import tools
from browser_manager import browser, status_store
from schemas import RunRequest

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

BASE_TOOLS = [
    tools.navigate_to, tools.navigate_to_original, tools.get_url,
    tools.perform_click, tools.smart_click, tools.type_text, tools.press_key,
    tools.analyze_page, tools.get_accessibility_tree,
    tools.capture_screen, tools.capture_and_analyze_screen,
    tools.write_bug_report, tools.update_status,
]
SCRIPT_TOOLS = BASE_TOOLS + [tools.write_ui_script, tools.run_ui_test]
PERF_TOOLS = BASE_TOOLS + [tools.write_locust_script, tools.run_locust_test]

# One shared browser and one status store, so only one run at a time.
run_lock = asyncio.Lock()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    config.ensure_dirs()
    yield
    await browser.close()


app = FastAPI(title="QA Agent", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


def build_run(req: RunRequest) -> tuple[str, list, str]:
    """Pick the system prompt, tool set and opening user message for a request."""
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


async def run_agent(system_prompt: str, agent_tools: list, user_message: str) -> str:
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
        tools.set_original_url(req.url)
        system_prompt, agent_tools, user_message = build_run(req)
        status_store.update(status="running", step="started", message="")
        try:
            report = await run_agent(system_prompt, agent_tools, user_message)
        except Exception as exc:
            status_store.update(status="error", step="failed", message=str(exc)[:200])
            raise HTTPException(status_code=500, detail=f"Agent run failed: {exc}") from exc
        status_store.update(status="idle", step="finished", message="")
    return {"status": "Test Completed", "url": req.url, "report": report}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host=config.HOST, port=config.PORT, reload=False)
