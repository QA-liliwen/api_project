import io
import json
import os
import zipfile
from django.utils import timezone
from api_app.models import DB_TestItem, DB_run_result
from api_app.api_test.api_jenkins_single_runner import build_jenkins_conftest, build_jenkins_log_config, trigger_jenkins_build

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_DIR = os.path.join(os.path.dirname(BASE_DIR), "data", "custom_scripts")


# 打包多接口脚本为独立 zip
def pack_custom_bundle(test_item_ids, script_vars=None, run_header=""):
    # 读取 conftest 文件（Jenkins 版：前置信息写入工作区 logs 目录；跑完后回调平台）
    conftest_content = build_jenkins_conftest()

    # 逐个读取测试项对应的脚本内容
    scripts = {}
    for item_id in test_item_ids:
        test_item = DB_TestItem.objects.get(id=item_id)
        if not test_item.script_filename:
            raise ValueError(f"测试项 {item_id} 未上传脚本文件")
        src_path = os.path.join(SCRIPTS_DIR, test_item.script_filename)
        if not os.path.exists(src_path):
            raise FileNotFoundError(f"脚本文件不存在: {test_item.script_filename}")
        with open(src_path, "r", encoding="utf-8") as f:
            scripts[f"test_flow_{item_id}.py"] = f.read()

    # 打包 zip
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("conftest.py", conftest_content)
        zf.writestr("log_config.py", build_jenkins_log_config())
        zf.writestr("requirements.txt", "requests\npytest\npytest-html\n")
        for name, content in scripts.items():
            zf.writestr(name, content)
        # 脚本运行数据（变量池种子：domain/env + 全量头 user_{角色}_{端} + 各脚本入参）
        if script_vars:
            zf.writestr("script_vars.json", json.dumps(script_vars, ensure_ascii=False, indent=2))
        # 执行前置信息（conftest 启动时写入 log 头部；pytest 输出由 Jenkins 构建命令重定向追加进同一 log，见 data/Jenkins配置.md）
        zf.writestr("run_header.txt", run_header)

    return buf.getvalue()


def run_custom_jenkins(test_item_ids, description, base_url, env='', script_vars=None, run_header=''):
    """Jenkins 执行多接口脚本测试项：打包脚本 → 触发构建 → 由 Jenkins 端回调平台"""
    test_run = DB_run_result.objects.create(
        env=env,
        status="running",
        description=description,
        test_items=','.join(str(i) for i in test_item_ids),
        started_at=timezone.now(),
        trigger_source="jenkins",
        total=len(test_item_ids),
    )

    # 打包脚本
    try:
        zip_bytes = pack_custom_bundle(test_item_ids, script_vars, run_header)
    except Exception as e:
        test_run.status = "failed"
        test_run.finished_at = timezone.now()
        test_run.save()
        return {"code": -1, "message": str(e)}, 400

    # 触发 Jenkins 构建
    try:
        jenkins_url = trigger_jenkins_build(zip_bytes, test_run.id, base_url)
    except Exception as e:
        test_run.status = "failed"
        test_run.finished_at = timezone.now()
        test_run.save()
        return {"code": -1, "message": str(e)}, 500

    test_run.jenkins_build_url = jenkins_url
    test_run.log_file = f"{test_run.id}_app.log"
    test_run.report_file = f"report_{test_run.id}.html"
    test_run.save()

    return {"code": 0, "message": "success", "run_id": test_run.id, "jenkins_build_url": jenkins_url}, 200
