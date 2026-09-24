import os
import time
import pytest
import requests


# ===== 执行前置信息写入 log（测试项/角色映射/token 结果） =====
# 来源：本地 = 环境变量 RUN_HEADER；Jenkins = 构建命令 copy run_header.txt 直写 log 后删除源文件，
# 此处检测不到即自动跳过（回退兼容：旧配置下仍可从 zip 解压的 run_header.txt 读取)
def _dump_run_header():
    header = os.environ.get("RUN_HEADER")
    if not header:
        header_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "run_header.txt")
        if os.path.exists(header_path):
            with open(header_path, "r", encoding="utf-8") as f:
                header = f.read()
    if not header:
        return
    log_file_name = os.environ.get("LOG_FILE_NAME")
    if not log_file_name:
        return
    try:
        # 注意：conftest 被 pytest 导入早于 run_request.py 的 sys.path.insert，
        # 此处无法 import log_config，直接拼路径（与 log_config.LOG_DIR 同逻辑）
        log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "logs")
        log_path = os.path.join(log_dir, log_file_name)
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(header)
    except Exception as e:
        print(f"[前置信息写入 log 失败] {e}")


_dump_run_header()


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
