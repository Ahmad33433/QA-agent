import asyncio

import pytest
from fastapi.testclient import TestClient

import main

BODY = {"url": "https://example.com", "category": "ui_test", "mode": "manual_test"}


@pytest.fixture
def client(monkeypatch):
    async def fake_agent(system_prompt, agent_tools, user_message):
        return "fake report"

    monkeypatch.setattr(main, "run_agent", fake_agent)
    return TestClient(main.app)


def test_status_starts_idle(client):
    assert client.get("/status").json()["status"] in ("idle", "running", "error")


def test_run_returns_report(client):
    res = client.post("/server", json=BODY)
    assert res.status_code == 200
    assert res.json()["report"] == "fake report"


def test_invalid_request_is_rejected(client):
    assert client.post("/server", json={**BODY, "url": "ftp://x"}).status_code == 422
    assert client.post("/server", json={**BODY, "mode": "load_test"}).status_code == 422


def test_scenario_text_is_passed_to_agent(monkeypatch):
    seen = {}

    async def fake_agent(system_prompt, agent_tools, user_message):
        seen["message"] = user_message
        return "ok"

    monkeypatch.setattr(main, "run_agent", fake_agent)
    body = {**BODY, "mode": "scenario_test", "scenario_text": "log in with a wrong password"}
    assert TestClient(main.app).post("/server", json=body).status_code == 200
    assert seen["message"] == "log in with a wrong password"


def test_script_mode_gets_script_tools():
    from schemas import RunRequest

    _, tool_list, _ = main.build_run(
        RunRequest(url="https://example.com", category="ui_test", mode="scripted_test")
    )
    names = {t.name for t in tool_list}
    assert {"write_ui_script", "run_ui_test"} <= names


def test_second_run_while_busy_gets_409(client):
    async def hold():
        await main.run_lock.acquire()

    loop = asyncio.new_event_loop()
    loop.run_until_complete(hold())
    try:
        assert client.post("/server", json=BODY).status_code == 409
    finally:
        main.run_lock.release()
        loop.close()
