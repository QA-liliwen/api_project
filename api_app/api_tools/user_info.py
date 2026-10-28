import base64
import json
import os
import time
from datetime import datetime

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


# ==================== 备用 token 来源（Charles Mirror + 平台本地缓存） ====================
# Mirror 落盘目录：Charles Tools → Mirror 开启（Only for selected locations，
# Path=*/auth/account/switch/*），App 切托管校区的 switch 响应体自动落盘为 JSON
TRUSTEE_MIRROR_DIR = r'D:\code\token_list'
# 平台每次成功拿到托管 token 后的本地缓存（兜底时与 Charles 取时间较近者）
PLATFORM_TOKEN_CACHE = os.path.join(TRUSTEE_MIRROR_DIR, '_platform_cache.json')


# 平台成功拿到托管 token 后落盘缓存（写失败静默，不影响主流程）
def save_platform_token(tgt_iid, tgt_uid, token):
    try:
        cache = {}
        if os.path.exists(PLATFORM_TOKEN_CACHE):
            try:
                with open(PLATFORM_TOKEN_CACHE, 'r', encoding='utf-8') as f:
                    cache = json.load(f)
            except (OSError, ValueError):
                cache = {}
        if not isinstance(cache, dict):
            cache = {}
        cache[f'{tgt_iid}:{tgt_uid}'] = {
            'token': token,
            'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'mtime': time.time(),
        }
        with open(PLATFORM_TOKEN_CACHE, 'w', encoding='utf-8') as f:
            json.dump(cache, f, ensure_ascii=False)
    except OSError:
        pass


# 从 Charles Mirror 落盘读指定托管身份「最后一次」switch 响应的 token
# 返回 (token, 获取时间, mtime)；目录不存在 / 无匹配 / 解析失败一律静默返回 (None, None, None)
def read_mirror_trustee_token(tgt_iid, tgt_uid):
    if not os.path.isdir(TRUSTEE_MIRROR_DIR):
        return None, None, None
    best = None  # (mtime, token, 时间字符串)
    cache_name = os.path.basename(PLATFORM_TOKEN_CACHE)
    for root, _dirs, files in os.walk(TRUSTEE_MIRROR_DIR):
        for fname in files:
            # 平台缓存文件不是 Mirror 响应体，跳过；其余按 URL 路径落盘、无扩展名，全部尝试解析
            if fname == cache_name:
                continue
            fpath = os.path.join(root, fname)
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except (OSError, ValueError):
                continue
            if str(data.get('code')) != '0':
                continue
            user = data.get('user') or {}
            if str(user.get('instId') or '') != str(tgt_iid) or str(user.get('userId') or '') != str(tgt_uid):
                continue
            token = data.get('token') or ''
            if not token:
                continue
            try:
                mtime = os.path.getmtime(fpath)
            except OSError:
                continue
            if best is None or mtime > best[0]:
                ts = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
                best = (mtime, token, ts)
    if best:
        return best[1], best[2], best[0]
    return None, None, None


# 兜底汇总：本地平台缓存 与 Charles Mirror，哪个时间近取哪个
# 返回 (token, 来源, 获取时间)；都取不到返回 (None, None, None)
def read_trustee_token_fallback(tgt_iid, tgt_uid):
    candidates = []
    # 本地平台缓存
    try:
        if os.path.exists(PLATFORM_TOKEN_CACHE):
            with open(PLATFORM_TOKEN_CACHE, 'r', encoding='utf-8') as f:
                cache = json.load(f)
            rec = (cache or {}).get(f'{tgt_iid}:{tgt_uid}') or {}
            if rec.get('token'):
                candidates.append((float(rec.get('mtime') or 0), rec['token'], '平台缓存', rec.get('time') or ''))
    except (OSError, ValueError):
        pass
    # Charles Mirror
    tok, ts, mtime = read_mirror_trustee_token(tgt_iid, tgt_uid)
    if tok:
        candidates.append((mtime, tok, 'Charles', ts))
    if not candidates:
        return None, None, None
    _mtime, token, src, t = max(candidates, key=lambda x: x[0])
    return token, src, t


# ==================== 托管 Token 获取链路（完整说明） ====================
# 目标：托管身份（courses 里 courseType=after_school_care 的校区节点）的 token，用于服务端只认托管身份的接口
#
# 1. 快路径（登录沾光）：app 登录返回「服务端记住的当前校区」的 token（前缀 = 该身份 userId）。
#    服务端记住托管校区时，登录 token 就是托管 token，直接用
# 2. 慢路径（switch 跨身份切换，主校区状态时）：
#    ① password_login（auth/password/login，App 原生密码登录）拿主 token
#    ② switch_to_trustee：header token=主 token，instid/serverid/RU 一律声明「当前身份」，
#      URL 路径参数指向「目标身份」→ 响应体返回目标身份的托管 token（2026-10-14 抓包复刻验证）
#    ⚠ 三处身份字段若误传目标身份，服务端判 token 与声明不符 → -1001 登录失效（曾长期踩坑）
# 3. 密码来源：FIXED_PASSWORDS（adminfmf 等）；无固定密码的账号只能靠快路径或人工在 App 切换
# ========================================================================


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


# 已知固定密码（按环境维护；未收录的账号直接走临时密码流程）
# 登录策略：先用固定密码，失败再回落临时密码；oss 与移动端分开判断，互不影响
FIXED_PASSWORDS = {
    'test': {
        'adminexam': '888888',
        'adminqa9515': '405824',
        'adminqwqwqw': '111111',
        'admincontent': '111111',
        'adminvswrr': 'Ct77a42z',
        'adminfmf': 'Qhwmtevf',
    },
    'pre': {
        'adminexam': 'lingshi0616',
        'admincontent': 'Lskj0987654321',
        'adminvswrr': '123456',
    },
    'prod': {
        'admincontent': 'LingShi_9896',
    },
}


# 登录参数编码：L + base64(用户名:密码) + S，L/S 为固定标识符
# 实测 'adminvswrr:bclw45' -> 'LYWRtaW52c3dycjpiY2x3NDU=S'，不是真加密，只是 Base64 混淆
def encode_login_param(username, password):
    raw = f'{username}:{password}'.encode('utf-8')
    return 'L' + base64.b64encode(raw).decode('utf-8') + 'S'


# App 原生密码登录（抓包 #11 复刻）：签发的 token 可跨身份调 switch（V2/Login 的 token 未经此验证）
# 失败抛 ToolError（含 -13002 密码错误风控文案，勿连续重试）
def password_login(username, password, app_server):
    ts = int(time.time() * 1000)
    headers = {
        'appversion': '5.6.35.238481',
        'devicecategory': 'MOBILE',
        'channel': 'tmxxsj',
        'smartedukey': 'dd3e1b1da431088c',
        'apptype': '17',
        'content-type': 'application/json',
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
    try:
        resp = requests.put(
            f'https://{app_server}/center/services/rest/auth/password/login?serino=319',
            json={'PasswordLoginArgu': {'loginKey': encode_login_param(username, password)}},
            headers=headers,
            verify=False,
            timeout=15,
        )
        data = resp.json()
    except requests.RequestException as e:
        raise ToolError(f'请求异常: {e}')
    if str(data.get('code')) != '0' or not data.get('token'):
        raise ToolError(f"{data.get('message', '未知错误')}")
    return data


# switch 跨身份切换（抓包 #16 复刻）：header/RU 声明「当前身份」，URL 参数指向「目标身份」→ 返回目标身份 token
# ⚠ instid/serverid/RU 必须是当前身份；误传目标身份 → -1001 登录失效
def switch_to_trustee(cur_token, cur_inst_id, cur_server_id, cur_user_id,
                      app_server, username, tgt_inst_id, tgt_user_id):
    if not all([cur_token, cur_inst_id, cur_server_id, cur_user_id, tgt_inst_id, tgt_user_id]):
        return None
    ts = int(time.time() * 1000)
    headers = {
        'user-agent': 'Android/5.6.35.238481 (Android; 9; Asus-user 9.0.0 20171130.276299 release-keys)',
        'appversion': '5.6.35.238481',
        'devicecategory': 'MOBILE',
        'channel': 'tmxxsj',
        'smartedukey': 'dd3e1b1da431088c',
        'apptype': '17',
        'content-type': 'application/json',
        'instid': str(cur_inst_id),
        'token': cur_token,
        'lan': 'ch',
        'timezone': 'GMT+08',
        'devicetype': '0',
        'hostappinstid': '3713',
        'appscope': 'LearningMode',
        'host': app_server,
        'username': username,
        'fromappname': 'Android',
        'serverid': str(cur_server_id),
        'deviceuniqueid': '643fae1a-cefb-41bd-a428-33185eb0cfdf_com.lingshi.flutter.app',
        'requestuniqueid': f'{cur_user_id}_{cur_inst_id}_{ts}_315',
    }
    try:
        resp = requests.put(
            f'https://{app_server}/center/services/rest/auth/account/switch/{tgt_inst_id}/{tgt_user_id}?serino={ts % 1000000}',
            headers=headers,
            data=b'',
            verify=False,
            timeout=15,
        )
        body = resp.json()
    except Exception:
        return None
    if str(body.get('code')) != '0' or not body.get('token'):
        return None
    return body['token']


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

    # 该账号在当前环境的固定密码（未收录 = None，走临时密码兜底）
    fixed_pw = FIXED_PASSWORDS.get(env, {}).get(username)
    if fixed_pw:
        infos.append({"label": "固定密码", "value": fixed_pw})

    # 临时密码懒申请：固定密码两个系统都通就完全不申请；dim token 同样懒加载
    #（有固定密码的账号全程不碰 dim，dim 挂了也不影响这类账号）；申请失败也只做一次
    temp_state = {'done': False, 'token': None, 'password': None, 'error': None}

    def ensure_temp_pw():
        if not temp_state['done']:
            temp_state['done'] = True
            try:
                if temp_state['token'] is None:
                    temp_state['token'] = get_dim_token('https://devapi1.lingshi.com/dim/vs2')
                temp_state['password'] = apply_dim_password(username, config['dim_base'], temp_state['token'])
                infos.append({"label": "OSS 临时密码", "value": temp_state['password']})
            except ToolError as e:
                temp_state['error'] = str(e)
        return temp_state

    # 单系统登录：先用固定密码，失败回落临时密码；返回登录结果 data（失败返回 None，错误已写入 infos）
    def system_login(login_fn, base, fail_label):
        if fixed_pw:
            try:
                return login_fn(username, fixed_pw, base)
            except ToolError:
                pass  # 固定密码登不上，回落临时密码
        st = ensure_temp_pw()
        if st['error']:
            infos.append({"label": fail_label, "value": f"获取失败: 临时密码申请失败（{st['error']}）", "error": True})
            return None
        try:
            return login_fn(username, st['password'], base)
        except ToolError as e:
            infos.append({"label": fail_label, "value": f"获取失败: {e}", "error": True})
            return None

    # 第一步：oss doLogin 拿用户信息与 token
    user_info = system_login(oss_dologin, config['oss_base'], 'OSS 用户信息')
    if user_info:
        oss_fields = ('userName', 'instId', 'instCode', 'token', 'serverId', 'userId')
        for field in oss_fields:
            infos.append({"label": f"OSS {field}", "value": str(user_info.get(field, ''))})

    # 第二步：app V2 登录拿 app token（key 同样是 L...S 编码，与 oss 独立判断）
    app_data = system_login(app_login, config['app_server'], 'APP token')
    if app_data:
        app_token = app_data.get('token', '')
        infos.append({"label": "APP token", "value": app_token})
        # 托管校区：先看登录沾光（token 前缀 == 托管 userId 直接用）；主校区状态时
        # 走 password_login + switch 跨身份切换（header/RU 声明当前身份，URL 指向目标身份）
        courses = app_data.get('courses') or []
        trustees = [c for c in courses if isinstance(c, dict) and str(c.get('courseType')) == 'after_school_care']
        if trustees:
            inst = trustees[0]
            tgt_uid = str(inst.get('userId') or '')
            tgt_iid = str(inst.get('instId') or '')
            if tgt_uid and app_token.startswith(f'{tgt_uid}:'):
                save_platform_token(tgt_iid, tgt_uid, app_token)
                infos.append({"label": "校务 token", "value": app_token})
            else:
                # 慢路径：password_login + switch 跨身份切换
                #（header/RU 声明当前身份，URL 参数指向目标身份，返回目标身份托管 token）
                # 密码：固定密码优先，未收录回落临时密码（懒申请）
                rec = None
                pw = fixed_pw
                if not pw:
                    st = ensure_temp_pw()
                    pw = st.get('password') if not st.get('error') else None
                if pw and tgt_uid:
                    try:
                        pdata = password_login(username, pw, config['app_server'])
                        u = pdata.get('user') or {}
                        rec = switch_to_trustee(str(pdata.get('token') or ''), str(u.get('instId') or ''),
                                                str(u.get('serverId') or ''), str(u.get('userId') or ''),
                                                config['app_server'], username, tgt_iid, tgt_uid)
                    except ToolError:
                        rec = None
                if rec:
                    save_platform_token(tgt_iid, tgt_uid, rec)
                    infos.append({"label": "校务 token", "value": rec})
                else:
                    # 备用兜底：本地平台缓存 与 Charles Mirror 取时间较近者（非实时）
                    tok, src, ts = read_trustee_token_fallback(tgt_iid, tgt_uid)
                    if tok:
                        save_platform_token(tgt_iid, tgt_uid, tok)
                        infos.append({"label": "校务 token", "value": tok})
                        infos.append({"label": "校务 token 备注", "value": f"{src}备用 token（非实时调用），获取时间 {ts}"})
                    else:
                        infos.append({"label": "校务 token", "value": "未获取到：自动切换失败且无备用 token（平台缓存/Charles），请在 App 切到托管校区后重查", "error": True})

    # 展示顺序固定（未列出的条目排最后，保持原相对顺序）
    display_order = ('OSS userName', '固定密码', 'OSS 临时密码', 'OSS userId', 'OSS instId',
                     'OSS instCode', 'OSS token', 'OSS serverId', 'APP token', '校务 token',
                     '校务 token 备注')
    infos.sort(key=lambda x: display_order.index(x['label']) if x['label'] in display_order else len(display_order))

    return {"infos": infos}
