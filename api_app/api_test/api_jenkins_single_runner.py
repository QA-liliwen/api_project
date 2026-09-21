import io
import os
import zipfile
import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JENKINS_BASE = "https://172.16.1.240:8443"
JENKINS_JOB = "Exam_APITest_Platform_Job"


# 生成 Jenkins 端使用的 log_config.py 内容（日志目录改为工作区内 logs）
def build_jenkins_log_config():
    with open(os.path.join(BASE_DIR, "log_config.py"), "r", encoding="utf-8") as f:
        content = f.read()
    content = content.replace('"../data/logs"', '"logs"')
    content = content.replace(
        'DEFAULT_FORMAT',
        'os.makedirs(os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs"), exist_ok=True)\nDEFAULT_FORMAT',
        1
    )
    return content


# 生成 Jenkins 端使用的 conftest.py 内容（前置信息写入目录改为工作区内 logs）
def build_jenkins_conftest():
    with open(os.path.join(BASE_DIR, "conftest.py"), "r", encoding="utf-8") as f:
        content = f.read()
    content = content.replace(
        'os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "logs")',
        'os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")'
    )
    return content


# 打包测试文件为独立 zip
def pack_test_bundle(test_run, cases_txt_path, run_header=""):
    cases_filename = os.path.basename(cases_txt_path)
    # 读取测试txt文件
    with open(cases_txt_path, "r", encoding="utf-8") as f:
        cases_content = f.read()

    # 读取 conftest 文件（Jenkins 版：前置信息写入工作区 logs 目录）
    conftest_content = build_jenkins_conftest()

    # 读取 run_request.py 文件
    with open(os.path.join(BASE_DIR, "run_request.py"), "r", encoding="utf-8") as f:
        run_request_content = f.read()

    # 读取 sql_assert.py 文件（SQL 断言执行器，run_request.py 依赖它）
    with open(os.path.join(BASE_DIR, "sql_assert.py"), "r", encoding="utf-8") as f:
        sql_assert_content = f.read()

    # 打包 zip
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("conftest.py", conftest_content)
        zf.writestr("run_request.py", run_request_content)
        zf.writestr("sql_assert.py", sql_assert_content)
        zf.writestr("log_config.py", build_jenkins_log_config())
        zf.writestr("requirements.txt", "requests\npytest\npytest-html\npymysql\n")
        zf.writestr(cases_filename, cases_content)
        zf.writestr("run_header.txt", run_header)  # 执行前置信息（conftest 启动时写入 log 头部）
        # 用例文件与收集规则固化到 pytest.ini，Jenkins 端统一执行 pytest .
        # run_request.py 不符合 pytest 默认的 test_*.py 命名，需显式加入 python_files
        zf.writestr(
            "pytest.ini",
            f"[pytest]\naddopts = --cases-file={cases_filename}\npython_files = run_request.py test_*.py\n"
        )

    return buf.getvalue()


def trigger_jenkins_build(zip_bytes, run_id, base_url, sql_conn=None):
    """POST 到 Jenkins Job，上传 zip 包，返回构建页面 URL"""
    jenkins_base = JENKINS_BASE
    jenkins_job_url = f"{jenkins_base}/job/{JENKINS_JOB}/buildWithParameters"

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
    # SQL 断言连接四要素（Jenkins job 需声明同名 4 个参数）
    if sql_conn:
        data.update(sql_conn)

    resp = session.post(jenkins_job_url, files=files, data=data, timeout=30)
    if resp.status_code not in (200, 201):
        raise Exception(f"Jenkins 触发失败: HTTP {resp.status_code}, {resp.text[:200]}")

    return resp.headers.get('Location', '')
