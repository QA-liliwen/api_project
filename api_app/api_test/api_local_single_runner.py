import os
import subprocess
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# 启动 pytest 子进程
def run_single_local(test_run, cases_txt_path):
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
    subprocess.Popen(
        ["pytest", os.path.join(BASE_DIR, "run_request.py"), "-v", f"--cases-file={cases_txt_path}"],
        env=pytest_env,
        cwd=BASE_DIR,
    )
