import os
import time
import pytest
import requests


def pytest_addoption(parser):
    parser.addoption(
        "--cases-file",
        action="store",
        default=None,
        help="测试用例文件路径"
    )


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
    base_url = os.environ.get("BASE_URL", "http://172.16.2.60:8000")
    payload = {
        "test_run_id": int(test_run_id),
        "status": status,
        "total": total,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "finished_at": finished_at,
        "duration": duration
    }

    # Jenkins 环境下回填真实构建链接与报告文件名（触发时拿不到构建号）
    build_url = os.environ.get("BUILD_URL")
    if build_url:
        payload["jenkins_build_url"] = build_url
        payload["report_file"] = f"report_{test_run_id}.html"

    # 回调失败不能中断 pytest，打印结果便于 Jenkins 日志排查
    try:
        resp = requests.post(f"{base_url}/update_run_result/", json=payload, timeout=10)
        print(f"\n[回调平台] {base_url} -> {resp.status_code} {resp.text[:200]}")
    except Exception as e:
        print(f"\n[回调平台失败] {base_url} -> {e}")
