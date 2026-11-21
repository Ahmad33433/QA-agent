from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator, model_validator

UI_MODES = ("manual_test", "scripted_test", "scenario_test")
PERF_MODES = ("load_test", "stress_test", "spike_test", "endurance_test")


class PerformanceParams(BaseModel):
    users: int = Field(10, ge=0, le=1000)
    duration: str = Field("30s", pattern=r"^(\d+[smh]?)?$")


class RunRequest(BaseModel):
    url: str
    category: Literal["ui_test", "performance_test"]
    mode: Literal[UI_MODES + PERF_MODES]
    scenario_text: str = Field("", max_length=4000)
    performance_params: PerformanceParams = PerformanceParams()

    @field_validator("url")
    @classmethod
    def _http_url(cls, value: str) -> str:
        parsed = urlparse(value)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ValueError("url must be an http(s) URL")
        return value

    @model_validator(mode="after")
    def _mode_matches_category(self):
        allowed = UI_MODES if self.category == "ui_test" else PERF_MODES
        if self.mode not in allowed:
            raise ValueError(f"mode {self.mode!r} is not valid for {self.category}")
        if self.mode == "scenario_test" and not self.scenario_text.strip():
            raise ValueError("scenario_test needs scenario_text")
        return self
