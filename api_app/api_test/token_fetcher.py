from api_app.api_tools.base import ToolError
from api_app.api_tools.user_info import (
    get_dim_token,
    apply_dim_password,
    oss_dologin,
    app_login,
    FIXED_PASSWORDS,
)

# dim accessToken 统一从测试环境获取
DIM_BASE = 'https://devapi1.lingshi.com/dim/vs2'

DOMAIN_PASSWORD_PROFILE = {
    'devapi1.lingshi.com': 'test',
    'preapi1.lingshi.com': 'pre',
    'api1.lingshi.com': 'prod',
}


# ===== 批量获取 token（入口） =====
# domain:   域名
# env_seg:  环境段
# app_server: app 登录域名
# usernames: 用户名列表
# 返回 {用户名: {'oss': token, 'app': token}}
# 登录失败不拦截，对应系统 token 落空串（用例执行时自然 401，报告可见）
def fetch_tokens(domain, env_seg, app_server, usernames):
    oss_base = f'https://{domain}/school/{env_seg}'
    dim_base = f'https://{domain}/dim/{env_seg}'
    # 当前域名的固定密码表
    fixed_pw_map = FIXED_PASSWORDS.get(DOMAIN_PASSWORD_PROFILE.get(domain, ''), {})
    dim_state = {'token': None}
    temp_pw_map = {}

    # 申请（或复用）某账号的临时密码；失败信息缓存，同账号后续系统不再重复调 dim
    def ensure_temp_pw(username):
        if username not in temp_pw_map:
            try:
                if dim_state['token'] is None:
                    dim_state['token'] = get_dim_token(DIM_BASE)
                password = apply_dim_password(username, dim_base, dim_state['token'])
                temp_pw_map[username] = {'password': password, 'error': None}
            except ToolError as e:
                temp_pw_map[username] = {'password': None, 'error': str(e)}
        return temp_pw_map[username]

    def login_one(username, system):
        # 根据调用的oss|app，将对应函数赋值，以便后续调用。
        login_fn = {'oss': oss_dologin, 'app': app_login}[system]
        login_base = oss_base if system == 'oss' else app_server
        # 第一步：固定密码
        fixed_pw = fixed_pw_map.get(username)
        if fixed_pw:
            try:
                return login_fn(username, fixed_pw, login_base)['token']
            except ToolError:
                pass
        # 第二步：临时密码（申请失败或登录失败均降级空串）
        temp = ensure_temp_pw(username)
        if temp['error'] or not temp['password']:
            print(f"[token_fetcher] 环境[{env_seg}] 账号 {username} 的 {system} token 获取失败：临时密码不可用（{temp['error']}）")
            return ''
        try:
            return login_fn(username, temp['password'], login_base)['token']
        except ToolError as e:
            print(f"[token_fetcher] 环境[{env_seg}] 账号 {username} 的 {system} token 获取失败：{e}")
            return ''

    # 每个账号固定拿 oss + app 两个 token
    tokens = {}
    for username in sorted(set(usernames)):
        tokens[username] = {system: login_one(username, system) for system in ('oss', 'app')}
    return tokens
