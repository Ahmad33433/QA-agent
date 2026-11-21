"""Settings read from the environment (see .env.example). No machine-specific paths."""
import os
import re
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
ARTIFACTS_DIR = Path(os.getenv("QA_ARTIFACTS_DIR", BASE_DIR / "artifacts")).resolve()
UI_TESTS_DIR = ARTIFACTS_DIR / "ui_tests"
LOCUST_DIR = ARTIFACTS_DIR / "locust"
SCREENSHOTS_DIR = ARTIFACTS_DIR / "screenshots"
BUG_REPORT_FILE = ARTIFACTS_DIR / "bug_report.txt"

# "openai" (OPENAI_API_KEY) or "gemini" (GOOGLE_API_KEY)
LLM_PROVIDER = os.getenv("QA_LLM_PROVIDER", "openai").lower()
_DEFAULT_MODELS = {"openai": ("gpt-5-mini", "gpt-4o"), "gemini": ("gemini-2.5-flash", "gemini-2.5-flash")}
if LLM_PROVIDER not in _DEFAULT_MODELS:
    raise ValueError(f"QA_LLM_PROVIDER must be one of {sorted(_DEFAULT_MODELS)}, got {LLM_PROVIDER!r}")
AGENT_MODEL = os.getenv("QA_AGENT_MODEL", _DEFAULT_MODELS[LLM_PROVIDER][0])
VISION_MODEL = os.getenv("QA_VISION_MODEL", _DEFAULT_MODELS[LLM_PROVIDER][1])
# Cap on model calls per minute (0 = no cap). Gemini free tier allows about 5.
REQUESTS_PER_MINUTE = float(os.getenv("QA_REQUESTS_PER_MINUTE", "0"))
HEADLESS = os.getenv("QA_HEADLESS", "false").lower() in ("1", "true", "yes")

HOST = os.getenv("QA_HOST", "127.0.0.1")
PORT = int(os.getenv("QA_PORT", "8000"))
ALLOWED_ORIGINS = [o.strip() for o in os.getenv("QA_ALLOWED_ORIGINS", "*").split(",") if o.strip()]

# LangSmith tracing is optional: only turned on when a key is present.
if os.getenv("LANGSMITH_API_KEY"):
    os.environ.setdefault("LANGSMITH_TRACING", "true")

_DURATION = re.compile(r"^(\d+)([smh]?)$")


def ensure_dirs() -> None:
    for folder in (UI_TESTS_DIR, LOCUST_DIR, SCREENSHOTS_DIR):
        folder.mkdir(parents=True, exist_ok=True)


def safe_path(folder: Path, filename: str) -> Path:
    """Join `filename` onto `folder`, keeping only its last path part.

    The filename comes from the LLM, so "../../x.py" must not escape the folder.
    """
    name = Path(str(filename).replace("\\", "/")).name
    if not name or name in (".", ".."):
        raise ValueError(f"Invalid file name: {filename!r}")
    return folder / name


def parse_duration(value: str) -> int:
    """Turn "30s", "2m", "1h" or "45" (seconds) into seconds."""
    match = _DURATION.match(value.strip())
    if not match:
        raise ValueError(f"Invalid duration: {value!r}")
    amount, unit = int(match.group(1)), match.group(2) or "s"
    return amount * {"s": 1, "m": 60, "h": 3600}[unit]
