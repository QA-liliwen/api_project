import os
import time
import pytest
import requests


def pytest_terminal_summary(terminalreporter, exitstatus):
    STATUS_MAP = {
        pytest.ExitCode.OK: "passed",
        pytest.ExitCode.TESTS_FAILED: "failed",
        pytest.ExitCode.INTERRUPTED: "interrupted",
        pytest.ExitCode.INTERNAL_ERROR: "internal_error",
        pytest.ExitCode.USAGE_ERROR: "usage_error",
        pytest.ExitCode.NO_TESTS_COLLECTED: "no_tests",
    }
    status = STATUS_MAP.get(exitstatus, "unknown")
    passed = len(terminalreporter.stats.get('passed', []))
    failed = len(terminalreporter.stats.get('failed', []))
    skipped = len(terminalreporter.stats.get('skipped', []))
    total = passed + failed + skipped

    start_at_ts = float(os.environ.get("STARTED_AT", time.time()))
    finished_at = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    duration = time.time() - start_at_ts

    test_run_id = os.environ.get("TEST_RUN_ID")
    resp = requests.post("http://127.0.0.1:8000/update_run_result/",
        json={
            "test_run_id": int(test_run_id),
            "status": status,
            "total": total,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "finished_at": finished_at,
            "duration": duration
        },
        timeout=10
    )
