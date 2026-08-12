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

        <button class="btn btn-primary w-100" style="font-size: 16px" @click="do_execute" :disabled="running || selected_items.length === 0">
            {{ running ? '执行中...' : '执行' }}
        </button>
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
            }
        },
        mounted:function () {
            console.log('[run_list] mounted')
            this.get_config()
            // 通过 event bus 接收 TestItemList 勾选事件（绕开 prop 响应性 HMR 问题）
            bus.$on('items:changed', payload => {
                console.log('[run_list] bus 收到:', payload)
                this.selected_items = payload.names
                this.selected_ids = payload.ids
            })
        },
        beforeDestroy(){
            bus.$off('items:changed')
        },
        methods:{
            get_config(){
                axios.get('http://localhost:8000/get_run_config/').then(res=>{
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
                axios.post('http://localhost:8000/execute_run/', {
                    test_item_ids: this.selected_ids,
                    domain_id: this.selected_domain || null,
                    env_id: this.selected_env || null,
                    token_id: this.selected_token || null,
                    header_template_id: this.selected_header_template || null,
                }).then(res=>{
                    console.log('执行结果：', res.data);
                    alert('执行已提交，run_id=' + res.data.run_id);
                }).catch(err=>{
                    console.error('执行失败：', err);
                    alert('执行失败');
                }).finally(()=>{
                    this.running = false
                })
            }
        }
    }
</script>
