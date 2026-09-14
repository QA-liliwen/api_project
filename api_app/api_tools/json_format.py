import json

from api_app.api_tools.base import ToolError, register_tool, get_str_param, get_choice_param

MODES = ('pretty', 'minify', 'escape', 'unescape')


# JSON 格式化 / 压缩 / 转义 / 去转义
@register_tool('json_format')
def run(params):
    text = get_str_param(params, 'text')
    mode = get_choice_param(params, 'mode', MODES, default='pretty')

    # 转义：把 JSON 文本转成可直接嵌入字符串的形式（不需要先解析）
    if mode == 'escape':
        return {"result": json.dumps(text, ensure_ascii=False)[1:-1]}

    # 去转义：还原被转义过的文本
    if mode == 'unescape':
        try:
            return {"result": json.loads(f'"{text}"')}
        except json.JSONDecodeError as e:
            raise ToolError(f"去转义失败：{e.msg}")

    # 美化 / 压缩：必须是合法 JSON
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise ToolError(f"JSON 解析失败：第 {e.lineno} 行 第 {e.colno} 列，{e.msg}")

    if mode == 'pretty':
        result = json.dumps(data, ensure_ascii=False, indent=4)
    else:
        result = json.dumps(data, ensure_ascii=False, separators=(',', ':'))

    return {"result": result, "length": len(result)}
