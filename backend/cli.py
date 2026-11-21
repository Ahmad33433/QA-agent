"""Run one test from the command line (same code path as POST /server).

    uv run python cli.py http://127.0.0.1:8765/index.html --mode manual_test
"""
import argparse
import asyncio
import json
import sys

import config
import main
from schemas import PERF_MODES, UI_MODES, RunRequest


async def run(args) -> int:
    category = "performance_test" if args.mode in PERF_MODES else "ui_test"
    req = RunRequest(
        url=args.url, category=category, mode=args.mode, scenario_text=args.scenario or "",
        performance_params={"users": args.users, "duration": args.duration},
    )
    config.ensure_dirs()
    system_prompt, tool_names, user_message = main.build_run(req)
    try:
        report = await main.run_agent(req, system_prompt, tool_names, user_message)
    except Exception as exc:
        print(f"Run failed: {main.root_cause(exc)!r}", file=sys.stderr)
        return 1
    print(json.dumps({"report": report}, indent=2, ensure_ascii=False))
    print(f"\nBug report file: {config.BUG_REPORT_FILE}")
    return 0


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("url")
    parser.add_argument("--mode", choices=UI_MODES + PERF_MODES, default="manual_test")
    parser.add_argument("--scenario", help="text for scenario_test")
    parser.add_argument("--users", type=int, default=10)
    parser.add_argument("--duration", default="30s")
    return parser.parse_args()


if __name__ == "__main__":
    sys.exit(asyncio.run(run(parse_args())))
