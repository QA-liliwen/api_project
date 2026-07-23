import pytest
import requests

from api_app.api_test.log_config import get_logger

log = get_logger(__name__)

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

# 断言层
def run_and_assert(case):
    if case.get('is_active') != 'Y':
        log.debug(f"用例 {case['CaseID']} 未启用")
        pytest.skip(f"用例 {case['CaseID']} 未启用")
    resp = run_request(url=case['url'], method=case['method'], headers=case['headers'], body=case.get('body', ''))
    log.info(f"状态码断言: 实际={resp.status_code}, 期望={case['expected_status_code']}")
    assert resp.status_code == case['expected_status_code'], f"状态码: 实际={resp.status_code}, 期望={case['expected_status_code']}"
    log.info(f"数据断言: {case['assertions']}")
    log.info(f"响应体: {resp.text[:1000]}")
    resp_json = resp.json()
    for assertion_str in case['assertions']:
        path, expected = assertion_str.rsplit('=', 1)
        data = resp_json
        keys = [k for k in path.strip('/').split('/') if k]
        for key in keys:
            if isinstance(data, list):
                key = int(key)
            data = data[key]

        expected_lower = expected.lower()
        if expected_lower == "true":
            expected = True
        elif expected_lower == "false":
            expected = False
        else:
            try:
                expected = int(expected)
            except ValueError:
                pass
        log.debug(f"断言: {path} 实际={data}, 期望={expected}")
        try:
            assert data == expected
        except AssertionError:
            log.error(f"断言失败: {path} 实际={data}, 期望={expected}")
            raise


if __name__ == '__main__':
    pass
