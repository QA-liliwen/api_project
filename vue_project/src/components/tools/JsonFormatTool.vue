<template>
    <div>
        <div class="form-row">
            <label>操作</label>
            <div class="form-check form-check-inline">
                <input class="form-check-input" type="radio" id="mode-pretty" value="pretty" v-model="mode">
                <label class="form-check-label" for="mode-pretty">美化</label>
            </div>
            <div class="form-check form-check-inline">
                <input class="form-check-input" type="radio" id="mode-minify" value="minify" v-model="mode">
                <label class="form-check-label" for="mode-minify">压缩</label>
            </div>
            <div class="form-check form-check-inline">
                <input class="form-check-input" type="radio" id="mode-escape" value="escape" v-model="mode">
                <label class="form-check-label" for="mode-escape">转义</label>
            </div>
            <div class="form-check form-check-inline">
                <input class="form-check-input" type="radio" id="mode-unescape" value="unescape" v-model="mode">
                <label class="form-check-label" for="mode-unescape">去转义</label>
            </div>
            <button class="btn btn-primary btn-sm" style="margin-left: 15px" :disabled="loading" @click="run">
                {{ loading ? '处理中...' : '执行' }}
            </button>
        </div>

        <div style="margin-bottom: 15px">
            <label style="font-size: 14px; display: block; margin-bottom: 6px">原始文本</label>
            <textarea class="form-control" rows="10" v-model="text" placeholder='例如 {"code":0,"data":{"id":1}}'></textarea>
        </div>

        <div>
            <div class="result-title">
                <label style="font-size: 14px">结果<span v-if="length" style="color: #888">（{{ length }} 字符）</span></label>
                <button class="btn btn-outline-secondary btn-sm" style="margin-left: 10px" :disabled="!result" @click="copy">复制</button>
            </div>
            <textarea class="form-control" rows="12" readonly :value="result"></textarea>
        </div>
    </div>
</template>

<script>
    import api from '../../api'
    export default {
        data(){
            return{
                text: '',
                mode: 'pretty',
                result: '',
                length: 0,
                loading: false,
            }
        },
        methods:{
            run(){
                if (!this.text.trim()) {
                    alert('请输入原始文本');
                    return;
                }
                this.loading = true;
                api.post('/run_tool/', {
                    tool_key: 'json_format',
                    params: {text: this.text, mode: this.mode}
                }).then(res=>{
                    this.result = res.data.data.result;
                    this.length = res.data.data.length || this.result.length;
                    this.loading = false;
                }).catch(()=>{
                    this.loading = false;
                })
            },
            copy(){
                const el = document.createElement('textarea');
                el.value = this.result;
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
    }
    /* 单选框的文字标签不受 60px 宽度约束 */
    .form-row .form-check-label{
        width: auto;
    }
    .result-title{
        display: flex;
        align-items: center;
        margin-bottom: 6px;
    }
</style>
