import time
from datetime import datetime

from api_app.api_tools.base import ToolError, register_tool, get_str_param, get_choice_param

DIRECTIONS = ('ts_to_date', 'date_to_ts')

# 日期字符串的候选解析格式，按顺序尝试
DATE_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d",
    "%Y/%m/%d %H:%M:%S",
    "%Y/%m/%d %H:%M",
    "%Y/%m/%d",
)


# 时间戳与日期字符串互转，秒/毫秒自动识别
@register_tool('timestamp_convert')
def run(params):
    direction = get_choice_param(params, 'direction', DIRECTIONS, default='ts_to_date')
    text = get_str_param(params, 'text').strip()

    now = time.time()
    data = {
        "now_seconds": str(int(now)),
        "now_milliseconds": str(int(now * 1000)),
    }

    if direction == 'ts_to_date':
        if not text.isdigit():
            raise ToolError("时间戳必须为纯数字")
        # 13 位及以上按毫秒处理，否则按秒
        if len(text) >= 13:
            data["unit"] = "毫秒"
            seconds = int(text) / 1000
        else:
            data["unit"] = "秒"
            seconds = int(text)
        try:
            data["result"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(seconds))
        except (OSError, ValueError, OverflowError):
            raise ToolError("时间戳超出可转换范围")
        return data

    # date_to_ts：逐个格式尝试解析
    dt = None
    for fmt in DATE_FORMATS:
        try:
            dt = datetime.strptime(text, fmt)
            break
        except ValueError:
            continue
    if dt is None:
        raise ToolError("日期格式无法识别，支持如 2026-09-04 18:30:00")

    ts = dt.timestamp()
    data["result"] = str(int(ts))
    data["result_milliseconds"] = str(int(ts * 1000))
    return data
