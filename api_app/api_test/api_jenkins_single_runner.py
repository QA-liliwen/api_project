import io
import os
import zipfile
import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# 打包测试文件为独立 zip（去 Django 依赖）
def pack_test_bundle(test_run, cases_txt_path):
    cases_filename = os.path.basename(cases_txt_path)
    with open(cases_txt_path, "r", encoding="utf-8") as f:
        cases_content = f.read()

    # 读取原始文件（tests.py 已合并进 run_request.py）
    with open(os.path.join(BASE_DIR, "conftest.py"), "r", encoding="utf-8") as f:
        conftest_content = f.read()
    conftest_content = conftest_content.replace(
        '"http://127.0.0.100:8000/update_run_result/"',
        'f\'{os.environ.get("BASE_URL", "http://127.0.0.100:8000")}/update_run_result/\''
    )

    # run_request.py: 把 Django import 改成本地 import
    with open(os.path.join(BASE_DIR, "run_request.py"), "r", encoding="utf-8") as f:
        run_request_content = f.read()
    run_request_content = run_request_content.replace(
        'from api_app.api_test.log_config import get_logger',
        'from log_config import get_logger'
    )

    # log_config.py: 替换日志目录（Jenkins 端无 data/logs 结构）
    with open(os.path.join(BASE_DIR, "log_config.py"), "r", encoding="utf-8") as f:
        log_config_content = f.read()
    log_config_content = log_config_content.replace('"../data/logs"', '"logs"')
    log_config_content = log_config_content.replace(
        'DEFAULT_FORMAT',
        'os.makedirs(os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs"), exist_ok=True)\nDEFAULT_FORMAT',
        1
    )

    # 打包 zip
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("conftest.py", conftest_content)
        zf.writestr("run_request.py", run_request_content)
        zf.writestr("log_config.py", log_config_content)
        zf.writestr("requirements.txt", "requests\npytest\n")
        zf.writestr(cases_filename, cases_content)

    return buf.getvalue()


def trigger_jenkins_build(zip_bytes, run_id, base_url):
    """POST 到 Jenkins Job，上传 zip 包，返回构建页面 URL"""
    jenkins_base = "https://172.16.1.240:8443"
    jenkins_job_url = f"{jenkins_base}/job/Exam_APITest_Platform_Job/buildWithParameters"

    # 用 Session 保持会话一致性（Cookie + crumb）
    session = requests.Session()
    session.auth = ('qaadmin', 'qatest2027')
    session.verify = False

    # 获取 CSRF crumb
    crumb_resp = session.get(f"{jenkins_base}/crumbIssuer/api/json", timeout=10)
    crumb_data = crumb_resp.json()
    crumb_field = crumb_data['crumbRequestField']
    crumb_value = crumb_data['crumb']
    session.headers[crumb_field] = crumb_value

    files = {
        'CASE_ZIP': ('test_bundle.zip', zip_bytes, 'application/zip'),
    }
    data = {
        'RUN_ID': str(run_id),
        'BASE_URL': base_url,
        crumb_field: crumb_value,  # 同时作为表单字段
    }

    resp = session.post(jenkins_job_url, files=files, data=data, timeout=30)
    if resp.status_code not in (200, 201):
        raise Exception(f"Jenkins 触发失败: HTTP {resp.status_code}, {resp.text[:200]}")

    return resp.headers.get('Location', '')
