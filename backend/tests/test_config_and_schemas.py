import pytest
from pydantic import ValidationError

import config
from schemas import RunRequest


def test_safe_path_strips_directories(tmp_path):
    assert config.safe_path(tmp_path, "../../evil.py") == tmp_path / "evil.py"
    assert config.safe_path(tmp_path, r"..\..\evil.py") == tmp_path / "evil.py"


def test_safe_path_rejects_empty_name(tmp_path):
    with pytest.raises(ValueError):
        config.safe_path(tmp_path, "..")


@pytest.mark.parametrize("value,seconds", [("30s", 30), ("2m", 120), ("1h", 3600), ("45", 45)])
def test_parse_duration(value, seconds):
    assert config.parse_duration(value) == seconds


def test_parse_duration_rejects_garbage():
    with pytest.raises(ValueError):
        config.parse_duration("soon")


def test_valid_ui_request():
    req = RunRequest(url="https://example.com", category="ui_test", mode="manual_test")
    assert req.performance_params.users == 10


def test_valid_performance_request():
    req = RunRequest(
        url="http://localhost:3000", category="performance_test", mode="spike_test",
        performance_params={"users": 50, "duration": "1m"},
    )
    assert req.performance_params.users == 50


@pytest.mark.parametrize("url", ["ftp://example.com", "example.com", "javascript:alert(1)", ""])
def test_rejects_non_http_url(url):
    with pytest.raises(ValidationError):
        RunRequest(url=url, category="ui_test", mode="manual_test")


def test_rejects_mode_from_other_category():
    with pytest.raises(ValidationError):
        RunRequest(url="https://example.com", category="ui_test", mode="load_test")


def test_scenario_mode_needs_text():
    with pytest.raises(ValidationError):
        RunRequest(url="https://example.com", category="ui_test", mode="scenario_test")
