import datetime
import json

from django.shortcuts import render
from django.http import JsonResponse

from api_app.models import *


# Create your views here.

# 进入首页
def api_list(request):
    Interface = DB_Interface.objects.filter(is_del=False).order_by('id')
    TestItem = DB_TestItem.objects.filter(is_del=False).order_by("id")
    res = {"Interface": Interface, "TestItem": TestItem}
    return render(request, 'api_list.html', res)

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
