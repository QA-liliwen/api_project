import json
import os
import subprocess
import time
import openpyxl
from django.http import JsonResponse
from django.utils import timezone
from api_app.models import *

xlsx_header_cn = ['CaseID', '用例名称', '是否执行', '请求体', '预期状态码', '断言', '描述']
xlsx_header_en = ['CaseID', 'case_name', 'is_active', 'body', 'expected_status_code', 'assertions', 'description']
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
XLSX_DIR = os.path.join(os.path.dirname(BASE_DIR), "data", "xlsx")


def upload_case(request):
    file = request.FILES.get("fileUpload")
    if not file or not file.name.endswith(".xlsx"):
        return JsonResponse({"msg": "请上传 xlsx 文件"}, status=400)
    upload_xlsx_name = file.name
    file_path = os.path.join(XLSX_DIR, upload_xlsx_name)
    with open(file_path, "wb") as f:
        for chunk in file.chunks():
            f.write(chunk)
    test_item_data = read_single_case(file_path)
    if not test_item_data:
        return JsonResponse({"msg": "用例解析失败，请检查文件格式"}, status=400)
    return JsonResponse({"msg": "解析成功", "cases": test_item_data, "filename": upload_xlsx_name})


# 读取单个用例文件
def read_single_case(file_path: str):
    wb = openpyxl.load_workbook(file_path, read_only=True)
    try:
        rows = list(wb.active.iter_rows(values_only=True))
        if not rows:
            return []
        headers = [str(h).strip() for h in rows[0]]
        if headers != xlsx_header_cn:
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
                return []

            assertions = row_dict["assertions"]
            if isinstance(assertions, str):
                row_dict["assertions"] = [a.strip() for a in assertions.split(";") if a.strip()]
            else:
                row_dict["assertions"] = [str(assertions)]
            data.append(row_dict)

        print(f"解析成功，共 {len(data)} 条用例")
        return data
    finally:
        wb.close()


# 合并单个测试项的接口信息和测试用例
def build_test_item_cases(test_item_id, domain, env, headers):
    test_item = DB_TestItem.objects.get(id=test_item_id)
    interface = test_item.interface
    base_url = "https://" + interface.url.format(domain, env)

    cases = []
    for case in test_item.cases:
        new_case = {
            'url': base_url,
            'method': interface.method.upper(),
            'headers': headers,
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


# 执行主函数（核心逻辑）
def single_run_main(test_item_ids, domain, env, env_name, headers):
    run_ids = ','.join(str(i) for i in test_item_ids)
    started_ts = time.time()
    started_at = timezone.now()
    test_run = DB_run_result.objects.create(
        env=env_name,
        status="running",
        description='',
        test_items=run_ids,
        started_at=started_at,
        executor='web',
    )

    # 获取完整用例
    all_cases = []
    for item_id in test_item_ids:
        cases = build_test_item_cases(item_id, domain, env, headers)
        all_cases.extend(cases)
    test_run.total = len(all_cases)

    # 保存用例
    cases_dir = os.path.join(os.path.dirname(BASE_DIR), "data", "cases")
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
    return test_run.id


if __name__ == '__main__':
    pass
