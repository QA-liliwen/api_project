import base64

import requests
import urllib3

from api_app.api_tools.base import ToolError, register_tool, get_str_param, get_choice_param

urllib3.disable_warnings()

# dim 系统 admin 账号的加密密码（RSA，固定值，三个环境通用）
_DIM_ADMIN_PASSWORD = "mooDo0TDAVq418YpRxi7XMe4dBGfGAxk6xorN8FxNOvXBL6bZ9jMvgMj+m4xWX8S7ecPukNWOYPyvmxT+3kzgDSjKIz2eFPvQzTLIp1/HMk1NEWYx8kHE8ftZAGv0H3fLIvSWUfzy6cHkO28uW4I/EnfQbHUEpQbd5ag8bqj6qcEckNK4jn/KrU8rsBPU54WU0PCOHXw84uiTlDZNHbAmGSQg11rSrYkV1vM96AKB3nVbxWiUJ1SVUlC106tM+NPJccyZMkbJaZ1LVSFLiOJfGOaGsHLNGgRXJHNf8yXbaWb8R5kMLZ12jm6dinHWAbuQcMxmA1KH3+BOsQvipD/SQ=="


# 登录 dim 系统拿 accessToken，用于后续接口的 Bearer 鉴权（替代硬编码 token，不再有过期问题）
def get_dim_token(dim_base):
    url = f'{dim_base}/crmsys/login/password'
    try:
        resp = requests.post(
            url,
            json={"username": "admin", "password": _DIM_ADMIN_PASSWORD},
            headers={'content-type': 'application/json;charset=UTF-8'},
            verify=False,
            timeout=10,
        )
        data = resp.json()
    except requests.RequestException as e:
        raise ToolError(f"请求 dim 登录接口失败: {e}")
    except ValueError:
        raise ToolError("dim 登录接口返回的不是合法 JSON")

    if data.get('code') not in ('0', 0):
        raise ToolError(f"dim 登录失败: {data.get('message', '未知错误')}")

    token = (data.get('data') or {}).get('accessToken', '')
    if not token:
        raise ToolError("dim 登录返回中缺少 accessToken")
    return token

# 环境配置：三个系统地址均按环境切换
# dim/oss 走 API 网关（规律：{网关}/dim|school/{环境段}），app 登录直接用环境域名
# 注：用户提供的 ossm/school 域名是 Web 控制台地址，API 实际走下列网关（从前端配置表挖出）
ENV_CONFIG = {
    'test': {
        'dim_base': 'https://devapi1.lingshi.com/dim/vs2',
        'oss_base': 'https://devapi1.lingshi.com/school/vs2',
        'app_server': 'stage2.51tyty.com',
    },
    'pre': {
        'dim_base': 'https://preapi1.lingshi.com/dim/xs',
        'oss_base': 'https://preapi1.lingshi.com/school/xs',
        'app_server': 'pre.51tyty.com',
    },
    'prod': {
        'dim_base': 'https://api1.lingshi.com/dim/ws',
        'oss_base': 'https://api1.lingshi.com/school/ws',
        'app_server': 'cs.51tyty.com',
    },
}


# 登录参数编码：L + base64(用户名:密码) + S，L/S 为固定标识符
# 实测 'adminvswrr:bclw45' -> 'LYWRtaW52c3dycjpiY2x3NDU=S'，不是真加密，只是 Base64 混淆
def encode_login_param(username, password):
    raw = f'{username}:{password}'.encode('utf-8')
    return 'L' + base64.b64encode(raw).decode('utf-8') + 'S'


# 到 dim 系统申请临时密码，返回 recordList 中「生效中」的密码
def apply_dim_password(code, dim_base, token):
    url = f'{dim_base}/crmsys/login/dynamic/apply'
    try:
        resp = requests.post(
            url,
            json={"data": {"code": code}},
            headers={
                'authorization': f'Bearer {token}',
                'content-type': 'application/json;charset=UTF-8',
            },
            verify=False,
            timeout=10,
        )
        data = resp.json()
    except requests.RequestException as e:
        raise ToolError(f"请求 dim 系统失败: {e}")
    except ValueError:
        raise ToolError("dim 系统返回的不是合法 JSON")

    if data.get('code') not in ('0', 0):
        raise ToolError(f"dim 系统返回失败: {data.get('message', '未知错误')}")

    # 密码列表按时间倒序，取第一条生效中的
    record_list = (data.get('data') or {}).get('recordList') or []
    for record in record_list:
        if record.get('pwdStatus') == '生效中':
            password = record.get('password', '')
            if password:
                return password

    raise ToolError("recordList 中没有生效中的密码")


# 到 oss 系统 doLogin，返回 data.userInfo 节点
# 登录参数：method=account，密码用 encode_login_param 编码后传入
def oss_dologin(username, password, oss_base):
    url = f'{oss_base}/schsys/login/doLogin'
    try:
        resp = requests.post(
            url,
            json={
                "method": "account",
                "userName": username,
                "password": encode_login_param(username, password),
                "server": None,
            },
            headers={
                'apptype': '10',
                'content-type': 'application/json;charset=UTF-8',
                'devicetype': '5',
                'deviceuniqueid': 'd91ed0b9-290c-4700-ad1e-1d619d625e54',
                'lan': 'ch',
                'language': 'ch',
                'timezone': 'GMT+0800',
            },
            verify=False,
            timeout=10,
        )
        data = resp.json()
    except requests.RequestException as e:
        raise ToolError(f"请求 oss 系统失败: {e}")
    except ValueError:
        raise ToolError("oss 系统返回的不是合法 JSON")

    if data.get('code') not in ('0', 0):
        raise ToolError(f"oss 登录失败: {data.get('message', '未知错误')}")

    user_info = (data.get('data') or {}).get('userInfo') or {}
    if not user_info.get('token'):
        raise ToolError("oss 登录返回中缺少 token")
    return user_info


# app V2 登录，返回含 token 的完整响应
# 与 oss 同样的 L...S 编码 key，请求头固定模拟 Android 客户端，PUT 提交
def app_login(username, password, app_server):
    headers = {
        'user-agent': 'Android/5.6.35.238481 (Android; 9; Asus-user 9.0.0 20171130.276299 release-keys)',
        'appversion': '5.6.35.238481',
        'devicecategory': 'MOBILE',
        'channel': 'tmxxsj',
        'smartedukey': 'dd3e1b1da431088c',
        'apptype': '17',
        'content-type': 'application/json',
        'umid': 'b1813a52eea4ec78a1bc3a6e6cea34de',
        'lan': 'ch',
        'timezone': 'GMT+08',
        'devicetype': '0',
        'hostappinstid': '3713',
        'appscope': 'LearningMode',
        'host': app_server,
        'serverid': '0',
        'fromappname': 'Android',
        'deviceuniqueid': '643fae1a-cefb-41bd-a428-33185eb0cfdf_com.lingshi.flutter.app',
        'requestuniqueid': f'{username}__0_106',
    }
    payload = {
        'LoginUserArgu': {
            'industryType': 'All',
            'key': encode_login_param(username, password),
            'server': app_server,
        }
    }
    try:
        resp = requests.put(
            f'https://{app_server}/center/services/rest/user/V2/Login?serino=110',
            json=payload,
            headers=headers,
            verify=False,
            timeout=15,
        )
        data = resp.json()
    except requests.RequestException as e:
        raise ToolError(f"请求 app 登录接口失败: {e}")
    except ValueError:
        raise ToolError("app 登录接口返回的不是合法 JSON")

    if data.get('code') not in ('0', 0):
        raise ToolError(f"app 登录失败: {data.get('message', '未知错误')}")

    token = data.get('token', '')
    if not token:
        raise ToolError("app 登录返回中缺少 token")
    return data


# ==================== 输入用户名（code），串联多个系统返回用户信息合集 ====================
@register_tool('user_info')
def run(params):
    username = get_str_param(params, 'username').strip()
    env = get_choice_param(params, 'env', tuple(ENV_CONFIG), default='test')
    config = ENV_CONFIG[env]

    infos = []

    # 第零步：dim 登录拿 accessToken（三个环境通用，统一从测试环境拿）
    dim_token = get_dim_token('https://devapi1.lingshi.com/dim/vs2')

    # 第一步：dim 系统拿 OSS 临时密码（后续接口依赖它，失败则整体失败）
    password = apply_dim_password(username, config['dim_base'], dim_token)
    infos.append({"label": "OSS 临时密码", "value": password})

    # 第二步：oss doLogin 拿用户信息与 token
    user_info = oss_dologin(username, password, config['oss_base'])
    oss_fields = ('userName', 'instId', 'instCode', 'token', 'serverId', 'userId')
    for field in oss_fields:
        infos.append({"label": f"OSS {field}", "value": str(user_info.get(field, ''))})

    # 第三步：app V2 登录拿 app token（key 同样是 L...S 编码）
    app_data = app_login(username, password, config['app_server'])
    infos.append({"label": "APP token", "value": app_data.get('token', '')})

    return {"infos": infos}
