<template>
    <div>
        <div class="now-bar">
            <span>当前秒级：<b>{{ now_seconds }}</b></span>
            <span style="margin-left: 25px">当前毫秒级：<b>{{ now_milliseconds }}</b></span>
        </div>

        <div class="form-row">
            <label>方向</label>
            <select class="form-select form-select-sm" style="width: 200px" v-model="direction">
                <option value="ts_to_date">时间戳 → 日期</option>
                <option value="date_to_ts">日期 → 时间戳</option>
            </select>
            <button class="btn btn-primary btn-sm" style="margin-left: 15px" :disabled="loading" @click="run">
                {{ loading ? '处理中...' : '转换' }}
            </button>
        </div>

        <div class="form-row">
            <label>输入</label>
            <input class="form-control form-control-sm" style="width: 320px" v-model="text"
                   :placeholder="placeholder" @keyup.enter="run">
        </div>

        <div class="result-box">
            <div class="result-line">
                <span class="result-label">结果</span>
                <span class="result-value">{{ result || '-' }}</span>
                <button class="btn btn-outline-secondary btn-sm" style="margin-left: 15px" :disabled="!result" @click="copy(result)">复制</button>
            </div>
            <div class="result-line" v-if="unit">
                <span class="result-label">识别单位</span>
                <span class="result-value">{{ unit }}</span>
            </div>
            <div class="result-line" v-if="result_milliseconds">
                <span class="result-label">毫秒时间戳</span>
                <span class="result-value">{{ result_milliseconds }}</span>
                <button class="btn btn-outline-secondary btn-sm" style="margin-left: 15px" @click="copy(result_milliseconds)">复制</button>
            </div>
        </div>
    </div>
</template>

<script>
    import api from '../../api'
    export default {
        data(){
            return{
                text: '',
                direction: 'ts_to_date',
                result: '',
                unit: '',
                result_milliseconds: '',
                now_seconds: '',
                now_milliseconds: '',
                loading: false,
                timer: null,
            }
        },
        computed:{
            placeholder(){
                return this.direction === 'ts_to_date' ? '例如 1757000000 或 1757000000000' : '例如 2026-09-04 18:30:00'
            }
        },
        mounted:function () {
            this.refresh_now();
            // 顶部当前时间每秒刷新，方便直接取值
            this.timer = setInterval(this.refresh_now, 1000);
        },
        beforeDestroy:function () {
            clearInterval(this.timer);
        },
        watch:{
            direction(){
                this.result = '';
                this.unit = '';
                this.result_milliseconds = '';
            }
        },
        methods:{
            refresh_now(){
                const ms = Date.now();
                this.now_seconds = String(Math.floor(ms / 1000));
                this.now_milliseconds = String(ms);
            },
            run(){
                if (!this.text.trim()) {
                    alert('请输入要转换的内容');
                    return;
                }
                this.loading = true;
                api.post('/run_tool/', {
                    tool_key: 'timestamp_convert',
                    params: {text: this.text, direction: this.direction}
                }).then(res=>{
                    const data = res.data.data;
                    this.result = data.result;
                    this.unit = data.unit || '';
                    this.result_milliseconds = data.result_milliseconds || '';
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
    .now-bar{
        font-size: 14px;
        color: #555;
        margin-bottom: 20px;
    }
    .form-row{
        display: flex;
        align-items: center;
        margin-bottom: 15px;
    }
    .form-row label{
        width: 60px;
        font-size: 14px;
    }
    .result-box{
        margin-top: 25px;
        padding: 15px;
        background-color: #f8f9fa;
        border-radius: 4px;
    }
    .result-line{
        display: flex;
        align-items: center;
        margin-bottom: 10px;
        font-size: 14px;
    }
    .result-line:last-child{
        margin-bottom: 0;
    }
    .result-label{
        width: 90px;
        color: #888;
    }
    .result-value{
        font-weight: bold;
    }
</style>
