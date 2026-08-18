import json
import os
from django.utils import timezone
from api_app.models import *
from api_app.api_test.api_jenkins_single_runner import *
from api_app.api_test.api_local_single_runner import *
from api_app.api_test.api_local_custom_runner import *


# 合并多个测试项的用例数据
def build_test_item_cases(test_item_ids, domain, env, headers):
    all_cases = []
    for item_id in test_item_ids:
        test_item = DB_TestItem.objects.get(id=item_id)
        interface = test_item.interface
        base_url = "https://" + interface.url.format(domain, env)
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
                'description': case['description']
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
    type1_ids = [item.id for item in test_items if item.type == 1]
    type2_ids = [item.id for item in test_items if item.type == 2]

    base_url = data.get('base_url', 'http://127.0.0.1:8000')
    results = []

    # --- 先执行单接口用例 (type=1) ---
    if type1_ids:
        domain_id = data.get('domain_id')
        env_id = data.get('env_id')
        token_id = data.get('token_id')
        header_template_id = data.get('header_template_id')

        domain_obj = DB_Domain.objects.filter(id=domain_id, is_del=False).first()
        env_obj = DB_Env.objects.filter(id=env_id, is_del=False).first()
        token_obj = DB_Token.objects.filter(id=token_id, is_del=False).first()
        header_obj = DB_HeaderTemplate.objects.filter(id=header_template_id, is_del=False).first()
        if not domain_obj or not env_obj:
            return {"code": -1, "message": "域名或环境未配置（单接口用例需要）"}, 400

        headers = header_obj.headers.copy() if header_obj else {}
        if token_obj:
            headers['token'] = token_obj.token

        test_run = DB_run_result.objects.create(
            env=env_obj.name,
            status="running",
            description=description,
            test_items=','.join(str(i) for i in type1_ids),
            started_at=timezone.now(),
            trigger_source=run_mode,
        )

        all_cases = build_test_item_cases(type1_ids, domain_obj.domain, env_obj.env, headers)
        test_run.total = len(all_cases)
        cases_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "cases")
        cases_txt_name = f"{test_run.id}_cases.txt"
        cases_txt_path = os.path.join(cases_dir, cases_txt_name)
        with open(cases_txt_path, "w", encoding="utf-8") as f:
            json.dump(all_cases, f, ensure_ascii=False, indent=2)
        test_run.cases_json_file = cases_txt_name

        if run_mode == 'jenkins':
            zip_bytes = pack_test_bundle(test_run, cases_txt_path)
            try:
                jenkins_url = trigger_jenkins_build(zip_bytes, test_run.id, base_url)
            except Exception as e:
                test_run.status = 'failed'
                test_run.finished_at = timezone.now()
                test_run.save()
                return {"code": -1, "message": str(e)}, 500
            test_run.jenkins_build_url = jenkins_url
            test_run.save()
            results.append({"type": 1, "run_id": test_run.id, "jenkins_build_url": jenkins_url})
        else:
            run_single_local(test_run, cases_txt_path)
            results.append({"type": 1, "run_id": test_run.id})

    # --- 再执行自定义脚本 (type=2) ---
    if type2_ids:
        resp, status = run_custom(type2_ids, description, base_url)
        if status != 200:
            return resp, status
        results.append({"type": 2, "run_id": resp.get("run_id")})

    return {"code": 0, "message": "success", "results": results}, 200
