from api_app.api_tools.base import ToolError
from api_app.api_tools.user_info import (
    get_dim_token,
    apply_dim_password,
    oss_dologin,
    app_login,
    FIXED_PASSWORDS,
    password_login,
    switch_to_trustee,
    save_platform_token,
    read_trustee_token_fallback,
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
# trustee_usernames: 托管角色（afterschool）的账号集合，其 app token 走托管身份 token（登录沾光/switch 切换）
# trustee_notes: 可选出参 dict，回填托管账号的获取说明（提取成功/跳过原因），供执行日志统一注释
# 返回 {用户名: {'oss': token, 'app': token}}
# 登录/提取失败不拦截，对应 token 落空串（用例执行时自然 401，报告可见）
def fetch_tokens(domain, env_seg, app_server, usernames, trustee_usernames=(), trustee_notes=None):
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

    # 登录（固定密码优先，失败回落临时密码），返回完整登录响应；失败抛 ToolError
    def login_data(username, system):
        # 根据调用的oss|app，将对应函数赋值，以便后续调用。
        login_fn = {'oss': oss_dologin, 'app': app_login}[system]
        login_base = oss_base if system == 'oss' else app_server
        # 第一步：固定密码
        fixed_pw = fixed_pw_map.get(username)
        if fixed_pw:
            try:
                return login_fn(username, fixed_pw, login_base)
            except ToolError:
                pass
        # 第二步：临时密码
        temp = ensure_temp_pw(username)
        if temp['error'] or not temp['password']:
            raise ToolError(f"临时密码不可用（{temp['error']}）")
        return login_fn(username, temp['password'], login_base)

    def login_one(username, system):
        # 登录失败不拦截，对应系统 token 落空串
        try:
            return login_data(username, system)['token']
        except ToolError as e:
            print(f"[token_fetcher] 环境[{env_seg}] 账号 {username} 的 {system} token 获取失败：{e}")
            return ''

    # 托管角色账号的 app token：按 courseType=after_school_care 识别托管校区后取托管身份 token
    # 快路径：登录沾光 —— 服务端记住托管校区时，登录 token 前缀就是托管 userId，直接用
    # 慢路径：主校区态时，password_login + switch 跨身份切换（密码：固定优先，未收录回落临时密码）
    #   （header/RU 声明当前身份，URL 参数指向目标身份，返回目标身份托管 token）
    # 失败一律跳过（app token 落空串）并返回原因，由 trustee_notes 交执行日志统一注释
    # 约定：托管账号不要同时配置到其他角色（token_map 按用户名组织，替换会影响其全部角色）
    def login_trustee(username):
        try:
            data = login_data(username, 'app')
        except ToolError as e:
            return '', f"跳过（获取失败：{e}）"

        trustees = [
            c for c in (data.get('courses') or [])
            if isinstance(c, dict) and str(c.get('courseType')) == 'after_school_care'
        ]
        if not trustees:
            return '', '跳过（获取失败：账号无托管身份）'

        # 多个托管身份时取第一个（执行器仅一个 afterschool 角色）
        inst = trustees[0]
        tgt_uid = str(inst.get('userId') or '')
        tgt_iid = str(inst.get('instId') or '')
        # 校区代号用 instName（courses 节点无 instCode 字段，如 fmf19/xsw644/fmf17）
        inst_name = str(inst.get('instName') or '')
        inst_label = f"（{inst_name}）" if inst_name else ''
        token = data.get('token') or ''
        if tgt_uid and token.startswith(f'{tgt_uid}:'):
            save_platform_token(tgt_iid, tgt_uid, token)
            return token, f"提取成功{inst_label}"

        # 主校区状态：password_login + switch 自动切换（固定密码优先，未收录回落临时密码）
        pw = fixed_pw_map.get(username)
        if not pw:
            temp = ensure_temp_pw(username)
            pw = temp.get('password') if not temp.get('error') else None
        if pw:
            try:
                pdata = password_login(username, pw, app_server)
                u = pdata.get('user') or {}
                new_t = switch_to_trustee(str(pdata.get('token') or ''), str(u.get('instId') or ''),
                                          str(u.get('serverId') or ''), str(u.get('userId') or ''),
                                          app_server, username, tgt_iid, tgt_uid)
                if new_t:
                    save_platform_token(tgt_iid, tgt_uid, new_t)
                    return new_t, f'提取成功{inst_label}'
            except ToolError:
                pass
        # 备用兜底：本地平台缓存 与 Charles Mirror 取时间较近者（非实时，note 带来源与时间）
        tok, src, ts = read_trustee_token_fallback(tgt_iid, tgt_uid)
        if tok:
            save_platform_token(tgt_iid, tgt_uid, tok)
            return tok, f'备用（{src}，获取时间 {ts}）'
        return '', '跳过（获取失败：登录为主校区 token 且无法自动切换，请在 App 切到托管校区后重跑）'

    # 每个账号固定拿 oss + app 两个 token（托管账号的 app 端走快/慢路径拿托管 token）
    trustee_set = set(trustee_usernames)
    tokens = {}
    for username in sorted(set(usernames)):
        if username in trustee_set:
            app_token, note = login_trustee(username)
            tokens[username] = {'oss': login_one(username, 'oss'), 'app': app_token}
            if trustee_notes is not None:
                trustee_notes[username] = note
        else:
            tokens[username] = {system: login_one(username, system) for system in ('oss', 'app')}
    return tokens
