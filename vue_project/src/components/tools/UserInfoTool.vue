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
            <button class="btn btn-primary btn-sm" style="margin-left: 15px" :disabled="loading" @click="run">
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
            <div class="result-line" v-for="item in infos" :key="item.label">
                <span class="result-label">{{ item.label }}</span>
                <span class="result-value" :class="{'error-value': item.error}" title="点击复制" @click="copy(item.value)">{{ item.value }}</span>
            </div>
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
                if (this.loading) {
                    return;
                }
                this.env = env;
                this.username = username;
                this.run();
            },
            run(){
                if (!this.username.trim()) {
                    alert('请输入用户名');
                    return;
                }
                this.loading = true;
                api.post('/run_tool/', {
                    tool_key: 'user_info',
                    params: {username: this.username.trim(), env: this.env}
                }).then(res=>{
                    // 业务失败（如 dim 登录都失败）：后端返回 code:-1，提示原因
                    if (res.data.code === -1) {
                        alert(res.data.message);
                        this.loading = false;
                        return;
                    }
                    this.infos = res.data.data.infos || [];
                    this.loading = false;
                }).catch(()=>{
                    this.loading = false;
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
