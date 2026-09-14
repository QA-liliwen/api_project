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

        <div class="result-box" v-if="infos.length">
            <div class="result-line" v-for="item in infos" :key="item.label">
                <span class="result-label">{{ item.label }}</span>
                <span class="result-value" title="点击复制" @click="copy(item.value)">{{ item.value }}</span>
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
            }
        },
        methods:{
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
</style>
