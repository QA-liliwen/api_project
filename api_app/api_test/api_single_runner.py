import time
import datetime
import json
import os
import subprocess
import openpyxl
from django.http import HttpResponse
from api_app.models import *

xlsx_header_cn = ['CaseID', '用例名称', '是否执行', '请求体', '预期状态码', '断言', '描述']
xlsx_header_en = ['CaseID', 'case_name', 'is_active', 'body', 'expected_status_code', 'assertions', 'description']
DOMAIN = "devapi1.lingshi.com"
ENV = "vs2"
DEFAULT_HEADERS = {
    "Connection": "keep-alive",
    "DeviceType": "0",
    "AppType": "6",
    "industryType": "Education",
    "DeviceUniqueId": "d91ed0b9-290c-4700-ad1e-1d619d625e54",
    "InstId": "462821",
    "serverId": "1201",
    "uc": "TYTY_TEST",
    "AppVersion": "4.3.86.177814",
    "lan": "ch",
    "Requestuniqueid": "761948_4367_1699530093582_355",
    "token": "462821:1848276668:20f80e61-2e0a-461c-b5e8-971253b27c39:1ac8d2da75a73686aee7276efda59e25:1201v",
    "Content-Type": "application/json",
    "FromAppName": "Test-automate",
    "Host": "devapi1.lingshi.com",
    "User-Agent": "Apache-HttpClient/4.5.14 (Java/1.8.0_202)"
}
upload_item_id = 2


# 文件存储
def upload_case(request):
    file = request.FILES.get("fileUpload")
    if not file or not file.name.endswith(".xlsx"):
        return HttpResponse("请上传 xlsx 文件")
    test_item = DB_TestItem.objects.get(id=upload_item_id)
    # 存文件
    upload_xlsx_name = f"{upload_item_id}_{test_item.name}.xlsx"
    save_dir = "api_app/data/xlsx"
    file_path = os.path.join(save_dir, upload_xlsx_name)
    with open(file_path, "wb+") as f:
        for chunk in file.chunks():
            f.write(chunk)
    # 存数据库
    test_item_data = read_single_case(file_path)
    test_item.cases = test_item_data
    test_item.save()
    return HttpResponse("上传成功")


# 读取单个用例文件
def read_single_case(file_path: str):
    wb = openpyxl.load_workbook(file_path, read_only=True)
    rows = list(wb.active.iter_rows(values_only=True))

    if not rows:
        wb.close()
        return []
    headers = [str(h).strip() for h in rows[0]]
    if headers != xlsx_header_cn:
        wb.close()
        return []

    data = []
    for row_idx, row in enumerate(rows[1:], start=2):
        row_dict = {}
        for idx, header in enumerate(xlsx_header_en):
            value = row[idx] if idx < len(row) else ""
            if value is None:
                value = ""
            elif isinstance(value, str):
                value = value.strip()
                if value.startswith("{") and value.endswith("}"):
                    try:
                        value = json.loads(value)
                    except json.JSONDecodeError:
                        pass
            row_dict[header] = value
        print(f"第 {row_idx} 行: {row_dict}")

        if not row_dict.get("expected_status_code") or not row_dict.get("assertions"):
            print(f"错误：第 {row_idx} 行 预期状态码/断言 为空")
            wb.close()
            return []

        row_dict["assertions"] = [a.strip() for a in row_dict["assertions"].split(";") if a.strip()]
        data.append(row_dict)

    wb.close()
    print(f"解析成功，共 {len(data)} 条用例")
    return data


# 合并单个测试项的接口信息和测试用例
def build_test_item_cases(test_item_id):
    test_item = DB_TestItem.objects.get(id=test_item_id)
    interface = DB_Interface.objects.get(id=test_item.interface)
    base_url = "https://"+interface.url.format(DOMAIN, ENV)

    cases = []
    for case in test_item.cases:
        new_case = {
            'url': base_url,
            'method': interface.method.upper(),
            'headers': DEFAULT_HEADERS,
            'CaseID': case['CaseID'],
            'case_name': case['case_name'],
            'is_active': case['is_active'],
            'body': case['body'],
            'expected_status_code': case['expected_status_code'],
            'assertions': case['assertions'],
            'description': case['description']
        }
        cases.append(new_case)
    return cases


# 执行主函数
def run_main(request):
    run_ids = request.POST.get("ids", "")
    run_items = run_ids.split(",")
    description = ''
    started_ts = time.time()
    started_at = datetime.datetime.fromtimestamp(started_ts)
    test_run = DB_run_result.objects.create(
        env=ENV,
        status="running",
        description=description,
        test_items=run_ids,
        started_at=started_at
    )
    # print(test_run.id)

    # 获取完整用例
    all_cases = []
    for run_item in run_items:
        cases = build_test_item_cases(run_item)
        all_cases.extend(cases)

    # 保存用例
    PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    cases_dir = os.path.join(PROJECT_DIR, "api_app", "data", "cases")
    cases_txt_name = f"{test_run.id}_cases.txt"
    cases_txt_path = os.path.join(cases_dir, cases_txt_name)
    with open(cases_txt_path, "w", encoding="utf-8") as f:
        json.dump(all_cases, f, ensure_ascii=False, indent=2)
    test_run.cases_json_file = cases_txt_name

    # 日志文件
    log_file_name = f"{test_run.id}_app.log"
    test_run.log_file = log_file_name

    test_run.save()

    pytest_env = os.environ.copy()
    pytest_env["TEST_RUN_ID"] = str(test_run.id)
    pytest_env["CASES_FILE"] = cases_txt_path
    pytest_env["LOG_FILE_NAME"] = log_file_name
    pytest_env['STARTED_AT'] = str(started_ts)
    subprocess.Popen(
        ["pytest", os.path.join(BASE_DIR, "tests.py"), "-v"],
        env=pytest_env,
        cwd=BASE_DIR,
    )
    return HttpResponse('')


if __name__ == '__main__':
    pass
