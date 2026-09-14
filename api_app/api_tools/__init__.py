from api_app.api_tools.base import TOOL_REGISTRY, ToolError

# 显式导入各工具模块，触发 register_tool 装饰器完成注册
# 新增工具时在此追加一行导入
from api_app.api_tools import json_format          # noqa: F401
from api_app.api_tools import timestamp_convert    # noqa: F401
from api_app.api_tools import user_info          # noqa: F401


# 按 tool_key 找到 handler 并执行，返回值即接口 data 字段内容
def dispatch_tool(tool_key, params):
    handler = TOOL_REGISTRY.get(tool_key)
    if not handler:
        raise ToolError(f"工具未注册: {tool_key}")
    return handler(params or {})
