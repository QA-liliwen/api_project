# 工具注册机制与公共辅助
# 本文件不依赖 Django，工具模块可脱离 Web 层单独调用

# tool_key -> handler
TOOL_REGISTRY = {}


# 工具业务异常，由视图层统一转成 code:-1 响应
class ToolError(Exception):
    pass


# 把工具入口函数登记到全局注册表
def register_tool(tool_key):
    def wrapper(func):
        if tool_key in TOOL_REGISTRY:
            raise RuntimeError(f"工具 key 重复注册: {tool_key}")
        TOOL_REGISTRY[tool_key] = func
        return func
    return wrapper


# 取字符串参数，required 时缺失或空白直接报错
def get_str_param(params, key, required=True, default=''):
    value = params.get(key, default)
    if value is None:
        value = default
    if not isinstance(value, str):
        value = str(value)
    if required and value.strip() == '':
        raise ToolError(f"参数 {key} 不能为空")
    return value


# 取枚举参数，不在候选范围内直接报错
def get_choice_param(params, key, choices, default=None):
    value = params.get(key) or default
    if value not in choices:
        raise ToolError(f"参数 {key} 取值非法，可选值: {', '.join(choices)}")
    return value
