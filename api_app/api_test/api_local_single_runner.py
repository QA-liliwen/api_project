import os
import subprocess
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# 启动 pytest 子进程
# base_url：pytest 跑完后回调平台写结果的地址（conftest.pytest_terminal_summary），
# 不注入会落到 conftest 的默认内网地址，本机 IP 变动后回调打不通、运行状态永远停在 running
def run_single_local(test_run, cases_txt_path, sql_conn=None, run_header="", base_url=""):
    started_ts = time.time()

    # 日志文件
    log_file_name = f"{test_run.id}_app.log"
    test_run.log_file = log_file_name
    test_run.save()

    # 启动 pytest 子进程
    pytest_env = os.environ.copy()
    pytest_env["TEST_RUN_ID"] = str(test_run.id)
    pytest_env["LOG_FILE_NAME"] = log_file_name
    pytest_env['STARTED_AT'] = str(started_ts)
    pytest_env["RUN_HEADER"] = run_header  # 执行前置信息（conftest 启动时写入 log 头部）
    if base_url:
        pytest_env["BASE_URL"] = base_url
    # SQL 断言连接四要素（未配置则不注入，sql: 断言自动跳过）
    if sql_conn:
        for key, value in sql_conn.items():
            pytest_env[key] = value
    subprocess.Popen(
        ["pytest", os.path.join(BASE_DIR, "run_request.py"), "-v", f"--cases-file={cases_txt_path}"],
        env=pytest_env,
        cwd=BASE_DIR,
    )
