import json
import os
import openpyxl
from django.http import JsonResponse
from django.utils import timezone
from api_app.models import *
from api_app.api_test.api_executor import dispatch_run

xlsx_header_cn = ['CaseID', '用例名称', '是否执行', '请求体', '预期状态码', '断言', '描述']
xlsx_header_en = ['CaseID', 'case_name', 'is_active', 'body', 'expected_status_code', 'assertions', 'description']
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
XLSX_DIR = os.path.join(BASE_DIR, "data", "xlsx")
SCRIPTS_DIR = os.path.join(BASE_DIR, "data", "scripts")


# 一级标签
def get_top_menu(request):
    first_tags = list(DB_FirstTag.objects.filter(is_del=False).order_by('sort', 'id').values())
    return JsonResponse({"first_tags": first_tags})


# 二级标签
def get_second_tags(request):
    first_tag_id = request.GET.get("first_tag_id")
    second_tags = list(DB_SecondTag.objects.filter(is_del=False, first_tag_id=first_tag_id).order_by('sort', 'id').values('id', 'name', 'sort'))
    return JsonResponse({"second_tags": second_tags})


# 测试项
def get_grouped_test_items(request):
    first_tag_id = request.GET.get("first_tag_id")
    second_tags = DB_SecondTag.objects.filter(is_del=False, first_tag_id=first_tag_id).order_by('sort', 'id')
    groups = []
    for tag in second_tags:
        items = list(DB_TestItem.objects.filter(is_del=False, second_tag=tag).order_by('sort', 'id').values('id', 'name', 'type', 'description', 'created_at'))
        groups.append({
            "second_tag_id": tag.id,
            "second_tag_name": tag.name,
            "test_items": items
        })
    return JsonResponse({"groups": groups})


# 执行配置
def get_run_config(request):
    domains = list(DB_Domain.objects.filter(is_del=False).values('id', 'name'))
    envs = list(DB_Env.objects.filter(is_del=False).values('id', 'name'))
    tokens = list(DB_Token.objects.filter(is_del=False).values('id', 'name'))
    header_templates = list(DB_HeaderTemplate.objects.filter(is_del=False).values('id', 'name'))
    return JsonResponse({
        "domains": domains,
        "envs": envs,
        "tokens": tokens,
        "header_templates": header_templates,
    })


# 上传用例文件
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


# 上传自定义脚本文件
def upload_script(request):
    print(f"[upload_script] 被调用, method={request.method}, FILES={list(request.FILES.keys())}")
    file = request.FILES.get("fileUpload")
    if not file or not file.name.endswith(".py"):
        return JsonResponse({"msg": "请上传 .py 文件"}, status=400)
    script_filename = file.name
    file_path = os.path.join(SCRIPTS_DIR, script_filename)
    with open(file_path, "wb") as f:
        for chunk in file.chunks():
            f.write(chunk)
    return JsonResponse({"msg": "上传成功", "filename": script_filename})


# 读取用例文件
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


# 测试项详情
def get_test_item_detail(request):
    item_id = request.GET.get('id')
    item = DB_TestItem.objects.filter(id=item_id, is_del=False).first()
    if not item:
        return JsonResponse({"code": -1, "message": "测试项不存在"}, status=404)
    return JsonResponse({
        "code": 0,
        "data": {
            "id": item.id,
            "name": item.name,
            "type": item.type,
            "description": item.description,
            "interface_id": item.interface_id,
            "cases": item.cases,
            "script_content": item.script_content,
            "script_filename": item.script_filename,
            "sort": item.sort,
        }
    })


# 接口列表
def get_interfaces(request):
    interfaces = list(DB_Interface.objects.filter(is_del=False).order_by('sort', 'id').values('id', 'name'))
    return JsonResponse({"interfaces": interfaces})


# 更新或创建测试项
def update_test_item(request):
    if request.method != 'POST':
        return JsonResponse({"code": -1, "message": "仅支持 POST 请求"}, status=405)
    if not request.body:
        return JsonResponse({"code": -1, "message": "请求体为空"}, status=400)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"code": -1, "message": "请求体不是合法 JSON"}, status=400)

    item_id = data.get('id')
    is_create = not item_id or item_id == 'new'

    if is_create:
        second_tag_id = data.get('second_tag_id')
        if not second_tag_id:
            return JsonResponse({"code": -1, "message": "新建测试项需要选择二级标签"}, status=400)
        item = DB_TestItem(second_tag_id=second_tag_id)
    else:
        item = DB_TestItem.objects.filter(id=item_id, is_del=False).first()
        if not item:
            return JsonResponse({"code": -1, "message": "测试项不存在"}, status=404)

    if data.get('is_del'):
        item.is_del = True
        item.save()
        return JsonResponse({"code": 0, "message": "删除成功"})

    item.name = data.get('name', item.name if not is_create else '未命名')
    item.type = data.get('type', item.type if not is_create else 1)
    item.description = data.get('description', item.description if not is_create else '')

    interface_id = data.get('interface_id')
    if interface_id is not None:
        item.interface_id = interface_id if interface_id != '' else None

    cases = data.get('cases')
    if cases is not None:
        item.cases = cases

    script_filename = data.get('script_filename')
    if script_filename is not None:
        item.script_filename = script_filename

    item.save()

    # 保存时重命名上传的 xlsx 文件
    uploaded_filename = data.get('uploaded_filename')
    if uploaded_filename:
        old_path = os.path.join(XLSX_DIR, uploaded_filename)
        new_name = f"{item.id}_{uploaded_filename}"
        new_path = os.path.join(XLSX_DIR, new_name)
        if os.path.exists(old_path) and old_path != new_path:
            if os.path.exists(new_path):
                os.remove(new_path)
            os.rename(old_path, new_path)

    # 保存时重命名上传的脚本文件
    uploaded_script = data.get('uploaded_script')
    if uploaded_script:
        old_path = os.path.join(SCRIPTS_DIR, uploaded_script)
        new_name = f"{item.id}_{uploaded_script}"
        new_path = os.path.join(SCRIPTS_DIR, new_name)
        if os.path.exists(old_path) and old_path != new_path:
            if os.path.exists(new_path):
                os.remove(new_path)
            os.rename(old_path, new_path)
        item.script_filename = new_name
        item.save(update_fields=['script_filename'])

    return JsonResponse({"code": 0, "message": "保存成功", "id": item.id})


# 执行测试
def execute_run(request):
    if request.method != 'POST':
        return JsonResponse({"code": -1, "message": "仅支持 POST 请求"}, status=405)
    if not request.body:
        return JsonResponse({"code": -1, "message": "请求体为空"}, status=400)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"code": -1, "message": "请求体不是合法 JSON"}, status=400)

    result, status_code = dispatch_run(data)
    return JsonResponse(result, status=status_code)


# 更新测试结果
def update_run_result(request):
    data = json.loads(request.body)
    run_id = data.get("test_run_id")
    run_result = DB_run_result.objects.get(id=run_id)
    run_result.status = data.get("status", "completed")
    run_result.total = data.get("total")
    run_result.passed = data.get("passed")
    run_result.failed = data.get("failed")
    run_result.skipped = data.get("skipped")
    run_result.duration_seconds = data.get("duration")
    run_result.finished_at = data.get("finished_at")
    run_result.report_file = data.get("report_file", run_result.report_file)
    run_result.log_file = data.get("log_file", run_result.log_file)
    run_result.jenkins_build_url = data.get("jenkins_build_url", run_result.jenkins_build_url)
    run_result.save()

    return JsonResponse({
        "code": 0,
        "message": "success",
        "data": {
            "test_run_id": run_id,
            "status": run_result.status
        }
    })