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