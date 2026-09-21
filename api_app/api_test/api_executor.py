import json
import os
from django.utils import timezone
from api_app.models import *
from api_app.api_test.api_jenkins_single_runner import *
from api_app.api_test.api_local_single_runner import *
from api_app.api_test.api_local_custom_runner import *
from api_app.api_test.api_jenkins_custom_runner import *
from api_app.api_test.token_fetcher import fetch_tokens


# 合并多个测试项的用例数据（请求头按测试项各自配置的角色/系统组装）
def build_test_item_cases(test_item_ids, domain, env, token_map, template_map, role_user_map):
    all_cases = []
    for item_id in test_item_ids:
        test_item = DB_TestItem.objects.get(id=item_id)
        interface = test_item.interface
        base_url = "https://" + interface.url.format(domain, env)
        # 该测试项的请求头 = 系统对应模板 + 角色解析出的用户名（当前环境）对应系统的 token
        username = role_user_map.get(test_item.role)
        headers = (template_map.get(test_item.system) or {}).copy()
        token = token_map.get(username, {}).get(test_item.system, '')
        headers['token'] = token
        # serverId 动态：从 token 末段提取（如 'xxx:1201v' -> '1201'，长度不固定，可能1001/1201/10/1）
        # 同步替换模板里的 serverid/serverId 字段（oss 模板小写、app 模板大写，大小写跟随模板）；token 为空则置空
        server_id = token.split(':')[-1].rstrip('v') if token else ''
        for key in [k for k in headers if k.lower() == 'serverid']:
            headers[key] = server_id
        for case in test_item.cases:
            all_cases.append({
                'url': base_url,
                'method': interface.method.upper(),
                'headers': headers,
                'CaseID': case['CaseID'],
                'case_name': case['case_name'],
                'is_active': case['is_active'],
                'body': case['body'],
                'expected_status_code': case['expected_status_code'],
                'assertions': case['assertions'],
                'description': case['description'],
                'sql_database': test_item.sql_database,  # SQL 断言查询库名
            })
    return all_cases


# 数据处理和执行调度
def dispatch_run(data):
    # 获取参数校验
    test_item_ids = data.get('test_item_ids', [])
    description = data.get('description', '')
    run_mode = data.get('run_mode', 'local')

    if not test_item_ids:
        return {"code": -1, "message": "未选择测试项"}, 400

    # 校验测试项是否存在
    test_items = list(DB_TestItem.objects.filter(id__in=test_item_ids, is_del=False))
    if len(test_items) != len(test_item_ids):
        return {"code": -1, "message": "部分测试项不存在或已删除"}, 400

    # 按类型拆分
    type1_items = [item for item in test_items if item.type == 1]
    type1_ids = [item.id for item in type1_items]
    type2_ids = [item.id for item in test_items if item.type == 2]

    base_url = data.get('base_url', 'http://172.16.2.60:8000')
    results = []

    env_id = data.get('env_id')
    env_obj = DB_Env.objects.filter(id=env_id, is_del=False).first()
    env_name = env_obj.name if env_obj else ''

    # ===== 执行准备：批量获取 token =====
    # 统一取当前环境全部角色的账号映射（环境维度全量，与测试项配置无关）
    role_user_map = {a.role: a.username for a in DB_TestAccount.objects.filter(env_id=env_id, is_del=False)}
    token_map, template_map = {}, {}

    # 获取域名（取 token / 拼接用例 URL 均依赖）
    domain_id = data.get('domain_id')
    domain_obj = DB_Domain.objects.filter(id=domain_id, is_del=False).first()

    if role_user_map:
        # 当前环境全部角色的用户名（去重）
        usernames = sorted(set(role_user_map.values()))

        # 请求头模板：system -> headers
        template_map = {tpl.system: tpl.headers for tpl in DB_HeaderTemplate.objects.filter(is_del=False) if tpl.system}

        # 批量获取所有账号的 token（一轮执行内复用；失败降级空串不拦截）
        token_map = fetch_tokens(domain_obj.domain, env_obj.env, domain_obj.app_server, usernames)

    # 先执行单接口用例
    if type1_ids:
        # 按 DB_Domain.domain 查 SQL 连接配置（如 devapi1.lingshi.com，未配置 = 忽略所有 sql: 断言）
        sql_conn = None
        sql_env = DB_SqlEnv.objects.filter(env_name=domain_obj.domain, is_del=False).first()
        if sql_env:
            sql_conn = {
                'DB_HOST': sql_env.host,
                'DB_PORT': str(sql_env.port),
                'DB_USER': sql_env.user,
                'DB_PASSWORD': sql_env.password,
            }

        test_run = DB_run_result.objects.create(
            env=env_name,
            status="running",
            description=description,
            test_items=','.join(str(i) for i in type1_ids),
            started_at=timezone.now(),
            trigger_source=run_mode,
        )

        all_cases = build_test_item_cases(type1_ids, domain_obj.domain, env_obj.env, token_map, template_map, role_user_map)
        test_run.total = len(all_cases)

        # 执行前置信息（写入本次执行 log 开头，在 pytest 输出之前）
        header_lines = [
            "\n==================== 执行前置信息 ====================\n",
            f"执行时间: {timezone.localtime().strftime('%Y-%m-%d %H:%M:%S')}\n",
            f"环境: {env_name} (env_id={env_id}) | 域名: {domain_obj.domain} | App登录域名: {domain_obj.app_server}\n",
            f"测试项({len(type1_items)}):\n",
        ]
        for it in type1_items:
            header_lines.append(f"  [{it.id}] {it.name} | 角色: {it.role or '-'} | 测试端: {it.system or '-'}\n")
        header_lines.append(f"角色映射(环境 {env_name}，共{len(role_user_map)}条):\n")
        for role, user in role_user_map.items():
            header_lines.append(f"  {role} -> {user}\n")
        header_lines.append("token 获取结果:\n")
        for user, tokens in token_map.items():
            header_lines.append(f"  {user}: oss={tokens.get('oss') or '(失败/空)'} | app={tokens.get('app') or '(失败/空)'}\n")
        header_lines.append("======================================================\n\n")
        run_header_text = "".join(header_lines)
        cases_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "cases")
        cases_txt_name = f"{test_run.id}_cases.txt"
        cases_txt_path = os.path.join(cases_dir, cases_txt_name)
        with open(cases_txt_path, "w", encoding="utf-8") as f:
            json.dump(all_cases, f, ensure_ascii=False, indent=2)
        test_run.cases_json_file = cases_txt_name

        # 执行用例
        if run_mode == 'jenkins':
            zip_bytes = pack_test_bundle(test_run, cases_txt_path, run_header_text)
            try:
                jenkins_url = trigger_jenkins_build(zip_bytes, test_run.id, base_url, sql_conn)
            except Exception as e:
                test_run.status = 'failed'
                test_run.finished_at = timezone.now()
                test_run.save()
                return {"code": -1, "message": str(e)}, 500
            test_run.jenkins_build_url = jenkins_url
            test_run.save()
            results.append({"type": 1, "run_id": test_run.id, "jenkins_build_url": jenkins_url})
        else:
            run_single_local(test_run, cases_txt_path, sql_conn, run_header_text)
            results.append({"type": 1, "run_id": test_run.id})

    # 执行多接口脚本
    if type2_ids:
        if run_mode == 'jenkins':
            resp, status = run_custom_jenkins(type2_ids, description, base_url, env=env_name)
        else:
            resp, status = run_custom(type2_ids, description, base_url, env=env_name)
        if status != 200:
            return resp, status
        results.append({
            "type": 2,
            "run_id": resp.get("run_id"),
            "jenkins_build_url": resp.get("jenkins_build_url", ""),
        })

    return {"code": 0, "message": "success", "results": results}, 200
