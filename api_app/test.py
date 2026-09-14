import requests

def get_temp_password(env, inst_id, expire_seconds=7200):
    """
    获取临时登录密码
    :param env: 环境域名，可选值：
        - 'stage2.51tyty.com'  VS2 环境
        - 'pre.51tyty.com'     XS 环境
        - 'rz.51tyty.com'      PROD 环境
    :param inst_id: 机构ID（主校ID），如 1001
    :param expire_seconds: 有效时长(秒)，默认7200(2小时)，上限7200
    :return: 临时密码字符串，失败返回错误信息
    """
    url = f'http://{env}/center/services/rest/user/dynamic/{inst_id}'
    params = {'expireSeconds': min(expire_seconds, 7200)}
    headers = {
        'DeviceType': '0',
        'AppType': '6',
        'DeviceUniqueId': '3573aed2-ede6-4d93-9dcd-27fc5fd6c3ab',
    }

    resp = requests.get(url, params=params, headers=headers, timeout=10)
    data = resp.json()
    if data.get('code') in ('0', 0):
        return data['password']
    return f"失败: {data.get('message', '未知错误')}"


# 用法
pwd = get_temp_password('stage2.51tyty.com', 1001)
print(pwd)
