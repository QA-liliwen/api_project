import os
import subprocess
import time
from django.utils import timezone
from api_app.models import DB_TestItem, DB_run_result

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(BASE_DIR)))
SCRIPTS_DIR = os.path.join(os.path.dirname(BASE_DIR), "data", "scripts")


def run_custom(test_item_ids, description, base_url, env=''):
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

    # 创建本次执行的临时目录（放在项目根目录下，避免加载父目录 conftest）
    run_dir = os.path.join(PROJECT_ROOT, "custom_runs", str(test_run.id))
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

    # 写入 conftest.py（用于跑完后回调平台）
    with open(os.path.join(BASE_DIR, "conftest.py"), "r", encoding="utf-8") as f:
        conftest_content = f.read()
    with open(os.path.join(run_dir, "conftest.py"), "w", encoding="utf-8") as f:
        f.write(conftest_content)

    # 设置环境变量
    pytest_env = os.environ.copy()
    pytest_env["TEST_RUN_ID"] = str(test_run.id)
    pytest_env["BASE_URL"] = base_url
    pytest_env["STARTED_AT"] = str(started_ts)

    # 日志文件路径
    log_file_name = f"{test_run.id}_app.log"
    test_run.log_file = log_file_name
    test_run.save()
    pytest_env["LOG_FILE_NAME"] = log_file_name

    report_file = f"report_{test_run.id}.xml"
    test_run.report_file = report_file
    test_run.save()

    # 启动 pytest
    subprocess.Popen(
        ["pytest", run_dir, "-v", f"--junitxml={os.path.join(run_dir, report_file)}"],
        env=pytest_env,
        cwd=run_dir,
    )

    return {"code": 0, "message": "success", "run_id": test_run.id}, 200
