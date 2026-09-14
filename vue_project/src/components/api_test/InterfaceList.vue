<template>
    <div style="padding: 20px">
        <div style="margin-bottom: 15px">
            <h4 style="margin: 0; text-align: center">接口列表</h4>
        </div>
        <div style="width: 80%; margin: 0 auto 10px auto; display: flex; align-items: center; gap: 8px">
            <input type="text" class="form-control" placeholder="搜索接口名称或url..." v-model="search_keyword" style="max-width: 300px">
            <button class="btn btn-outline-primary btn-sm" @click="open_create" style="margin-left: auto; margin-bottom: -8px;">新建接口</button>
        </div>
        <table class="table table-bordered table-hover" style="text-align: center; font-size: 14px; width: 80%; margin: 0 auto;">
            <thead class="table-light">
                <tr>
                    <th>接口名称</th>
                    <th style="width: 80px">方法</th>
                    <th>URL</th>
                    <th style="width: 200px">所属标签</th>
                    <th style="width: 200px">描述</th>
                    <th style="width: 70px">编辑</th>
                </tr>
            </thead>
            <tbody>
                <tr v-for="item in filtered_interfaces" :key="item.id">
                    <td style="text-align: left; padding-left: 10px">{{ item.name }}</td>
                    <td><span class="badge" :class="method_class(item.method)">{{ item.method }}</span></td>
                    <td style="text-align: left; padding-left: 10px; font-family: monospace; font-size: 12px">{{ item.url }}</td>
                    <td>{{ item.tag__name || '-' }}</td>
                    <td>{{ item.description || '-' }}</td>
                    <td @click.stop><button class="btn btn-outline-primary btn-sm" @click="open_edit(item)" style="border: 0">编辑</button></td>
                </tr>
                <tr v-if="filtered_interfaces.length === 0">
                    <td colspan="6" style="color: gray">暂无接口</td>
                </tr>
            </tbody>
        </table>

        <!-- 编辑弹窗 -->
        <div v-if="show_modal" class="modal-backdrop" @click.self="show_modal = false">
            <div class="modal-dialog-custom">
                <div class="modal-header-custom">
                    <h5>{{ edit_form.is_create ? '新建接口' : '编辑接口' }}</h5>
                    <button type="button" class="btn-close" @click="show_modal = false"></button>
                </div>
                <div class="modal-body">
                    <div class="form-row">
                        <label class="form-label-fixed">名 称：</label>
                        <input type="text" class="form-control" v-model="edit_form.name">
                    </div>
                    <div class="form-row">
                        <label class="form-label-fixed">方 法：</label>
                        <select class="form-select" v-model="edit_form.method">
                            <option>GET</option>
                            <option>POST</option>
                            <option>PUT</option>
                            <option>DELETE</option>
                            <option>PATCH</option>
                        </select>
                    </div>
                    <div class="form-row">
                        <label class="form-label-fixed">U R L：</label>
                        <input type="text" class="form-control" v-model="edit_form.url">
                    </div>
                    <div class="form-row">
                        <label class="form-label-fixed">一级标签：</label>
                        <select class="form-select" v-model="edit_form.tag_id">
                            <option :value="null">无</option>
                            <option v-for="tag in first_tags" :key="tag.id" :value="tag.id">{{ tag.name }}</option>
                        </select>
                    </div>
                    <div class="form-row">
                        <label class="form-label-fixed">描 述：</label>
                        <input type="text" class="form-control" v-model="edit_form.description">
                    </div>
                    <div class="form-row">
                        <label class="form-label-fixed">请求头：</label>
                        <textarea class="form-control" rows="3" v-model="edit_form.headers_json" style="font-family: monospace; font-size: 13px"></textarea>
                    </div>
                    <div class="form-row">
                        <label class="form-label-fixed">请求参数：</label>
                        <textarea class="form-control" rows="3" v-model="edit_form.params_json" style="font-family: monospace; font-size: 13px"></textarea>
                    </div>
                </div>
                <div class="modal-footer">
                    <button v-if="!edit_form.is_create" type="button" class="btn btn-danger" style="margin-right: auto" @click="soft_delete">删除接口</button>
                    <button type="button" class="btn btn-secondary" @click="show_modal = false">取消</button>
                    <button type="button" class="btn btn-primary" @click="save_edit">保存</button>
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
                interfaces: [],
                search_keyword: '',
                first_tags: [],
                show_modal: false,
                edit_form: {
                    id: null,
                    is_create: false,
                    name: '',
                    method: 'GET',
                    url: '',
                    tag_id: null,
                    sort: 0,
                    description: '',
                    headers_json: '{}',
                    params_json: '{}',
                },
            }
        },
        mounted() {
            this.get_list()
            this.get_first_tags()
        },
        computed: {
            filtered_interfaces() {
                const kw = this.search_keyword.trim().toLowerCase()
                if (!kw) return this.interfaces
                return this.interfaces.filter(item => {
                    if (item.name.toLowerCase().includes(kw)) return true
                    // URL 最后一段也作为搜索项
                    const segments = (item.url || '').replace(/\/+$/, '').split('/')
                    const last = (segments[segments.length - 1] || '').toLowerCase()
                    return last.includes(kw)
                })
            }
        },
        methods: {
            get_list() {
                axios.get('http://172.16.2.60:8000/get_interface_list/').then(res => {
                    this.interfaces = res.data.interfaces || []
                })
            },
            get_first_tags() {
                axios.get('http://172.16.2.60:8000/get_top_menu/').then(res => {
                    this.first_tags = res.data.first_tags || []
                })
            },
            method_class(method) {
                const map = {
                    'GET': 'bg-success',
                    'POST': 'bg-primary',
                    'PUT': 'bg-warning',
                    'DELETE': 'bg-danger',
                }
                return map[method] || 'bg-secondary'
            },
            open_create() {
                this.edit_form = {
                    id: null,
                    is_create: true,
                    name: '',
                    method: 'GET',
                    url: '',
                    tag_id: null,
                    sort: 0,
                    description: '',
                    headers_json: '{}',
                    params_json: '{}',
                }
                this.show_modal = true
            },
            open_edit(item) {
                axios.get('http://172.16.2.60:8000/get_interface_detail/', {
                    params: {id: item.id}
                }).then(res => {
                    if (res.data.code === 0) {
                        const d = res.data.data
                        this.edit_form = {
                            id: d.id,
                            is_create: false,
                            name: d.name,
                            method: d.method,
                            url: d.url,
                            tag_id: d.tag_id,
                            sort: d.sort || 0,
                            description: d.description || '',
                            headers_json: JSON.stringify(d.headers || {}, null, 2),
                            params_json: JSON.stringify(d.params || {}, null, 2),
                        }
                        this.show_modal = true
                    } else {
                        alert(res.data.message || '获取详情失败')
                    }
                })
            },
            save_edit() {
                let headers = {}
                let params = {}
                try {
                    if (this.edit_form.headers_json) {
                        headers = JSON.parse(this.edit_form.headers_json)
                    }
                } catch (e) {
                    alert('请求头 JSON 格式错误')
                    return
                }
                try {
                    if (this.edit_form.params_json) {
                        params = JSON.parse(this.edit_form.params_json)
                    }
                } catch (e) {
                    alert('请求参数 JSON 格式错误')
                    return
                }
                const payload = {
                    id: this.edit_form.is_create ? null : this.edit_form.id,
                    name: this.edit_form.name,
                    method: this.edit_form.method,
                    url: this.edit_form.url,
                    tag_id: this.edit_form.tag_id,
                    sort: this.edit_form.sort,
                    description: this.edit_form.description,
                    headers: headers,
                    params: params,
                }
                axios.post('http://172.16.2.60:8000/update_interface/', payload).then(res => {
                    if (res.data.code === 0) {
                        this.show_modal = false
                        this.get_list()
                    } else {
                        alert(res.data.message || '保存失败')
                    }
                }).catch(err => {
                    alert('请求失败: ' + err.message)
                })
            },
            soft_delete() {
                if (!confirm('确定要删除这个接口吗？')) return
                axios.post('http://172.16.2.60:8000/delete_interface/', {
                    id: this.edit_form.id
                }).then(res => {
                    if (res.data.code === 0) {
                        this.show_modal = false
                        this.get_list()
                    } else {
                        alert(res.data.message || '删除失败')
                    }
                })
            },
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
        width: 600px;
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
    .form-row {
        display: flex;
        align-items: center;
        margin-bottom: 12px;
    }
    .form-label-fixed {
        width: 90px;
        min-width: 90px;
        margin: 0;
        text-align: right;
        font-size: 14px;
    }
    .form-control, .form-select {
        flex: 1;
    }
</style>
