"""Tools the agent can call. Each one is a thin wrapper around the shared Playwright page."""
import asyncio
import base64
import json
import sys

from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

import config
from browser_manager import browser, status_store

original_url = ""

ANALYZE_JS = """() => {
    return Array.from(document.querySelectorAll('input, button, a, [role="button"]'))
        .filter(el => {
            const rect = el.getBoundingClientRect();
            return rect.width > 0 && rect.height > 0 && window.getComputedStyle(el).visibility !== 'hidden';
        })
        .slice(0, 20)
        .map(el => {
            const tag = el.tagName.toLowerCase();
            const selector = el.id ? `#${el.id}` :
              el.getAttribute('data-testid') ? `[data-testid="${el.getAttribute('data-testid')}"]` :
              el.getAttribute('aria-label') ? `[aria-label="${el.getAttribute('aria-label')}"]` :
              el.name ? `${tag}[name="${el.name}"]` :
              el.href ? `a[href="${el.getAttribute('href')}"]` :
              tag;
            const label = el.innerText || el.placeholder || el.value || 'No Label';
            return `Selector: [ ${selector} ] | Label: "${label}" | Tag: <${tag}>`;
        })
        .join('\\n');
}"""


def set_original_url(url: str) -> None:
    global original_url
    original_url = url


async def _run_script(cmd: list[str], timeout: int) -> tuple[int | None, str, str]:
    """Run a subprocess with a hard timeout. Returns (returncode, stdout, stderr)."""
    process = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    try:
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        process.kill()
        await process.wait()
        return None, "", ""
    return process.returncode, stdout.decode(errors="ignore"), stderr.decode(errors="ignore")


# ---------------------------------------------------------------- reporting
@tool
async def write_bug_report(report: str) -> str:
    """Append a bug or the final summary to the bug report file."""
    config.ensure_dirs()
    with open(config.BUG_REPORT_FILE, "a", encoding="utf-8") as file:
        file.write(f"{report}\n\n")
    return f"Report saved to {config.BUG_REPORT_FILE}"


@tool
async def update_status(step: str, message: str = "") -> str:
    """Update the current QA testing status shown in the Chrome extension."""
    status_store.update(status="running", step=step, message=message)
    return f"Status updated to: {step}"


# --------------------------------------------------------------- navigation
@tool
async def navigate_to(url: str) -> str:
    """Navigates the browser to a specific URL."""
    page = await browser.init_browser()
    await page.goto(url, wait_until="domcontentloaded")
    await page.wait_for_timeout(2000)
    return f"we reach this url: {url}"


@tool
async def navigate_to_original() -> str:
    """Go back to the original page after a click led to another page."""
    page = await browser.init_browser()
    await page.goto(original_url, wait_until="domcontentloaded")
    await page.wait_for_timeout(2000)
    return f"we reach this url: {original_url}"


@tool
async def get_url() -> str:
    """Return the current page URL so you know whether you are still on the original page."""
    page = await browser.init_browser()
    return f"here the page url: {page.url}"


# -------------------------------------------------------------- interaction
@tool
async def perform_click(selector: str) -> str:
    """Clicks on a visible HTML element using a robust strategy."""
    page = await browser.init_browser()
    try:
        locator = page.locator(selector).first
        await locator.wait_for(state="visible", timeout=10000)
        await locator.scroll_into_view_if_needed()
        try:
            await locator.click(timeout=5000)
        except Exception:
            await page.evaluate(
                "(sel) => { const el = document.querySelector(sel); if (el) el.click(); }",
                selector,
            )
        return f"Clicked: {selector}"
    except Exception as exc:
        return f"Failed: {selector} | Reason: {exc}"


@tool
async def smart_click(text: str) -> str:
    """Click an element by its visible text."""
    page = await browser.init_browser()
    try:
        await page.get_by_text(text).first.click(timeout=5000)
        return f"clicked by text: {text}"
    except Exception:
        return f"failed to click text: {text}"


@tool
async def type_text(selector: str, text: str) -> str:
    """Types text into an input field."""
    page = await browser.init_browser()
    try:
        await page.wait_for_selector(selector, timeout=30000)
        await page.fill(selector, text)
    except Exception as exc:
        return f"Failed to type into {selector}: {exc}"
    return f"this text:{text} was filled in this {selector}"


@tool
async def press_key(key: str = "Enter") -> str:
    """Presses a keyboard key (e.g. 'Enter', 'Tab', 'ArrowDown')."""
    page = await browser.init_browser()
    await page.keyboard.press(key)
    return f"pressed {key}"


# ------------------------------------------------------------ page analysis
@tool
async def analyze_page() -> str:
    """Returns CSS selectors and labels for the visible interactive elements (first 20)."""
    page = await browser.init_browser()
    elements = await page.evaluate(ANALYZE_JS)
    return f"Visible Interactive Elements:\n{elements}"


@tool
async def get_accessibility_tree() -> str:
    """Returns the page's accessibility tree: roles and structure of its elements."""
    page = await browser.init_browser()
    try:
        cdp_session = await page.context.new_cdp_session(page)
        result = await cdp_session.send("Accessibility.getFullAXTree")
        return json.dumps(result, ensure_ascii=False)
    except Exception as exc:
        return f"Failed to capture accessibility tree due to error: {exc}"


@tool
async def capture_screen(filename: str = "qa_evidence.png") -> str:
    """Take a screenshot as evidence of a bug."""
    page = await browser.init_browser()
    config.ensure_dirs()
    path = config.safe_path(config.SCREENSHOTS_DIR, filename)
    try:
        await page.screenshot(path=path)
        return f"Screenshot saved to: {path}"
    except Exception as exc:
        return f"Failed: {exc}"


@tool
async def capture_and_analyze_screen(filename: str = "qa_analysis.png") -> str:
    """Take a screenshot and describe it with a vision model (layout, elements, visible errors)."""
    page = await browser.init_browser()
    config.ensure_dirs()
    path = config.safe_path(config.SCREENSHOTS_DIR, filename)
    await page.screenshot(path=path)
    image = base64.b64encode(path.read_bytes()).decode("utf-8")
    message = HumanMessage(
        content=[
            {
                "type": "text",
                "text": (
                    "Describe the page you see: its content, its interactive and "
                    "non-interactive elements, and any apparent errors. "
                    "This is for an AI agent doing QA automation."
                ),
            },
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image}"}},
        ]
    )
    response = await ChatOpenAI(model=config.VISION_MODEL).ainvoke([message])
    return f"here vision analysis: {response.content}"


# ------------------------------------------------------- generated scripts
@tool
async def write_ui_script(filename: str, code_content: str) -> str:
    """Saves a Playwright UI test script (Python file) to disk."""
    config.ensure_dirs()
    path = config.safe_path(config.UI_TESTS_DIR, filename)
    path.write_text(code_content, encoding="utf-8")
    return f"UI Automation script saved to {path}"


@tool
async def run_ui_test(script_filename: str, timeout: int = 60) -> str:
    """Executes a saved Playwright UI test script and returns the console output."""
    path = config.safe_path(config.UI_TESTS_DIR, script_filename)
    if not path.exists():
        return f"Script file not found: {path}"
    code, out, err = await _run_script([sys.executable, str(path)], timeout)
    if code is None:
        return "UI Test execution timed out."
    if code == 0:
        return f"UI Test passed successfully.\nOutput:\n{out}"
    return f"UI Test failed.\nOutput:\n{out}\nErrors:\n{err}"


@tool
async def write_locust_script(filename: str, code_content: str) -> str:
    """Saves a Locust test script (Python file) to disk."""
    config.ensure_dirs()
    path = config.safe_path(config.LOCUST_DIR, filename)
    path.write_text(code_content, encoding="utf-8")
    return f"Locust script saved to {path}"


@tool
async def run_locust_test(script_filename: str, host: str, users: int = 10, run_time: str = "30s") -> str:
    """Executes a Locust performance test using a previously saved script."""
    path = config.safe_path(config.LOCUST_DIR, script_filename)
    if not path.exists():
        return f"Script file not found: {path}"
    try:
        seconds = config.parse_duration(run_time)
    except ValueError as exc:
        return str(exc)
    cmd = [
        sys.executable, "-m", "locust", "-f", str(path), "--host", host,
        "--users", str(users), "--run-time", f"{seconds}s", "--headless",
        "--csv", str(config.LOCUST_DIR / "locust_results"),
    ]
    code, out, err = await _run_script(cmd, seconds * 2 + 10)
    if code is None:
        return "Locust test timed out."
    return f"Locust test finished.\nOutput:\n{out}\nErrors:\n{err}"
