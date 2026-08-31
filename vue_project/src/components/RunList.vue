<template>
    <div class="card" style="margin: 10px; padding: 15px; position: fixed; top: 60px; right: 1%; width: 18%">
        <h6>执行配置</h6>
        <select class="form-select form-select-sm mb-2" v-model="selected_domain">
            <option value="">选择域名</option>
            <option v-for="d in domains" :key="d.id" :value="d.id">{{ d.name }}</option>
        </select>
        <select class="form-select form-select-sm mb-2" v-model="selected_env">
            <option value="">选择环境</option>
            <option v-for="e in envs" :key="e.id" :value="e.id">{{ e.name }}</option>
        </select>
        <select class="form-select form-select-sm mb-2" v-model="selected_token">
            <option value="">选择Token</option>
            <option v-for="t in tokens" :key="t.id" :value="t.id">{{ t.name }}</option>
        </select>
        <select class="form-select form-select-sm mb-3" v-model="selected_header_template">
            <option value="">选择请求头模板</option>
            <option v-for="h in header_templates" :key="h.id" :value="h.id">{{ h.name }}</option>
        </select>

        <h6>待执行测试项 ({{ selected_items.length }})</h6>
        <div class="list-group" style="max-height: 520px; overflow-y: auto; margin-bottom: 10px">
            <a class="list-group-item list-group-item-action py-1 px-2" v-for="(name, idx) in selected_items" :key="idx">
                {{ name }}
            </a>
            <div v-if="selected_items.length === 0" class="text-muted py-2" style="font-size: 13px">
                请在左侧勾选测试项
            </div>
        </div>

        <button class="btn btn-primary w-100" style="font-size: 16px" @click="show_dialog = true" :disabled="running || selected_ids.length === 0">
            {{ running ? '执行中...' : '执行' }}
        </button>

        <!-- 执行弹窗 -->
        <div v-if="show_dialog" class="run-overlay" @click.self="show_dialog = false">
            <div class="run-dialog-box">
                <h5 style="margin-bottom: 15px">执行配置</h5>

                <div class="mb-3">
                    <label class="form-label">执行方式</label>
                    <div>
                        <div class="form-check form-check-inline">
                            <input class="form-check-input" type="radio" v-model="run_mode" value="local" id="mode_local">
                            <label class="form-check-label" for="mode_local">本地执行</label>
                        </div>
                        <div class="form-check form-check-inline">
                            <input class="form-check-input" type="radio" v-model="run_mode" value="jenkins" id="mode_jenkins">
                            <label class="form-check-label" for="mode_jenkins">Jenkins 执行</label>
                        </div>
                    </div>
                </div>

                <div class="mb-3">
                    <textarea class="form-control" rows="3" v-model="run_description" placeholder="填写本次执行说明"></textarea>
                </div>

                <div style="text-align: right">
                    <button class="btn btn-secondary me-2" @click="show_dialog = false">取消</button>
                    <button class="btn btn-primary" @click="do_execute" :disabled="running">
                        {{ running ? '执行中...' : '执行' }}
                    </button>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
    import axios from 'axios'
    import bus from '../bus'
    export default {
        data(){
            return{
                domains: [],
                envs: [],
                tokens: [],
                header_templates: [],
                selected_domain: '',
                selected_env: '',
                selected_token: '',
                selected_header_template: '',
                running: false,
                selected_items: [],
                selected_ids: [],
                show_dialog: false,
                run_mode: 'local',
                run_description: '',
            }
        },
        mounted:function () {
            this.get_config()
            bus.$on('items:changed', payload => {
                this.selected_items = payload.names
                this.selected_ids = payload.ids
            })
        },
        beforeDestroy(){
            bus.$off('items:changed')
        },
        methods:{
            get_config(){
                axios.get('http://127.0.0.100:8000/get_run_config/').then(res=>{
                    this.domains = res.data.domains;
                    this.envs = res.data.envs;
                    this.tokens = res.data.tokens;
                    this.header_templates = res.data.header_templates;
                })
            },
            do_execute(){
                if (this.selected_ids.length === 0) {
                    alert('请先选择测试项');
                    return
                }
                this.running = true;

                const payload = {
                    test_item_ids: this.selected_ids,
                    domain_id: this.selected_domain || null,
                    env_id: this.selected_env || null,
                    token_id: this.selected_token || null,
                    header_template_id: this.selected_header_template || null,
                    description: this.run_description,
                    run_mode: this.run_mode,
                };

                axios.post('http://127.0.0.100:8000/execute_run/', payload).then(res=>{
                    this.show_dialog = false;
                    this.run_description = '';
                    const results = res.data.results || [];
                    const runIds = results.map(r => r.run_id).join(', ');
                    const jenkinsUrl = (results.find(r => r.jenkins_build_url) || {}).jenkins_build_url;
                    if (jenkinsUrl) {
                        alert('Jenkins 执行已提交，run_id=' + runIds + '\n构建链接：' + jenkinsUrl);
                    } else {
                        alert('本地执行已提交，run_id=' + runIds);
                    }
                }).catch(err=>{
                    console.error('执行失败：', err);
                    const msg = err.response?.data?.message || err.response?.data?.msg || err.message || '未知错误';
                    alert('执行失败：' + msg);
                }).finally(()=>{
                    this.running = false
                })
            }
        }
    }
</script>

<style scoped>
    .run-overlay{
        position: fixed; top: 0; left: 0; width: 100%; height: 100%;
        background: rgba(0,0,0,0.4); display: flex;
        align-items: center; justify-content: center; z-index: 9999;
    }
    .run-dialog-box{
        background: #fff; border-radius: 8px; padding: 24px;
        width: 420px; box-shadow: 0 4px 20px rgba(0,0,0,0.2);
    }
</style>
