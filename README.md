# QA Agent

An LLM agent that tests a web page for you. A Chrome extension sends the current page URL to a
FastAPI backend, and the agent drives a real Chromium browser (Playwright) to find problems.
It writes a bug report when it is done.

> Prototype. It runs LLM-written scripts on your machine, so only use it on pages you own or are
> allowed to test, and only on a local machine. See [Limitations](#limitations).

## What it can do

| Category | Mode | What the agent does |
|---|---|---|
| UI test | `manual_test` | Walks through every interactive element on the page, checks the result with screenshots, and reports bugs |
| UI test | `scripted_test` | Writes a Playwright script for the page, runs it, fixes it if it fails, and reports |
| UI test | `scenario_test` | Executes a scenario you describe in plain text (for example "log in with a wrong password") |
| Performance | `load_test`, `stress_test`, `spike_test`, `endurance_test` | Finds the page's endpoints, writes a Locust script with a load shape, runs it, and reports requests per second, response times and failures |

The agent has 17 tools in `backend/tools.py`: navigation, click/type/keypress, element analysis,
the accessibility tree, screenshots (with optional vision-model analysis), script writing and
running, and bug reporting.

## Setup

Requirements: Python 3.13+, [uv](https://docs.astral.sh/uv/), Google Chrome, an OpenAI API key.

```bash
cd backend
uv sync
uv run playwright install chromium
cp .env.example .env        # then put your OPENAI_API_KEY in .env
uv run python main.py       # serves on http://127.0.0.1:8000
```

Load the extension: open `chrome://extensions`, turn on Developer mode, choose **Load unpacked**,
and select the `extension/` folder. Open any page and click the extension icon.

Reports, generated scripts and screenshots are saved in `backend/artifacts/`
(change it with `QA_ARTIFACTS_DIR`).

## API

- `POST /server`: run a test. Body: `{"url", "category", "mode", "scenario_text", "performance_params": {"users", "duration"}}`.
  The request is validated, returns `422` for bad input and `409` if a test is already running.
- `GET /status`: current step, polled by the extension.

## Project layout

```
backend/
  main.py             FastAPI app: validation, picks prompt + tools, runs the agent
  prompts.py          System prompt for each mode
  tools.py            The agent's tools
  schemas.py          Request validation (Pydantic)
  config.py           Settings from environment variables
  browser_manager.py  Shared Playwright browser and status
  tests/              pytest suite
extension/            Chrome extension (Manifest V3)
```

## Tests

```bash
cd backend
uv run pytest
```

Covers request validation, path safety, script execution (pass, fail, timeout), the API
(including `409` when busy), and the browser tools against a local page in headless Chromium
(skipped if Chromium is not installed). No API key is needed to run the tests.

## Limitations

- One run at a time (a single shared browser).
- Generated Playwright and Locust scripts run on your machine without a sandbox. A hostile page
  could try to influence the model, so test only pages you trust.
- CORS defaults to `*` because the extension calls the API from the page's origin. The server only
  listens on `127.0.0.1`, but any page open in your browser could call it. Set `QA_ALLOWED_ORIGINS`
  to restrict it.
- Result quality depends on the model. There is no benchmark yet of how many real bugs it finds.
