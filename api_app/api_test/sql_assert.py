import os
import re
import json
import pymysql
from log_config import get_logger

log = get_logger(__name__)

# SQL 断言语法: sql:SELECT ...=/rows/0/status=1 （无需引号/括号包裹，JSON 零转义）
# 分界规则：断言部分必然以「比较操作符紧跟 /」开头（如 =/rows/0/status、>=/row_count）
SQL_BOUNDARY = re.compile(r'(==|!=|>=|<=|=|>|<)\s*/')  # 「操作符紧跟/」= 分界点（正常SQL里几乎不出现）


# 解析 sql: 断言段: 剥离前缀后的内容 -> (SQL语句, 断言表达式)
def parse_sql_assertion(expr):
    text = expr.strip()
    # 找第一个「操作符紧跟/」的位置 = SQL 与断言的分界
    match = SQL_BOUNDARY.search(text)
    if not match:
        raise AssertionError(f"SQL断言格式错误（未找到断言边界，正确格式: sql:SELECT ...=/路径=预期值）: {expr}")
    # 分割 SQL 和断言表达式
    sql = text[:match.start()].strip()
    assert_expr = text[match.start():].strip()
    if not sql:
        raise AssertionError(f"SQL断言格式错误（SQL语句为空）: {expr}")
    return sql, assert_expr


# ${var} 变量替换，未定义直接报错
def replace_vars(sql, variables):
    def repl(match):
        # 括号分组捕获到的变量名，如 ${qid} 里的 qid
        name = match.group(1)
        if name not in variables:
            raise AssertionError(f"SQL 变量未定义: {name}（请检查 set: 是否写在 sql: 之前）")
        return str(variables[name])

    # 匹配 ${变量名}，每匹配到一个 ${xxx} 就回调_repl函数一次
    return re.sub(r"\$\{(\w+)\}", repl, sql)


# 从环境变量读取连接四要素
def get_conn_config():
    host = os.environ.get("DB_HOST")
    port = os.environ.get("DB_PORT")
    user = os.environ.get("DB_USER")
    password = os.environ.get("DB_PASSWORD")
    if not all([host, port, user, password]):
        return None
    return {"host": host, "port": int(port), "user": user, "password": password}


# 安全校验
def check_sql_safety(sql):
    # 去前导空白并转大写（SELECT / select 都能识别）
    sql_head = sql.lstrip().upper()
    if not (sql_head.startswith("SELECT") or sql_head.startswith("WITH")):
        raise AssertionError(f"SQL安全校验失败（只允许 SELECT / WITH 开头）: {sql[:100]}")
    if ";" in sql:
        raise AssertionError(f"SQL安全校验失败（SQL内禁止分号）: {sql[:100]}")


# 执行 SQL 并包装结果 {"rows": [...], "row_count": N}
def execute_sql(sql, database):
    # 数据库连接配置
    conn_config = get_conn_config()
    if not conn_config:
        return None

    # 安全校验
    check_sql_safety(sql)

    # 建数据库连接：库名=测试项配置的 sql_database；utf8mb4 防中文乱码；
    # 超时控制防慢 SQL 卡死用例；DictCursor 让每行结果是 {列名: 值} 字典
    conn = pymysql.connect(
        database=database,
        charset="utf8mb4",
        connect_timeout=10,   # 建连接超时（秒）
        read_timeout=30,      # 读结果超时（秒）
        write_timeout=30,     # 写超时（秒）
        cursorclass=pymysql.cursors.DictCursor,
        **conn_config,        # 展开 host/port/user/password 四要素
    )
    try:
        with conn.cursor() as cursor:  # with 结束自动关闭游标
            cursor.execute(sql)        # 执行查询
            rows = cursor.fetchall()   # 取回全部结果行
    finally:
        conn.close()  # 无论成功失败都关连接，防止连接泄漏

    log.debug(f"SQL执行成功: {sql[:100]}... 共 {len(rows)} 行")
    # 统一包装成固定形态，供断言按 /rows/... 或 /row_count 取值
    return {"rows": rows, "row_count": len(rows)}


# ===== SQL 查询入口 =====
def run_sql_assertion(expr, sql_database, variables):
    # 拆出 SQL 语句和断言表达式
    sql, assert_expr = parse_sql_assertion(expr)

    # 测试项未配库名 -> 跳过
    if not sql_database:
        log.info(f"SQL断言跳过（测试项未配置SQL库名）: {sql[:100]}")
        return None

    # 环境未配连接四要素 -> 跳过
    if not get_conn_config():
        log.info(f"SQL断言跳过（当前环境未配置SQL连接）: {sql[:100]}")
        return None

    # 替换 ${var} 为变量池的值（来自 set: 提取）
    sql = replace_vars(sql, variables)
    try:
        # 连库执行查询
        result = execute_sql(sql, sql_database)  
    except AssertionError:
        raise
    except Exception as e:
        log.error(f"SQL执行失败: {e}")
        raise AssertionError(f"SQL执行失败: {e}")
    return assert_expr, result


# 解析断言表达式部分:
# 常规三方校验 "=/data/answer='c'" -> =, /data/answer, 'c'
# 带前导操作符 "=/rows/0/status=1" / ">=/row_count>=2" -> 前导操作符为比较操作符
# 省略预期值 "=/questions/0/solution" -> 预期返回 None，语义为查库值与入参值直接比对
def parse_sql_assert_expr(assert_expr):
    expr = assert_expr.strip()  # 去首尾空白
    # 拆断言表达式开头的那个操作符
    match = re.compile(r'^(==|!=|>=|<=|=|>|<)\s*(/.*)$', re.S).match(expr)
    if match:
        op = match.group(1)
        rest = match.group(2).strip()
        # 在剩余部分里找第一个操作符，切出「路径」和「预期值」
        for o in ('==', '!=', '>=', '<=', '=', '>', '<'):
            if o in rest:
                path, expected = rest.split(o, 1)
                # 返回路径、操作符、预期值
                return path.strip(), op, expected.strip()
        # 没有预期值，则置 None
        return rest, op, None
    raise AssertionError(f"SQL断言格式错误（未找到运算符）: {assert_expr}")


# 归一化比较：数据库常以字符串存 JSON（如 {"ids":["D"]}），入参是结构化对象
# 双方先直接比较；任一侧能解析成 JSON 的一律按解析后的结构深度比较
def smart_equal(actual, expected):
    # 第一步：直接比较，相等最快（无需任何解析）
    if actual == expected:
        return True

    # 把任意值「尽量」转成 JSON 结构：dict/list 本来就是结构，原样返回；
    # 字符串尝试 json.loads 解析；解析失败或其他类型（数字等）返回 None 表示转不成
    def _as_json(v):
        if isinstance(v, (dict, list)):
            return v
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, ValueError):
                return None
        return None

    # 第二步：两侧分别归一化，都成功转成结构才按结构深度比较（空格/键序差异被消除）
    a = _as_json(actual)
    e = _as_json(expected)
    if a is not None and e is not None:
        return a == e
    # 第三步：直比不等、又无法都转成 JSON 结构 -> 判定不相等
    return False


# 落库校验形式：从查询结果取比较值，字段名 = 入参路径最后一段
# 字段不存在时：仅一列则取唯一列，多列则报错（可用 as 别名与入参字段对齐）
def extract_db_value(result, req_path):
    rows = result['rows']  # 查询结果的所有行（DictCursor 返回的 [{列:值}, ...]）
    # 一行都没有 = WHERE 条件没匹配到数据，没有可比的值，直接报错
    if not rows:
        raise AssertionError(f"SQL查询结果为空，无法比较字段: {req_path}")
    column = req_path.strip('/').split('/')[-1]  # 取入参路径最后一段当列名，如 /data/solution -> solution
    row0 = rows[0]  # 只取第一行比较（断言只关心第一条记录）
    if column in row0:  # 查询结果里有同名列 -> 直接取该列的值
        return row0[column]
    if len(row0) == 1:  # 没有同名列但只查了一列 -> 单列兜底，取这唯一一列
        return next(iter(row0.values()))
    # 多列又没同名列：无法确定该比哪个，报错并提示用 as 别名对齐列名
    raise AssertionError(f"查询结果不存在字段 {column}（可用 as 别名与入参字段对齐，或只查询该列）")

