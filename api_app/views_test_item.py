import datetime
import json

from django.shortcuts import render
from django.http import JsonResponse

from api_app.models import *


# Create your views here.

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
    run_result.report_file = data.get("report_file")
    run_result.log_file = data.get("log_file")
    run_result.jenkins_build_url = data.get("jenkins_build_url")
    run_result.save()

    return JsonResponse({
        "code": 0,
        "message": "success",
        "data": {
            "test_run_id": run_id,
            "status": run_result.status
        }
    })


# 一级标签（顶部菜单数据）
def get_top_menu(request):
    first_tags = list(DB_FirstTag.objects.filter(is_del=False).order_by('sort', 'id').values())
    return JsonResponse({"first_tags": first_tags})


# 二级标签数据（左侧菜单数据，按一级标签筛选）
def get_second_tags(request):
    first_tag_id = request.GET.get("first_tag_id")
    second_tags = list(DB_SecondTag.objects.filter(is_del=False, first_tag_id=first_tag_id).order_by('sort', 'id').values('id', 'name', 'sort'))
    return JsonResponse({"second_tags": second_tags})


# 测试项数据（按一级标签筛选）
def get_test_items(request):
    test_items = list(DB_TestItem.objects.filter(is_del=False).order_by('sort', 'id').values('id', 'name', 'type', 'description', 'created_at'))
    return JsonResponse({"test_items": test_items})


# 按一级标签获取二级标签分组的测试项
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


# 获取执行配置（域名/环境/Token/请求头模板）
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


# 执行测试（选中项 → 查配置 → 调 run_main）
def execute_run(request):
    from api_app.api_test.api_single_runner import run_main

    data = json.loads(request.body)
    test_item_ids = data.get('test_item_ids', [])
    domain_id = data.get('domain_id')
    env_id = data.get('env_id')
    token_id = data.get('token_id')
    header_template_id = data.get('header_template_id')

    if not test_item_ids:
        return JsonResponse({"code": -1, "message": "未选择测试项"}, status=400)

    # 查询配置
    domain_obj = DB_Domain.objects.filter(id=domain_id, is_del=False).first()
    env_obj = DB_Env.objects.filter(id=env_id, is_del=False).first()
    token_obj = DB_Token.objects.filter(id=token_id, is_del=False).first()
    header_obj = DB_HeaderTemplate.objects.filter(id=header_template_id, is_del=False).first()

    if not domain_obj or not env_obj:
        return JsonResponse({"code": -1, "message": "域名或环境未配置"}, status=400)

    # 构建请求头
    headers = header_obj.headers.copy() if header_obj else {}
    if token_obj:
        headers['token'] = token_obj.token

    # 调用 run_main
    run_id = run_main(test_item_ids, domain_obj.domain, env_obj.env, env_obj.name, headers)
    return JsonResponse({"code": 0, "message": "success", "run_id": run_id})


# 获取测试项详情（编辑时回填）
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
            "sort": item.sort,
        }
    })


# 获取所有接口列表（用于下拉框）
def get_interfaces(request):
    interfaces = list(DB_Interface.objects.filter(is_del=False).order_by('sort', 'id').values('id', 'name'))
    return JsonResponse({"interfaces": interfaces})


# 更新测试项
def update_test_item(request):
    data = json.loads(request.body)
    item_id = data.get('id')
    item = DB_TestItem.objects.filter(id=item_id, is_del=False).first()
    if not item:
        return JsonResponse({"code": -1, "message": "测试项不存在"}, status=404)

    # 软删除
    if data.get('is_del'):
        item.is_del = True
        item.save()
        return JsonResponse({"code": 0, "message": "删除成功"})

    item.name = data.get('name', item.name)
    item.type = data.get('type', item.type)
    item.description = data.get('description', item.description)

    interface_id = data.get('interface_id')
    if interface_id is not None:
        item.interface_id = interface_id if interface_id != '' else None

    cases = data.get('cases')
    if cases is not None:
        item.cases = cases

    item.save()
    return JsonResponse({"code": 0, "message": "更新成功"})


