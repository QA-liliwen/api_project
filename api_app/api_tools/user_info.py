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
    for root, _dirs, files in os.walk(TRUSTEE_MIRROR_DIR):
        for fname in files:
            # 平台自用缓存文件（_ 开头）不是 Mirror 响应体，跳过；
            # 其余按 URL 路径落盘、无扩展名，全部尝试解析
            if fname.startswith('_'):
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
# 目标：托管身份（courses 里的托管校区节点，识别规则见 find_trustee_courses）的 token，用于服务端只认托管身份的接口
#
# 1. 快路径（登录沾光）：app 登录返回「服务端记住的当前校区」的 token（前缀 = 该身份 userId）。
#    服务端记住托管校区时，登录 token 就是托管 token，直接用
# 2. 慢路径（switch 跨身份切换，主校区状态时）：
#    ① password_login（auth/password/login，App 原生密码登录）拿主 token
#    ② switch_to_trustee：header token=主 token，instid/serverid/RU 一律声明「当前身份」，
#      URL 路径参数指向「目标身份」→ 响应体返回目标身份的托管 token（2026-10-14 抓包复刻验证）
#    ⚠ 三处身份字段若误传目标身份，服务端判 token 与声明不符 → -1001 登录失效（曾长期踩坑）
#    ③ 目标 userId 以 list_inst_accounts（auth/{instId}/accounts）为准，逐个尝试；courses 给的 userId 可能切不动
#      （-2022 用户不存在），只作回落（switch_to_trustee_inst 封装）
# 3. 密码来源：FIXED_PASSWORDS（adminfmf 等）；无固定密码的账号只能靠快路径或人工在 App 切换
# ========================================================================


# 环境配置：三个系统地址均按环境切换
# dim/oss 走 API 网关（规律：{网关}/dim|school/{环境段}），app 登录直接用环境域名
# 注：用户提供的 ossm/school 域名是 Web 控制台地址，API 实际走下列网关（从前端配置表挖出）
# dim 登录拿 accessToken 固定走测试环境（三个环境的 dim 申请接口共用这一个 token）
DIM_LOGIN_BASE = 'https://devapi1.lingshi.com/dim/vs2'

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


# 各环境托管集群 serverId（用户定案）：courses 节点 serverId 命中即视为托管校区
TRUSTEE_SERVER_IDS = {
    'test': {'1203', '1206'},
    'pre': {'1004'},
    'prod': {'112'},
}


# 从登录响应 courses 中找托管校区节点：courseType=after_school_care 或 serverId 命中当前环境托管集合
# 两条都命中的排最前（pre 的 1004 同时属于商学院，靠 courseType 区分出真托管），其余保持原顺序
# env: test / pre / prod
def find_trustee_courses(courses, env):
    sids = TRUSTEE_SERVER_IDS.get(env, set())
    scored = []
    for c in courses or []:
        if not isinstance(c, dict):
            continue
        score = (str(c.get('courseType')) == 'after_school_care') + (str(c.get('serverId') or '') in sids)
        if score:
            scored.append((score, c))
    scored.sort(key=lambda x: -x[0])
    return [c for _score, c in scored]


# token 是否已是该托管节点的身份：前缀 = 托管 userId 且尾段 = {托管 serverId}v
# 只看前缀不够：部分账号主校区与托管校区 userId 相同（如 adminvswrr 的 vswrr/vsw1 都是 728355），
# 主校区 token（1201v）会被误判为托管 token；节点无 serverId 时退化为只比前缀
def is_trustee_token(token, inst):
    uid = str(inst.get('userId') or '')
    sid = str(inst.get('serverId') or '')
    if not uid or not token.startswith(f'{uid}:'):
        return False
    return not sid or token.endswith(f':{sid}v')


# 已知固定密码（按环境维护；未收录的账号直接走临时密码流程）
# 登录策略：先用固定密码，失败再回落临时密码；oss 与移动端分开判断，互不影响
FIXED_PASSWORDS = {
    'test': {
        # 'adminexam': '888888',
        'adminqa9515': '405824',
        'adminqwqwqw': '111111',
        'admincontent': '111111',
        'adminvswrr': '111111',
        # 'adminlsllw': 'Aa888888',
        'adminfmf': 'Aa123456',
    },
    'pre': {
        'adminexam': 'lingshi0616',
        'admincontent': 'Lskj0987654321',
        'adminxswrr': 'Lsls0315',
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


# App 端固定模拟 Android 客户端的公共请求头（登录 / 已登录态请求共用；host 与身份字段由各请求补齐）
_APP_USER_AGENT = 'Android/5.6.35.238481 (Android; 9; Asus-user 9.0.0 20171130.276299 release-keys)'
_APP_COMMON_HEADERS = {
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
    'fromappname': 'Android',
    'deviceuniqueid': '643fae1a-cefb-41bd-a428-33185eb0cfdf_com.lingshi.flutter.app',
}


# App 原生密码登录（抓包 #11 复刻）：签发的 token 可跨身份调 switch（V2/Login 的 token 未经此验证）
# 失败抛 ToolError（含 -13002 密码错误风控文案，勿连续重试）
def password_login(username, password, app_server):
    headers = {
        **_APP_COMMON_HEADERS,
        'host': app_server,
        'serverid': '0',
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
    except ValueError:
        raise ToolError('密码登录接口返回的不是合法 JSON')
    if str(data.get('code')) != '0' or not data.get('token'):
        raise ToolError(f"{data.get('message', '未知错误')}")
    return data


# 已登录态 App 请求头：instid/serverid/RU 一律声明「当前身份」（switch / accounts 共用）
def _session_headers(cur_token, cur_inst_id, cur_server_id, cur_user_id, app_server, username):
    ts = int(time.time() * 1000)
    return {
        'user-agent': _APP_USER_AGENT,
        **_APP_COMMON_HEADERS,
        'instid': str(cur_inst_id),
        'token': cur_token,
        'host': app_server,
        'username': username,
        'serverid': str(cur_server_id),
        'requestuniqueid': f'{cur_user_id}_{cur_inst_id}_{ts}_315',
    }


# switch 跨身份切换（抓包 #16 复刻）：header/RU 声明「当前身份」，URL 参数指向「目标身份」→ 返回目标身份 token
# ⚠ instid/serverid/RU 必须是当前身份；误传目标身份 → -1001 登录失效
# 返回 (token, 失败原因)：成功时原因为 None；失败原因带服务端 code/message，供上层汇总展示
def switch_to_trustee(cur_token, cur_inst_id, cur_server_id, cur_user_id,
                      app_server, username, tgt_inst_id, tgt_user_id):
    if not all([cur_token, cur_inst_id, cur_server_id, cur_user_id, tgt_inst_id, tgt_user_id]):
        return None, '当前/目标身份信息不全'
    try:
        resp = requests.put(
            f'https://{app_server}/center/services/rest/auth/account/switch/{tgt_inst_id}/{tgt_user_id}'
            f'?serino={int(time.time() * 1000) % 1000000}',
            headers=_session_headers(cur_token, cur_inst_id, cur_server_id, cur_user_id, app_server, username),
            data=b'',
            verify=False,
            timeout=15,
        )
        body = resp.json()
    except (requests.RequestException, ValueError) as e:
        return None, f'请求异常 {e}'
    if str(body.get('code')) != '0' or not body.get('token'):
        return None, f"{body.get('code')} {body.get('message') or '响应无 token'}"
    return body['token'], None


# 目标机构下本账号的真实身份列表（App 切换前先调此接口拿 userId，2026-11-04 抓包复刻）
# courses 节点的 userId 不一定可切：同一账号在一个机构下可能有多个身份，
# 如 adminvswrr 在 vsw1 下有 728355 / 30956，courses 只给 728355（switch 返回 -2022 用户不存在），30956 才能切
# 返回 (身份列表, 失败原因)：失败时列表为 []（注意 V2/Login 的 token 调此接口恒返回空列表，须用 password_login 的 token）
def list_inst_accounts(cur_token, cur_inst_id, cur_server_id, cur_user_id, app_server, username, tgt_inst_id):
    if not all([cur_token, cur_inst_id, cur_server_id, cur_user_id, tgt_inst_id]):
        return [], '当前身份信息不全'
    try:
        resp = requests.get(
            f'https://{app_server}/center/services/rest/auth/{tgt_inst_id}/accounts'
            f'?serino={int(time.time() * 1000) % 1000000}',
            headers=_session_headers(cur_token, cur_inst_id, cur_server_id, cur_user_id, app_server, username),
            verify=False,
            timeout=15,
        )
        body = resp.json()
    except (requests.RequestException, ValueError) as e:
        return [], f'accounts 请求异常 {e}'
    if str(body.get('code')) != '0':
        return [], f"accounts 返回 {body.get('code')} {body.get('message') or ''}".rstrip()
    return [a for a in body.get('accounts') or [] if isinstance(a, dict) and a.get('userId')], None


# 切到目标托管机构：先查机构下真实身份逐个 switch，首个成功即返回；查不到时回落 courses 给的 userId
# pdata: password_login 响应（提供当前身份）
# 返回 (token, 失败原因)：成功时原因为 None；失败时汇总 accounts 与每个 userId 的 switch 结果
# （如 -1001 会话失效 / -2022 用户不存在），不再静默吞掉
def switch_to_trustee_inst(pdata, app_server, username, tgt_inst_id, tgt_user_id):
    u = pdata.get('user') or {}
    cur = (str(pdata.get('token') or ''), str(u.get('instId') or ''),
           str(u.get('serverId') or ''), str(u.get('userId') or ''))
    accounts, acc_err = list_inst_accounts(*cur, app_server, username, tgt_inst_id)
    fails = [acc_err] if acc_err else []
    uids = [str(a['userId']) for a in accounts] + [str(tgt_user_id or '')]
    for uid in dict.fromkeys(uids):
        if not uid:
            continue
        token, err = switch_to_trustee(*cur, app_server, username, tgt_inst_id, uid)
        if token:
            return token, None
        fails.append(f'switch {uid}: {err}')
    return None, '；'.join(fails) or '无可切换的目标身份'


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


# ==================== 临时密码本地缓存（规避 dim 申请接口限流） ====================
# dim 的申请接口有频率限制（一天多次查询会报「获取密码过于频繁」），
# 而临时密码在有效期内可反复登录 → 落盘缓存复用，只在过期/失效时才真正申请
TEMP_PW_CACHE = os.path.join(TRUSTEE_MIRROR_DIR, '_temp_pw_cache.json')
# 缓存新鲜期：之内直接复用不碰 dim；超过则尝试重新申请（申请失败仍回落旧密码）
TEMP_PW_TTL = 6 * 3600


# 读缓存的临时密码，返回 (密码, 申请时间, 是否在新鲜期内)；无缓存返回 (None, None, False)
def read_temp_pw(env, username):
    try:
        with open(TEMP_PW_CACHE, 'r', encoding='utf-8') as f:
            cache = json.load(f)
    except (OSError, ValueError):
        return None, None, False
    rec = (cache or {}).get(f'{env}:{username}') or {}
    password = rec.get('password')
    if not password:
        return None, None, False
    fresh = (time.time() - float(rec.get('mtime') or 0)) < TEMP_PW_TTL
    return password, rec.get('time') or '', fresh


# 申请成功后落盘缓存（目录不存在或写失败一律静默，不影响主流程）
def save_temp_pw(env, username, password):
    if not os.path.isdir(os.path.dirname(TEMP_PW_CACHE)):
        return
    try:
        cache = {}
        if os.path.exists(TEMP_PW_CACHE):
            try:
                with open(TEMP_PW_CACHE, 'r', encoding='utf-8') as f:
                    cache = json.load(f)
            except (OSError, ValueError):
                cache = {}
        if not isinstance(cache, dict):
            cache = {}
        cache[f'{env}:{username}'] = {
            'password': password,
            'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'mtime': time.time(),
        }
        with open(TEMP_PW_CACHE, 'w', encoding='utf-8') as f:
            json.dump(cache, f, ensure_ascii=False)
    except OSError:
        pass


# 取临时密码：新鲜缓存优先 → 否则申请 → 申请失败（如 dim 限流）回落旧缓存
# force=True 跳过缓存强制重申（缓存密码登录失败时用）
# dim_token_getter 延迟取 accessToken，命中缓存时完全不碰 dim
# 返回 (密码, 错误说明, 来源说明, 是否来自缓存)
def ensure_temp_password(username, env, dim_base, dim_token_getter, force=False):
    cached, ts, fresh = (None, None, False) if force else read_temp_pw(env, username)
    if cached and fresh:
        return cached, None, f'复用本地缓存（申请于 {ts}）', True
    try:
        password = apply_dim_password(username, dim_base, dim_token_getter())
    except ToolError as e:
        if cached:
            return cached, None, f'dim 申请失败（{e}），回落本地缓存（申请于 {ts}）', True
        return None, str(e), None, False
    save_temp_pw(env, username, password)
    return password, None, '新申请', False


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
        'user-agent': _APP_USER_AGENT,
        **_APP_COMMON_HEADERS,
        'umid': 'b1813a52eea4ec78a1bc3a6e6cea34de',
        'host': app_server,
        'serverid': '0',
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
# action：all = 查 OSS 信息 + APP（英语）token；trustee = 只查托管校务 token（前端「查托管」按钮单独触发）
# 两者分开：取托管要再登录 + switch，会话复用下可能让刚取到的英语 token 在部分服务上失效
@register_tool('user_info')
def run(params):
    username = get_str_param(params, 'username').strip()
    env = get_choice_param(params, 'env', tuple(ENV_CONFIG), default='test')
    action = get_choice_param(params, 'action', ('all', 'trustee'), default='all')
    config = ENV_CONFIG[env]

    infos = []

    # 该账号在当前环境的固定密码（未收录 = None，走临时密码兜底）
    fixed_pw = FIXED_PASSWORDS.get(env, {}).get(username)
    if fixed_pw:
        infos.append({"label": "固定密码", "value": fixed_pw})

    # 临时密码懒申请：固定密码两个系统都通就完全不申请；dim token 同样懒加载
    #（有固定密码的账号全程不碰 dim，dim 挂了也不影响这类账号）
    temp_state = {'done': False, 'token': None, 'password': None, 'error': None, 'from_cache': False}

    def ensure_temp_pw(force=False):
        if force or not temp_state['done']:
            temp_state['done'] = True

            def dim_token():
                if temp_state['token'] is None:
                    temp_state['token'] = get_dim_token(DIM_LOGIN_BASE)
                return temp_state['token']

            pw, err, note, from_cache = ensure_temp_password(username, env, config['dim_base'],
                                                             dim_token, force=force)
            temp_state.update({'password': pw, 'error': err, 'from_cache': from_cache})
            if pw:
                # 同 label 只保留最新一次（force 重申时覆盖旧展示）
                infos[:] = [i for i in infos if i['label'] not in ('OSS 临时密码', 'OSS 临时密码备注')]
                infos.append({"label": "OSS 临时密码", "value": pw})
                if note and note != '新申请':
                    infos.append({"label": "OSS 临时密码备注", "value": note})
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
            # 缓存的临时密码可能已失效 → 强制重申一次再试
            if st['from_cache']:
                st = ensure_temp_pw(force=True)
                if not st['error']:
                    try:
                        return login_fn(username, st['password'], base)
                    except ToolError as retry_err:
                        e = retry_err
            infos.append({"label": fail_label, "value": f"获取失败: {e}", "error": True})
            return None

    # 托管校区取 token：先看登录沾光（登录 token 已是托管身份直接用）；主校区状态时
    # 走 password_login + switch 跨身份切换（header/RU 声明当前身份，URL 指向目标身份）
    def fetch_trustee_token(inst, app_token):
        tgt_uid = str(inst.get('userId') or '')
        tgt_iid = str(inst.get('instId') or '')
        if is_trustee_token(app_token, inst):
            save_platform_token(tgt_iid, tgt_uid, app_token)
            infos.append({"label": "校务 token", "value": app_token})
            return
        # 慢路径密码：固定密码优先，未收录回落临时密码（懒申请）；why 记录失败原因，兜底/报错时一并展示
        rec, why = None, None
        pw = fixed_pw
        if not pw:
            st = ensure_temp_pw()
            pw = st.get('password') if not st.get('error') else None
            if not pw:
                why = f"无可用密码（{st.get('error')}）"
        if not tgt_iid:
            why = '托管节点缺少 instId'
        elif pw:
            try:
                pdata = password_login(username, pw, config['app_server'])
                rec, why = switch_to_trustee_inst(pdata, config['app_server'], username, tgt_iid, tgt_uid)
            except ToolError as e:
                why = f'密码登录失败：{e}'
        if rec:
            save_platform_token(tgt_iid, tgt_uid, rec)
            infos.append({"label": "校务 token", "value": rec})
            return
        # 备用兜底：本地平台缓存 与 Charles Mirror 取时间较近者（非实时）
        tok, src, ts = read_trustee_token_fallback(tgt_iid, tgt_uid)
        if tok:
            save_platform_token(tgt_iid, tgt_uid, tok)
            infos.append({"label": "校务 token", "value": tok})
            infos.append({"label": "校务 token 备注",
                          "value": f"自动切换失败（{why}），改用{src}备用 token（非实时调用），获取时间 {ts}"})
        else:
            infos.append({"label": "校务 token",
                          "value": f"未获取到：自动切换失败（{why}）且无备用 token（平台缓存/Charles），请在 App 切到托管校区后重查",
                          "error": True})

    # 查托管：courses 里找托管校区 → 有则取托管 token（结果只回 校务 token 相关条目），无则 has_trustee=False
    if action == 'trustee':
        app_data = system_login(app_login, config['app_server'], '校务 token')
        if app_data:
            trustees = find_trustee_courses(app_data.get('courses'), env)
            if not trustees:
                return {"infos": [], "has_trustee": False}
            fetch_trustee_token(trustees[0], app_data.get('token', ''))
        return {"infos": [i for i in infos if i['label'].startswith('校务 token')], "has_trustee": True}

    # 第一步：oss doLogin 拿用户信息与 token
    user_info = system_login(oss_dologin, config['oss_base'], 'OSS 用户信息')
    if user_info:
        oss_fields = ('userName', 'instId', 'instCode', 'token', 'serverId', 'userId')
        for field in oss_fields:
            infos.append({"label": f"OSS {field}", "value": str(user_info.get(field, ''))})

    # 第二步：app V2 登录拿 app token（key 同样是 L...S 编码，与 oss 独立判断）
    app_data = system_login(app_login, config['app_server'], 'APP token')
    if app_data:
        infos.append({"label": "APP token", "value": app_data.get('token', '')})

    # 展示顺序固定（未列出的条目排最后，保持原相对顺序）
    display_order = ('OSS userName', '固定密码', 'OSS 临时密码', 'OSS 临时密码备注', 'OSS userId',
                     'OSS instId', 'OSS instCode', 'OSS token', 'OSS serverId', 'APP token',
                     '校务 token', '校务 token 备注')
    infos.sort(key=lambda x: display_order.index(x['label']) if x['label'] in display_order else len(display_order))

    return {"infos": infos}
