import pytest

import config
import tools


@pytest.fixture(autouse=True)
def artifacts(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "ARTIFACTS_DIR", tmp_path)
    monkeypatch.setattr(config, "UI_TESTS_DIR", tmp_path / "ui_tests")
    monkeypatch.setattr(config, "LOCUST_DIR", tmp_path / "locust")
    monkeypatch.setattr(config, "SCREENSHOTS_DIR", tmp_path / "screenshots")
    monkeypatch.setattr(config, "BUG_REPORT_FILE", tmp_path / "bug_report.txt")
    return tmp_path


async def test_write_ui_script_cannot_escape_folder(artifacts):
    await tools.write_ui_script(filename="../../evil.py", code_content="print(1)")
    assert (artifacts / "ui_tests" / "evil.py").exists()
    assert not (artifacts.parent / "evil.py").exists()


async def test_run_ui_test_passes_and_fails(artifacts):
    await tools.write_ui_script(filename="ok.py", code_content="print('hello')")
    await tools.write_ui_script(filename="bad.py", code_content="raise SystemExit(1)")
    ok = await tools.run_ui_test(script_filename="ok.py")
    bad = await tools.run_ui_test(script_filename="bad.py")
    assert "passed" in ok and "hello" in ok
    assert "failed" in bad


async def test_run_ui_test_times_out(artifacts):
    await tools.write_ui_script(filename="slow.py", code_content="import time; time.sleep(30)")
    result = await tools.run_ui_test(script_filename="slow.py", timeout=1)
    assert "timed out" in result


async def test_run_ui_test_missing_script():
    result = await tools.run_ui_test(script_filename="nope.py")
    assert "not found" in result


async def test_bug_reports_are_appended(artifacts):
    await tools.write_bug_report(report="first bug")
    await tools.write_bug_report(report="second bug")
    text = (artifacts / "bug_report.txt").read_text()
    assert "first bug" in text and "second bug" in text


async def test_run_locust_rejects_bad_duration(artifacts):
    await tools.write_locust_script(filename="l.py", code_content="x=1")
    result = await tools.run_locust_test(script_filename="l.py", host="http://x", run_time="soon")
    assert "Invalid duration" in result
