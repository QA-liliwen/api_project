import pytest
import requests
import os
import sys
import json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from log_config import get_logger
from sql_assert import run_sql_assertion, parse_sql_assert_expr, extract_db_value, smart_equal

log = get_logger(__name__)

OPS = {
    '==': lambda a, e: a == e,
    '!=': lambda a, e: a != e,
    '>=': lambda a, e: float(a) >= float(e),
    '<=': lambda a, e: float(a) <= float(e),
    '=': lambda a, e: a == e,
    '>': lambda a, e: float(a) > float(e),
    '<': lambda a, e: float(a) < float(e),
}


# 符号分割预期结果与实际结果
def parse_expr(expr):
    for op in OPS:
        if op in expr:
            path, expected = expr.split(op, 1)
            return path.strip(), op, expected.strip()
    raise ValueError(f"断言格式错误，未找到运算符: {expr}")


# 按路径从断言路径里逐层取值
def extract_by_path(resp_json, path):
    data = resp_json
    keys = [k for k in path.strip('/').split('/') if k]
    for key in keys:
        if isinstance(data, list):
            key = int(key)
        data = data[key]
    return data


# 对断言的预期结果进行数据转换
def convert_expected(expected):
    # 如果输入的expected被引号包裹，则统一认为字符串直接断言，如果不是，则进入其他类型进行校验
    if len(expected) >= 2 and expected[0] == expected[-1] and expected[0] in ('"', "'"):
        return expected[1:-1]
    expected_lower = expected.lower()
    if expected_lower == "true":
        return True
    if expected_lower == "false":
        return False
    if expected_lower in ("null", "none"):
        return None
    for i in (int, float):
        try:
            return i(expected)
        except ValueError:
            # 没引号,也不是布尔, none, int, float的数据均以字符串处理
            pass
    return expected


# 数组长度断言: len:/data/list>=1
def assert_len(expr, resp, resp_json):
    path, op, expected = parse_expr(expr)
    actual = len(extract_by_path(resp_json, path))
    log.debug(f"长度断言: len({path}) 实际={actual} {op} 期望={expected}")
    try:
        assert OPS[op](actual, int(expected)), f"len({path}) 实际={actual} {op} 期望={expected}"
    except AssertionError:
        log.error(f"长度断言失败: len({path}) 实际={actual} {op} 期望={expected}")
        raise


# 存在性断言: exists:/data/id
def assert_exists(expr, resp, resp_json):
    log.debug(f"存在性断言: {expr}")
    try:
        extract_by_path(resp_json, expr)
    except (KeyError, IndexError, TypeError):
        log.error(f"存在性断言失败: 字段不存在: {expr}")
        raise AssertionError(f"字段不存在: {expr}")


# 数据结构断言: type:/data/list=list 支持list, dict, str, int, float, bool, none
def assert_type(expr, resp, resp_json):
    path, op, expected = parse_expr(expr)
    data = extract_by_path(resp_json, path)
    actual = type(data).__name__
    if actual == 'NoneType':
        actual = 'none'
    log.debug(f"类型断言: {path} 实际={actual} 期望={expected}")
    try:
        assert actual == expected, f"{path} 实际类型={actual}, 期望={expected}"
    except AssertionError:
        log.error(f"类型断言失败: {path} 实际类型={actual}, 期望={expected}")
        raise


# 响应头断言: header:Content-Type=application/json
def assert_header(expr, resp, resp_json):
    name, op, expected = parse_expr(expr)
    actual = resp.headers.get(name)
    log.debug(f"响应头断言: {name} 实际={actual} {op} 期望={expected}")
    try:
        assert actual is not None, f"响应头不存在: {name}"
        if not OPS[op](actual, expected) and op in ('=', '=='):
            actual = actual.split(';')[0].strip()
        assert OPS[op](actual, expected), f"响应头 {name} 实际={actual} {op} 期望={expected}"
    except AssertionError:
        log.error(f"响应头断言失败: {name} 实际={actual} {op} 期望={expected}")
        raise


# 成员断言: in:/data/0/questionType=single|multiple|judge;
def assert_in(expr, resp, resp_json):
    path, op, expected = parse_expr(expr)
    data = extract_by_path(resp_json, path)
    allowed = [convert_expected(v.strip()) for v in expected.split('|')]
    log.debug(f"成员断言: {path} 实际={data} 候选列表={allowed}")
    try:
        assert data in allowed, f"{path} 实际={data} 不在候选列表 {allowed}"
    except AssertionError:
        log.error(f"成员断言失败: {path} 实际={data} 不在候选列表 {allowed}")
        raise


# 变量提取: set:变量名=JSON路径，从响应提取变量入变量池（供后续 sql: 的 ${var} 引用）
def assert_set(expr, variables, resp, resp_json):
    name, sep, path = expr.partition('=')
    if not sep or not name.strip() or not path.strip():
        raise AssertionError(f"变量提取格式错误（正确格式 set:变量名=JSON路径）: set:{expr}")
    name = name.strip()
    try:
        value = extract_by_path(resp_json, path.strip())
    except (KeyError, IndexError, TypeError):
        log.error(f"变量提取失败: {name} <- {path.strip()}（路径不存在）")
        raise AssertionError(f"变量提取失败: {name} <- {path.strip()}（路径不存在）")
    variables[name] = value
    log.debug(f"变量提取: {name} = {value}")


# SQL 断言（落库校验）:
# 三方校验: sql:select answer from t where id=${qid}=/data/answer='c'
#   查库值、入参值 都与手输预期值比较
# 省略预期值: sql:select solution from t where id=${qid}=/questions/0/solution
#   两方校验：查库值 == 入参值（库内存 JSON 字符串时自动解析后深度比较）
# 库名为空或连接四要素缺失时跳过（不报错），其余异常往上抛
def assert_sql(expr, sql_database, variables, body=None):
    # 传入的 断言内容， sql库， 变量池后，返回 断言表达式, 查询结果
    parsed = run_sql_assertion(expr, sql_database, variables)
    if parsed is None:
        return
    assert_expr, result = parsed
    # 解析断言表达式部分: =/data/answer='c' -> =, /data/answer, 'c'
    path, op, expected = parse_sql_assert_expr(assert_expr)
    expected = convert_expected(expected) if expected is not None else None

    # 路径作用于入参
    if not isinstance(body, (dict, list)):
        raise AssertionError(f"入参不是JSON对象，无法按入参路径断言: {path}")
    column = path.strip('/').split('/')[-1]
    try:
        req_value = extract_by_path(body, path)
    except (KeyError, IndexError, TypeError):
        log.error(f"入参路径不存在: {path}")
        raise AssertionError(f"入参路径不存在: {path}")
    db_value = extract_db_value(result, path)

    # 省略预期值：查库值 == 入参值（两方校验，JSON 归一化）
    if expected is None:
        log.debug(f"SQL断言(落库比对): 字段={column} 查库值={db_value!r} 入参值={req_value!r}")
        if not smart_equal(db_value, req_value):
            msg = f"SQL断言失败: 查库值 {column}={db_value!r} != 入参值 {path}={req_value!r}"
            log.error(msg)
            raise AssertionError(msg)
        return

    # 三方校验：入参值、查库值 都与预期值比较（= 比较带 JSON 归一化）
    def sql_op(a, e):
        if op in ('=', '==') and smart_equal(a, e):
            return True
        return OPS[op](a, e)

    log.debug(f"SQL断言(落库校验): 字段={column} 查库值={db_value} 入参值={req_value} {op} 期望={expected}")
    try:
        assert sql_op(req_value, expected), f"入参值 {path}={req_value} {op} 期望={expected}"
    except AssertionError:
        log.error(f"SQL断言失败(入参值): {path} 实际={req_value} {op} 期望={expected}")
        raise
    try:
        assert sql_op(db_value, expected), f"查库值 {column}={db_value} {op} 期望={expected}"
    except AssertionError:
        log.error(f"SQL断言失败(查库值): {column} 实际={db_value} {op} 期望={expected}")
        raise


# 执行主函数
def run_main(case):
    if case.get('is_active') != 'Y':
        log.debug(f"用例 {case['CaseID']} 未启用")
        pytest.skip(f"用例 {case['CaseID']} 未启用")

    resp = run_request(url=case['url'], method=case['method'], headers=case['headers'], body=case.get('body', ''))
    log.info(f"状态码断言: 实际={resp.status_code}, 期望={case['expected_status_code']}")
    assert resp.status_code == case['expected_status_code'], f"状态码: 实际={resp.status_code}, 期望={case['expected_status_code']}"
    log.info(f"数据断言: {case['assertions']}")
    log.info(f"响应体: {resp.text[:1000]}")
    resp_json = resp.json()

    # 每条用例独立变量池（set: 提取，后续 sql: 的 ${var} 引用）
    variables = {}

    for assertion_str in case['assertions']:
        # 如果断言中存在冒号，依据ASSERT_HANDLERS指向对应函数
        ASSERT_HANDLERS = {
            'len': assert_len,
            'exists': assert_exists,
            'type': assert_type,
            'header': assert_header,
            'in': assert_in,
        }
        # 分离断言的前缀和冒号和剩余内容， 
        prefix, sep, rest = assertion_str.partition(':')

        # set: 变量提取 / sql: 数据库断言（需变量池与库名，单独分发）
        if sep and prefix == 'set':
            assert_set(rest, variables, resp, resp_json)
            continue
        if sep and prefix == 'sql':
            assert_sql(rest, case.get('sql_database', ''), variables, case.get('body'))
            continue

        handler = ASSERT_HANDLERS.get(prefix) if sep else None
        if handler:
            # 如果断言使用了内置函数，传递断言内容，完整响应，响应体到对应函数
            handler(rest, resp, resp_json)
        else:
            # 数据断言
            path, op, expected = parse_expr(assertion_str)
            data = extract_by_path(resp_json, path)
            expected = convert_expected(expected)

            log.debug(f"断言: {path} 实际={data} {op} 期望={expected}")
            try:
                assert OPS[op](data, expected), f"{path} 实际={data} {op} 期望={expected}"
            except AssertionError:
                log.error(f"断言失败: {path} 实际={data} {op} 期望={expected}")
                raise


# 执行层
def run_request(url, method, headers, body=None):
    log.info(f"准备发送请求: {method.upper()} {url}")
    log.debug(f"请求头: {headers}")
    log.debug(f"请求体: {body}")
    if method == 'GET':
        if body:
            url = url + '?' + str(body)
        return requests.get(url, headers=headers)
    elif method == 'POST':
        return requests.post(url, headers=headers, json=body)
    else:
        return requests.request(method, url, headers=headers, json=body)


if __name__ == '__main__':
    pass


# ===== pytest 入口 =====
def pytest_generate_tests(metafunc):
    cases_file = metafunc.config.getoption("--cases-file") or os.environ.get("CASES_FILE")
    if not cases_file:
        return
    with open(cases_file, "r", encoding="utf-8") as f:
        cases_data = json.load(f)

    metafunc.parametrize(
        "case",
        cases_data,
        ids=[c['CaseID'] for c in cases_data]
    )


def test_api(case):
    run_main(case)
