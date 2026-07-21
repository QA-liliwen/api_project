import pytest
import requests


# 执行层
def run_request(url, method, headers, body=None):
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
        pytest.skip(f"用例 {case['CaseID']} 未启用")
    resp = run_request(url=case['url'], method=case['method'], headers=case['headers'], body=case.get('body', ''))
    print(f"\n[{case['CaseID']}] 响应体: {resp.text[:1000]}")
    assert resp.status_code == case['expected_status_code'], f"状态码: 实际={resp.status_code}, 期望={case['expected_status_code']}"
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
        assert data == expected, f"断言失败: {path} 实际={data}, 期望={expected}"


if __name__ == '__main__':
    pass
