<template>
    <div class="card" style="margin: 10px; padding: 15px; position: fixed; top: 60px; right: 1%; width: 18%">
        <h6>执行配置</h6>
        <div class="d-flex align-items-center gap-2 mb-2" style="margin-top: 20px;">
            <label class="form-label mb-0 text-nowrap">选择域名:</label>
            <select class="form-select form-select-sm" v-model="selected_domain">
                <option v-for="d in domains" :key="d.id" :value="d.id">{{ d.name }}</option>
            </select>
        </div>
        <div class="d-flex align-items-center gap-2 mb-3">
            <label class="form-label mb-0 text-nowrap">选择环境:</label>
            <select class="form-select form-select-sm" v-model="selected_env">
                <option v-for="e in envs" :key="e.id" :value="e.id">{{ e.name }}</option>
            </select>
        </div>
        <button class="btn btn-outline-secondary btn-sm w-100 mb-3" @click="open_role_dialog">角色配置</button>

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

        <!-- 角色配置弹窗：行=环境，列=角色，格子=账号名 -->
        <div v-if="show_role_dialog" class="run-overlay" @click.self="show_role_dialog = false">
            <div class="run-dialog-box" style="width: 860px">
                <h5 style="margin-bottom: 15px">角色配置（环境 × 角色 → 账号）</h5>
                <table class="table table-bordered" style="font-size: 14px; margin-bottom: 15px">
                    <thead style="text-align: center">
                        <tr>
                            <th>环境</th>
                            <th v-for="r in roles" :key="r">{{ roleLabel(r) }}</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr v-for="e in envs" :key="e.id">
                            <td style="text-align: center; white-space: nowrap">{{ e.name }}</td>
                            <td v-for="r in roles" :key="r">
                                <input type="text" class="form-control form-control-sm" v-model="account_matrix[e.id][r]" style="min-width: 110px">
                            </td>
                        </tr>
                    </tbody>
                </table>
                <div style="text-align: right">
                    <button class="btn btn-secondary me-2" @click="show_role_dialog = false">取消</button>
                    <button class="btn btn-primary" @click="save_accounts">保存</button>
                </div>
            </div>
        </div>

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
    import bus from '../../bus'
    import { roleLabel } from './role_labels'
    export default {
        data(){
            return{
                domains: [],
                envs: [],
                selected_domain: '',
                selected_env: '',
                running: false,
                selected_items: [],
                selected_ids: [],
                show_dialog: false,
                run_mode: 'local',
                run_description: '',
                show_role_dialog: false,
                roles: [],
                account_matrix: {},
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
            roleLabel,
            get_config(){
                axios.get('http://172.16.2.60:8000/get_run_config/').then(res=>{
                    this.domains = res.data.domains;
                    this.envs = res.data.envs;
                    // 自动选中后台标记为默认的域名/环境
                    const default_domain = this.domains.find(d => d.is_default);
                    const default_env = this.envs.find(e => e.is_default);
                    if (default_domain) this.selected_domain = default_domain.id;
                    if (default_env) this.selected_env = default_env.id;
                })
            },
            open_role_dialog(){
                axios.get('http://172.16.2.60:8000/get_test_accounts/').then(res => {
                    this.roles = res.data.roles || [];
                    // 先按 环境×角色 初始化空格子（保证 Vue2 响应式），再回填已保存账号
                    const matrix = {};
                    this.envs.forEach(e => {
                        const row = {};
                        this.roles.forEach(r => { row[r] = ''; });
                        matrix[e.id] = row;
                    });
                    (res.data.accounts || []).forEach(a => {
                        if (matrix[a.env_id] && a.role in matrix[a.env_id]) matrix[a.env_id][a.role] = a.username;
                    });
                    this.account_matrix = matrix;
                    this.show_role_dialog = true;
                })
            },
            save_accounts(){
                // 全量提交（含空格子，后端过滤空用户名不落库）
                const accounts = [];
                this.envs.forEach(e => {
                    this.roles.forEach(r => {
                        accounts.push({env_id: e.id, role: r, username: (this.account_matrix[e.id] || {})[r] || ''});
                    });
                });
                axios.post('http://172.16.2.60:8000/update_test_accounts/', {accounts}).then(res => {
                    if (res.data.code === 0) {
                        alert('保存成功，共 ' + res.data.count + ' 条映射');
                        this.show_role_dialog = false;
                    } else {
                        alert(res.data.message || '保存失败');
                    }
                }).catch(err => {
                    alert('保存失败: ' + err.message);
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
                    description: this.run_description,
                    run_mode: this.run_mode,
                };

                axios.post('http://172.16.2.60:8000/execute_run/', payload).then(res=>{
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
