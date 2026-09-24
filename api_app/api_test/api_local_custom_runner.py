import json
import os
import subprocess
import time
from django.utils import timezone
from api_app.models import DB_TestItem, DB_run_result

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_DIR = os.path.join(os.path.dirname(BASE_DIR), "data", "custom_scripts")
LOGS_DIR = os.path.join(os.path.dirname(BASE_DIR), "data", "logs")
CUSTOM_RUNS_DIR = os.path.join(os.path.dirname(BASE_DIR), "data", "custom_runs")


# 生成多接口本地执行目录使用的 conftest.py
# 前置信息写入目录改为绝对路径兜底（conftest 位于 custom_runs/{run_id}/ 下，
# 原相对路径 "../data/logs" 会解析到 custom_runs/data/logs；正常链路头部由父进程直接写入，
# 此处替换仅防手动调试设 RUN_HEADER 时写错目录）
def build_custom_conftest():
    with open(os.path.join(BASE_DIR, "conftest.py"), "r", encoding="utf-8") as f:
        content = f.read()
    content = content.replace(
        'os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "logs")',
        repr(LOGS_DIR)
    )
    return content


def run_custom(test_item_ids, description, base_url, env='', script_vars=None, run_header=''):
    """执行多接口脚本测试项：写临时文件 → pytest 执行 → 回调平台"""
    started_ts = time.time()

    # 创建执行记录
    test_run = DB_run_result.objects.create(
        env=env,
        status="running",
        description=description,
        test_items=','.join(str(i) for i in test_item_ids),
        started_at=timezone.now(),
        trigger_source="local",
        total=len(test_item_ids),
    )

    # 创建本次执行的临时目录（放在 data 目录下，上级目录无 conftest.py，不会加载父目录 conftest）
    run_dir = os.path.join(CUSTOM_RUNS_DIR, str(test_run.id))
    os.makedirs(run_dir, exist_ok=True)

    # 将每个测试项的脚本文件复制到执行目录
    try:
        for item_id in test_item_ids:
            test_item = DB_TestItem.objects.get(id=item_id)
            if not test_item.script_filename:
                raise ValueError(f"测试项 {item_id} 未上传脚本文件")
            src_path = os.path.join(SCRIPTS_DIR, test_item.script_filename)
            if not os.path.exists(src_path):
                raise FileNotFoundError(f"脚本文件不存在: {test_item.script_filename}")
            dst_name = f"test_flow_{item_id}.py"
            dst_path = os.path.join(run_dir, dst_name)
            with open(src_path, "r", encoding="utf-8") as f:
                content = f.read()
            with open(dst_path, "w", encoding="utf-8") as f:
                f.write(content)
    except Exception as e:
        test_run.status = "failed"
        test_run.save()
        return {"code": -1, "message": str(e)}, 400

    # 写入脚本运行数据（变量池种子：domain/env + 全量头 user_{角色}_{端} + 各脚本入参）
    if script_vars:
        with open(os.path.join(run_dir, "script_vars.json"), "w", encoding="utf-8") as f:
            json.dump(script_vars, f, ensure_ascii=False, indent=2)

    # 写入 conftest.py（用于跑完后回调平台；日志目录改为绝对路径，指向平台统一 logs 目录）
    with open(os.path.join(run_dir, "conftest.py"), "w", encoding="utf-8") as f:
        f.write(build_custom_conftest())

    # 设置环境变量
    pytest_env = os.environ.copy()
    pytest_env["TEST_RUN_ID"] = str(test_run.id)
    pytest_env["BASE_URL"] = base_url
    pytest_env["STARTED_AT"] = str(started_ts)
    pytest_env["PYTHONIOENCODING"] = "utf-8"  # pytest 输出含中文，防止重定向落盘时 GBK 编码报错
    # 注意：前置信息不走 RUN_HEADER 环境变量——Windows 下子进程继承的 stdout 句柄无追加语义，
    # pytest 输出会从共享文件指针处覆盖 conftest 追加写的头部，故由父进程直接先写入 log

    # 日志文件路径
    log_file_name = f"{test_run.id}_app.log"
    test_run.log_file = log_file_name
    test_run.save()
    pytest_env["LOG_FILE_NAME"] = log_file_name

    report_file = f"report_{test_run.id}.xml"
    test_run.report_file = report_file
    test_run.save()

    # 启动 pytest（stdout/stderr 追加写入 app.log：脚本不打业务日志，
    # 用例通过/失败结果与失败断言详情全靠 pytest 输出落盘）
    # 前置信息由父进程先写入（写入后共享文件指针停在头部末尾，子进程输出顺延其后不被覆盖）
    log_file = open(os.path.join(LOGS_DIR, log_file_name), "a", encoding="utf-8")
    if run_header:
        log_file.write(run_header)
        log_file.flush()
    subprocess.Popen(
        ["pytest", run_dir, "-v", f"--junitxml={os.path.join(run_dir, report_file)}"],
        env=pytest_env,
        cwd=run_dir,
        stdout=log_file,
        stderr=subprocess.STDOUT,
    )
    log_file.close()

    return {"code": 0, "message": "success", "run_id": test_run.id}, 200
