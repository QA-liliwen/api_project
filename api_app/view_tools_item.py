import json

from django.http import JsonResponse

from api_app.models import DB_Tool
from api_app.api_tools import dispatch_tool
from api_app.api_tools.base import ToolError


# 工具列表（按 category 分组、按 sort 排序），供左侧菜单渲染
def get_tools(request):
    tools = DB_Tool.objects.filter(is_del=False).order_by('sort', 'id')

    groups = []
    group_index = {}
    for tool in tools:
        category = tool.category or '未分类'
        if category not in group_index:
            group_index[category] = {"category": category, "tools": []}
            groups.append(group_index[category])
        group_index[category]["tools"].append({
            "id": tool.id,
            "tool_key": tool.tool_key,
            "name": tool.name,
            "description": tool.description or '',
        })

    return JsonResponse({"code": 0, "message": "success", "groups": groups})


# 工具统一执行入口，内部按 tool_key 分发，不含任何具体工具逻辑
def run_tool(request):
    if request.method != 'POST':
        return JsonResponse({"code": -1, "message": "仅支持 POST 请求"})

    if not request.META.get('CONTENT_LENGTH'):
        return JsonResponse({"code": -1, "message": "请求体不能为空"})

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"code": -1, "message": "请求体不是合法 JSON"})

    tool_key = data.get('tool_key', '')
    if not tool_key:
        return JsonResponse({"code": -1, "message": "缺少参数 tool_key"})

    # 工具内部异常统一转成错误响应，不把 500 抛给前端
    try:
        result = dispatch_tool(tool_key, data.get('params') or {})
    except ToolError as e:
        return JsonResponse({"code": -1, "message": str(e)})
    except Exception as e:
        return JsonResponse({"code": -1, "message": f"工具执行异常: {e}"})

    return JsonResponse({"code": 0, "message": "执行成功", "data": result})
