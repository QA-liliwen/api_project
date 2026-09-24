<template>
    <div style="padding: 20px">
        <div style="margin-bottom: 15px">
            <h4 style="margin: 0; text-align: center">测试结果</h4>
        </div>
        <!-- Jenkins 执行 -->
        <div style="margin-bottom: 30px">
            <h5 style="margin-bottom: 12px">Jenkins 执行</h5>
            <table class="table table-bordered table-hover" style="text-align: center; font-size: 14px">
                <thead class="table-light">
                    <tr>
                        <th style="text-align: left; padding-left: 10px">描述</th>
                        <th style="width: 80px">类型</th>
                        <th style="width: 100px">测试项</th>
                        <th style="width: 80px">状态</th>
                        <th style="width: 60px">总数</th>
                        <th style="width: 60px">通过</th>
                        <th style="width: 60px">失败</th>
                        <th style="width: 60px">跳过</th>
                        <th style="width: 80px">耗时(s)</th>
                        <th style="width: 100px">环境</th>
                        <th style="width: 160px">开始时间</th>
                        <th style="width: 160px">结束时间</th>
                        <th style="width: 80px">日志</th>
                        <th style="width: 80px">报告</th>
                        <th style="width: 80px">链接</th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="item in jenkins_results" :key="item.id">
                        <td style="text-align: left; padding-left: 10px">{{ item.description || '-' }}</td>
                        <td>{{ type_name(item.test_type) }}</td>
                        <td>
                            <button class="btn btn-outline-primary btn-sm" style="font-size: 12px" @click="show_items(item)">查看</button>
                        </td>
                        <td><span class="badge" :class="status_class(item.status)">{{ item.status }}</span></td>
                        <td>{{ item.total ?? '-' }}</td>
                        <td style="color: green">{{ item.passed ?? '-' }}</td>
                        <td style="color: red">{{ item.failed ?? '-' }}</td>
                        <td style="color: gray">{{ item.skipped ?? '-' }}</td>
                        <td>{{ item.duration_seconds ? item.duration_seconds.toFixed(1) : '-' }}</td>
                        <td>{{ item.env || '-' }}</td>
                        <td>{{ format_time(item.started_at) }}</td>
                        <td>{{ format_time(item.finished_at) }}</td>
                        <td>
                            <a v-if="item.log_file && item.jenkins_build_url" :href="'http://172.16.2.60:8000/download_jenkins_log/?run_id=' + item.id" class="btn btn-outline-primary btn-sm" style="font-size: 12px">下载</a>
                            <span v-else style="color: gray">-</span>
                        </td>
                        <td>
                            <a v-if="item.report_file && item.jenkins_build_url" :href="item.jenkins_build_url + 'artifact/' + item.report_file" target="_blank" class="btn btn-outline-success btn-sm" style="font-size: 12px">报告</a>
                            <span v-else style="color: gray">-</span>
                        </td>
                        <td>
                            <a v-if="item.jenkins_build_url" :href="item.jenkins_build_url" target="_blank" class="btn btn-outline-primary btn-sm" style="font-size: 12px">链接</a>
                            <span v-else style="color: gray">-</span>
                        </td>
                    </tr>
                    <tr v-if="jenkins_results.length === 0">
                        <td colspan="15" style="color: gray">暂无测试记录</td>
                    </tr>
                </tbody>
            </table>
        </div>

        <!-- 本地执行 -->
        <div style="margin-bottom: 30px">
            <h5 style="margin-bottom: 12px">本地执行</h5>
            <table class="table table-bordered table-hover" style="text-align: center; font-size: 14px">
                <thead class="table-light">
                    <tr>
                        <th style="text-align: left; padding-left: 10px">描述</th>
                        <th style="width: 80px">类型</th>
                        <th style="width: 100px">测试项</th>
                        <th style="width: 80px">状态</th>
                        <th style="width: 60px">总数</th>
                        <th style="width: 60px">通过</th>
                        <th style="width: 60px">失败</th>
                        <th style="width: 60px">跳过</th>
                        <th style="width: 80px">耗时(s)</th>
                        <th style="width: 100px">环境</th>
                        <th style="width: 160px">开始时间</th>
                        <th style="width: 160px">结束时间</th>
                        <th style="width: 80px">日志</th>
                        <th style="width: 80px">操作</th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="item in local_results" :key="item.id">
                        <td style="text-align: left; padding-left: 10px">{{ item.description || '-' }}</td>
                        <td>{{ type_name(item.test_type) }}</td>
                        <td>
                            <button class="btn btn-outline-primary btn-sm" style="font-size: 12px" @click="show_items(item)">查看</button>
                        </td>
                        <td><span class="badge" :class="status_class(item.status)">{{ item.status }}</span></td>
                        <td>{{ item.total ?? '-' }}</td>
                        <td style="color: green">{{ item.passed ?? '-' }}</td>
                        <td style="color: red">{{ item.failed ?? '-' }}</td>
                        <td style="color: gray">{{ item.skipped ?? '-' }}</td>
                        <td>{{ item.duration_seconds ? item.duration_seconds.toFixed(1) : '-' }}</td>
                        <td>{{ item.env || '-' }}</td>
                        <td>{{ format_time(item.started_at) }}</td>
                        <td>{{ format_time(item.finished_at) }}</td>
                        <td>
                            <a v-if="item.log_file" :href="'http://172.16.2.60:8000/download_log/?filename=' + item.log_file" class="btn btn-outline-primary btn-sm" style="font-size: 12px">下载</a>
                            <span v-else style="color: gray">-</span>
                        </td>
                        <td>
                            <a v-if="item.jenkins_build_url" :href="item.jenkins_build_url" target="_blank" class="btn btn-outline-primary btn-sm" style="font-size: 12px">Jenkins</a>
                            <span v-else style="color: gray">-</span>
                        </td>
                    </tr>
                    <tr v-if="local_results.length === 0">
                        <td colspan="14" style="color: gray">暂无测试记录</td>
                    </tr>
                </tbody>
            </table>
        </div>
        <!-- 测试项弹窗 -->
        <div v-if="item_modal.show" class="modal-backdrop" @click.self="item_modal.show = false">
            <div class="modal-dialog-custom">
                <div class="modal-header-custom">
                    <h5>测试项列表</h5>
                    <button type="button" class="btn-close" @click="item_modal.show = false"></button>
                </div>
                <div class="modal-body" style="max-height: 400px; overflow-y: auto">
                    <div v-for="(name, idx) in item_modal.names" :key="idx" style="padding: 6px 0; border-bottom: 1px solid #f0f0f0">
                        {{ idx + 1 }}. {{ name }}
                    </div>
                    <div v-if="item_modal.names.length === 0" style="color: gray">暂无测试项</div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" @click="item_modal.show = false">关闭</button>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
    import axios from 'axios'
    export default {
        data() {
            return {
                jenkins_results: [],
                local_results: [],
                item_modal: {
                    show: false,
                    names: []
                }
            }
        },
        mounted() {
            this.get_list()
        },
        methods: {
            get_list() {
                axios.get('http://172.16.2.60:8000/get_run_result_list/').then(res => {
                    this.jenkins_results = res.data.jenkins || []
                    this.local_results = res.data.local || []
                })
            },
            status_class(status) {
                const map = {
                    'running': 'bg-info',
                    'passed': 'bg-success',
                    'failed': 'bg-danger',
                }
                return map[status] || 'bg-secondary'
            },
            type_name(type) {
                const map = { 1: '单接口', 2: '多接口' }
                return map[type] || '-'
            },
            format_time(t) {
                if (!t) return '-'
                return t.replace('T', ' ').substring(0, 19)
            },
            show_items(item) {
                this.item_modal.names = item.test_item_names || []
                this.item_modal.show = true
            }
        }
    }
</script>

<style scoped>
    .modal-backdrop {
        position: fixed;
        top: 0; left: 0; right: 0; bottom: 0;
        background: rgba(0,0,0,0.4);
        z-index: 1050;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .modal-dialog-custom {
        background: white;
        border-radius: 8px;
        width: 500px;
        max-height: 85vh;
        overflow-y: auto;
        box-shadow: 0 4px 20px rgba(0,0,0,0.2);
    }
    .modal-header-custom {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 15px 20px;
        border-bottom: 1px solid #dee2e6;
    }
    .modal-footer {
        display: flex;
        gap: 8px;
        justify-content: flex-end;
        padding: 15px 20px;
        border-top: 1px solid #dee2e6;
    }
    .modal-body {
        padding: 20px;
    }
</style>
