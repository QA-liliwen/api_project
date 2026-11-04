<template>
    <div>
        <div class="form-row">
            <label>环境</label>
            <div class="form-check form-check-inline">
                <input class="form-check-input" type="radio" id="env-test" value="test" v-model="env">
                <label class="form-check-label" for="env-test">测试</label>
            </div>
            <div class="form-check form-check-inline">
                <input class="form-check-input" type="radio" id="env-pre" value="pre" v-model="env">
                <label class="form-check-label" for="env-pre">预发布</label>
            </div>
            <div class="form-check form-check-inline">
                <input class="form-check-input" type="radio" id="env-prod" value="prod" v-model="env">
                <label class="form-check-label" for="env-prod">生产</label>
            </div>
        </div>

        <div class="form-row">
            <label>用户名</label>
            <input class="form-control form-control-sm" style="width: 320px" v-model="username"
                   placeholder="输入用户名，一次拿全多系统信息" @keyup.enter="run">
            <button class="btn btn-primary btn-sm" style="margin-left: 15px" :disabled="loading || trusteeLoading" @click="run">
                {{ loading ? '查询中...' : '查询' }}
            </button>
        </div>

        <div class="account-row" v-for="group in accountGroups" :key="group.env">
            <span class="group-label">{{ group.label }}</span>
            <span v-for="acc in group.accounts" :key="acc" class="account-item"
                  :class="{'item-active': env === group.env && username === acc}"
                  @click="quickQuery(group.env, acc)">{{ acc }}</span>
        </div>

        <div class="result-box" v-if="infos.length">
            <template v-for="item in infos">
                <div class="result-line" :key="item.label">
                    <span class="result-label">{{ item.label }}</span>
                    <span class="result-value" :class="{'error-value': item.error}" title="点击复制" @click="copy(item.value)">{{ item.value }}</span>
                </div>
                <!-- APP token 下方：单独查托管（托管获取失败时在校务 token 下方可重试） -->
                <div class="result-line" v-if="showTrusteeBtn(item)" :key="item.label + '-btn'">
                    <span class="result-label"></span>
                    <button class="btn btn-outline-primary btn-sm" :disabled="trusteeLoading" @click="queryTrustee">
                        {{ trusteeLoading ? '查询中...' : (item.label === 'APP token' ? '查托管' : '重新查托管') }}
                    </button>
                </div>
            </template>
        </div>
    </div>
</template>

<script>
    import api from '../../api'
    export default {
        name: 'UserInfoTool',
        data(){
            return{
                env: 'test',
                username: '',
                infos: [],
                loading: false,
                trusteeLoading: false,
                // 当前结果对应的账号与环境（查托管用它，不受输入框后续修改影响）
                queried: {username: '', env: ''},
                accountGroups: [
                    {env: 'test', label: '测试', accounts: ['adminexam', 'admincontent', 'adminzhihui', 'adminvswrr', 'adminfmf', 'adminqa9515']},
                    {env: 'pre', label: '预发布', accounts: ['adminexam', 'admincontent', 'adminzhihui', 'adminxswrr']},
                    {env: 'prod', label: '生产', accounts: ['adminexam', 'admincontent', 'adminzhihui', 'adminvswrr', 'adminfmf', 'adminlsllw']},
                ],
            }
        },
        methods:{
            // 右侧常用账号点击：切换环境+填用户名，直接触发查询
            quickQuery(env, username){
                if (this.loading || this.trusteeLoading) {
                    return;
                }
                this.env = env;
                this.username = username;
                this.run();
            },
            run(){
                if (this.loading || this.trusteeLoading) {
                    return;
                }
                if (!this.username.trim()) {
                    alert('请输入用户名');
                    return;
                }
                this.loading = true;
                const queried = {username: this.username.trim(), env: this.env};
                api.post('/run_tool/', {
                    tool_key: 'user_info',
                    params: queried
                }).then(res=>{
                    this.infos = res.data.data.infos || [];
                    this.queried = queried;
                    this.loading = false;
                }).catch(()=>{
                    this.loading = false;
                })
            },
            // 按钮只出现一次：尚未查过托管时挂在 APP token 下；查过但失败时挂在校务 token 报错条目下
            showTrusteeBtn(item){
                if (item.label === '校务 token') {
                    return !!item.error;
                }
                const hasTrustee = this.infos.some(i => i.label === '校务 token');
                return item.label === 'APP token' && !item.error && !hasTrustee;
            },
            // 查托管：拿到校务 token → 顶替 APP token（取托管会让英语 token 可能失效，不再展示）；
            // 失败 → 保留 APP token，只刷新校务 token 报错条目；无托管 → 提示
            queryTrustee(){
                if (this.trusteeLoading) {
                    return;
                }
                this.trusteeLoading = true;
                const queried = this.queried;
                api.post('/run_tool/', {
                    tool_key: 'user_info',
                    params: {...queried, action: 'trustee'}
                }).then(res=>{
                    this.trusteeLoading = false;
                    // 等待期间已换账号重查，这次结果作废
                    if (queried !== this.queried) {
                        return;
                    }
                    const data = res.data.data;
                    if (!data.has_trustee) {
                        alert(`${queried.username} 没有托管学校`);
                        return;
                    }
                    const fresh = data.infos || [];
                    const ok = fresh.some(i => i.label === '校务 token' && !i.error);
                    const first = this.infos.findIndex(i => i.label === 'APP token' || i.label.startsWith('校务 token'));
                    const rest = this.infos.filter(i => !(i.label.startsWith('校务 token') || (ok && i.label === 'APP token')));
                    const appAt = rest.findIndex(i => i.label === 'APP token');
                    const at = ok ? (first < 0 ? rest.length : first) : (appAt < 0 ? rest.length : appAt + 1);
                    rest.splice(at, 0, ...fresh);
                    this.infos = rest;
                }).catch(()=>{
                    this.trusteeLoading = false;
                })
            },
            copy(value){
                const el = document.createElement('textarea');
                el.value = value;
                document.body.appendChild(el);
                el.select();
                document.execCommand('copy');
                document.body.removeChild(el);
            }
        }
    }
</script>

<style scoped>
    .form-row{
        display: flex;
        align-items: center;
        margin-bottom: 15px;
    }
    .form-row label{
        width: 60px;
        font-size: 14px;
        flex-shrink: 0;
    }
    /* 环境单选框的文字标签不受 60px 宽度约束 */
    .form-row .form-check-label{
        width: auto;
    }
    .result-box{
        margin-top: 25px;
        padding: 15px;
        background-color: #f8f9fa;
        border-radius: 4px;
    }
    /* 常用账号：按环境分行展示在输入框下方，行首 label 与表单 label 对齐 */
    .account-row{
        display: flex;
        align-items: center;
        flex-wrap: wrap;
        margin-bottom: 8px;
        font-size: 14px;
    }
    .group-label{
        width: 60px;
        flex-shrink: 0;
        font-size: 13px;
        color: #888;
    }
    /* 账号标签：圆角小徽章，点击即查询 */
    .account-item{
        display: inline-block;
        padding: 2px 10px;
        margin: 0 6px 6px 0;
        background-color: #fff;
        border: 1px solid #ddd;
        border-radius: 12px;
        font-size: 13px;
        cursor: pointer;
    }
    .account-item:hover{
        border-color: #0d6efd;
        color: #0d6efd;
    }
    /* 当前查询中的账号高亮 */
    .account-item.item-active{
        border-color: #0d6efd;
        color: #0d6efd;
        background-color: #e7f1ff;
    }
    .result-line{
        display: flex;
        align-items: flex-start;
        margin-bottom: 12px;
        font-size: 14px;
    }
    .result-line:last-child{
        margin-bottom: 0;
    }
    .result-label{
        width: 120px;
        color: #888;
        flex-shrink: 0;
        line-height: 26px;
    }
    /* token 类字段较长，允许换行完整展示；虚线下划线提示可点击复制 */
    .result-value{
        font-weight: bold;
        word-break: break-all;
        line-height: 26px;
        white-space: pre-wrap;
        cursor: pointer;
        border-bottom: 1px dashed #999;
    }
    .result-value:hover{
        border-bottom-color: #0d6efd;
        color: #0d6efd;
    }
    /* 失败项（后端带 error 标记）标红，与正常结果区分 */
    .result-value.error-value{
        color: #dc3545;
        border-bottom-color: #dc3545;
    }
    .result-value.error-value:hover{
        color: #dc3545;
        border-bottom-color: #dc3545;
    }
</style>
