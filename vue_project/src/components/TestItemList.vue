<template>
    <div style="text-align: center;width: 100%;margin-top: 40px">
        <div v-for="group in groups" :key="group.second_tag_id" :id="'second-tag-' + group.second_tag_id" class="item-group">
            <div style="display: flex; align-items: center; margin-bottom: 15px">
                <div style="flex: 1"></div>
                <h5 style="margin: 0">{{ group.second_tag_name }}</h5>
                <div style="flex: 1; text-align: right; margin-right: 16px;">
                    <button class="btn btn-outline-primary btn-sm" @click="open_create(group.second_tag_id)" style="border: 0px">新建</button>
                </div>
            </div>
            <table class="table table-bordered table-hover" style="text-align: center; margin: 0 auto; font-size: 16px">
                <thead>
                    <tr>
                        <th style="width: 75px" @click="toggle_all(group)">
                            <input type="checkbox" class="form-check-input" :checked="is_all_selected(group)">
                        </th>
                        <th style="width: 40%">测试项名称</th>
                        <th style="width: 100px">项目类型</th>
                        <th>描述</th>
                        <th style="width: 75px">
                            <button class="btn btn-outline-secondary btn-sm" @click.stop="group.collapsed = !group.collapsed" style="border: 0px">
                                {{ group.collapsed ? '展开' : '收起' }}
                            </button>
                        </th>
                    </tr>
                </thead>
                <tbody v-show="!group.collapsed">
                    <tr v-for="item in group.test_items" :key="item.id" @click="toggle(item.id)">
                        <td><input type="checkbox" class="form-check-input" :value="item.id" v-model="checked_ids" @change="up_checked" @click.stop></td>
                        <td style="text-align: left; padding-left: 16px">{{ item.name }} <span v-if="item.type === 2" class="script-badge">[Script]</span></td>
                        <td>{{ type_name(item.type) }}</td>
                        <td>{{ item.description }}</td>
                        <td @click.stop><button class="btn btn-outline-primary btn-sm" @click="open_edit(item)" style="border: 0px">编辑</button></td>
                    </tr>
                    <tr v-if="group.test_items.length === 0">
                        <td colspan="5" style="color: gray; font-size: 16px">暂无测试项</td>
                    </tr>
                </tbody>
            </table>
        </div>

        <!-- 编辑模态框 -->
        <div v-if="show_modal" class="modal-overlay" @click.self="show_modal = false">
            <div class="edit-modal-box" style="width: 900px">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">{{ edit_form.is_create ? '新建测试项' : '编辑测试项' }}</h5>
                        <button type="button" class="btn-close" @click="show_modal = false"></button>
                    </div>
                    <div class="modal-body">
                        <div class="form-row">
                            <label class="form-label-fixed">名 称：</label>
                            <input type="text" class="form-control" v-model="edit_form.name">
                        </div>
                        <div class="form-row">
                            <label class="form-label-fixed">项目类型：</label>
                            <select class="form-select" v-model="edit_form.type">
                                <option :value="1">单接口用例</option>
                                <option :value="2">自定义脚本</option>
                            </select>
                        </div>
                        <div v-if="edit_form.is_create" class="form-row">
                            <label class="form-label-fixed">二级标签：</label>
                            <select class="form-select" v-model="edit_form.second_tag_id">
                                <option v-for="tag in second_tags" :key="tag.id" :value="tag.id">{{ tag.name }}</option>
                            </select>
                        </div>
                        <div v-if="edit_form.type === 1" class="form-row">
                            <label class="form-label-fixed">关联接口：</label>
                            <select class="form-select" v-model="edit_form.interface_id">
                                <option :value="null">无</option>
                                <option v-for="iface in interfaces" :key="iface.id" :value="iface.id">{{ iface.name }}</option>
                            </select>
                        </div>
                        <div class="form-row">
                            <label class="form-label-fixed">描 述：</label>
                            <input class="form-control" rows="2" v-model="edit_form.description"></input>
                        </div>
                        <div v-if="edit_form.type === 1" class="form-row">
                            <label class="form-label-fixed">测试JSON：</label>
                            <textarea class="form-control" rows="6" v-model="edit_form.cases_json" style="width: 744px;"></textarea>
                        </div>
                        <div v-if="edit_form.type === 2" class="form-row">
                            <label class="form-label-fixed">上传脚本：</label>
                            <div style="flex: 1; display: flex; gap: 8px; align-items: center">
                                <input type="file" class="form-control" accept=".py" ref="scriptInput" @change="upload_script" style="flex: 1">
                            </div>
                        </div>
                        <div v-if="edit_form.type === 2 && edit_form.script_filename" class="form-row">
                            <label class="form-label-fixed"></label>
                            <div style="flex: 1; text-align: left; font-size: 13px; color: #666">
                                已上传: {{ edit_form.script_filename }}
                            </div>
                        </div>
                        <div v-if="edit_form.type === 1" class="form-row">
                            <label class="form-label-fixed">上传用例：</label>
                            <div style="flex: 1; display: flex; gap: 8px; align-items: center">
                                <input type="file" class="form-control" accept=".xlsx" ref="fileInput" @change="upload_file" style="flex: 1">
                            </div>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button v-if="!edit_form.is_create" type="button" class="btn btn-danger" style="margin-right: auto" @click="soft_delete">删除测试项</button>
                        <button type="button" class="btn btn-secondary" @click="show_modal = false">取消</button>
                        <button type="button" class="btn btn-primary" @click="save_edit">保存</button>
                    </div>
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
                groups: [],
                checked_ids: [],
                interfaces: [],
                second_tags: [],
                show_modal: false,
                edit_form: {
                    id: null,
                    is_create: false,
                    second_tag_id: null,
                    name: '',
                    type: 1,
                    description: '',
                    interface_id: null,
                    cases_json: '',
                    uploaded_filename: '',
                    script_filename: '',
                    uploaded_script: '',
                },
            }
        },
        mounted:function () {
            this.get_groups()
            this.get_interfaces()
            this.get_second_tags()
        },
        methods:{
            get_groups(){
                const tag_id = this.$route.params.tag_id;
                axios.get('http://127.0.0.100:8000/get_grouped_test_items/', {
                    params: {first_tag_id: tag_id}
                }).then(res=>{
                    this.groups = res.data.groups.map(g => ({...g, collapsed: false}));
                    this.checked_ids = [];
                })
            },
            get_interfaces(){
                axios.get('http://127.0.0.100:8000/get_interfaces/').then(res => {
                    this.interfaces = res.data.interfaces || [];
                })
            },
            get_second_tags(){
                const tag_id = this.$route.params.tag_id;
                axios.get('http://127.0.0.100:8000/get_second_tags/', {
                    params: {first_tag_id: tag_id}
                }).then(res => {
                    this.second_tags = res.data.second_tags || [];
                })
            },
            type_name(type){
                const map = {1: '单接口用例', 2: '自定义脚本'}
                return map[type] || '未知'
            },
            is_all_selected(group){
                if (group.test_items.length === 0) return false
                return group.test_items.every(item => this.checked_ids.includes(item.id))
            },
            toggle_all(group){
                const ids = group.test_items.map(item => item.id)
                if (this.is_all_selected(group)) {
                    this.checked_ids = this.checked_ids.filter(id => !ids.includes(id))
                } else {
                    this.checked_ids = [...new Set([...this.checked_ids, ...ids])]
                }
                this.up_checked()
            },
            toggle(id){
                if (this.checked_ids.includes(id)) {
                    this.checked_ids = this.checked_ids.filter(i => i !== id)
                } else {
                    this.checked_ids.push(id)
                }
                this.up_checked()
            },
            up_checked(){
                const checked_names = this.get_checked_names();
                this.$emit('upItems', {checked_ids: this.checked_ids, checked_names: checked_names, count: this.checked_ids.length})
                // 通过 event bus 直接通知 run_list（绕开 prop 响应性 HMR 问题）
                bus.$emit('items:changed', {
                    ids: this.checked_ids.slice(),
                    names: checked_names.slice(),
                })
            },
            get_checked_names(){
                const names = [];
                for (const group of this.groups) {
                    for (const item of group.test_items) {
                        if (this.checked_ids.includes(item.id)) {
                            names.push(item.name)
                        }
                    }
                }
                return names
            },
            open_edit(item){
                axios.get('http://127.0.0.100:8000/get_test_item_detail/', {
                    params: {id: item.id}
                }).then(res => {
                    if (res.data.code === 0) {
                        const d = res.data.data;
                        this.edit_form = {
                            id: d.id,
                            is_create: false,
                            second_tag_id: null,
                            name: d.name,
                            type: d.type,
                            description: d.description,
                            interface_id: d.interface_id,
                            cases_json: JSON.stringify(d.cases, null, 2),
                            uploaded_filename: '',
                            script_filename: d.script_filename || '',
                            uploaded_script: '',
                        };
                        this.show_modal = true;
                    } else {
                        alert(res.data.message || '获取详情失败');
                    }
                })
            },
            open_create(second_tag_id){
                this.edit_form = {
                    id: null,
                    is_create: true,
                    second_tag_id: second_tag_id,
                    name: '',
                    type: 1,
                    description: '',
                    interface_id: null,
                    cases_json: '',
                    uploaded_filename: '',
                    script_filename: '',
                    uploaded_script: '',
                };
                this.show_modal = true;
            },
            upload_file(){
                const fileInput = this.$refs.fileInput;
                if (!fileInput || !fileInput.files || fileInput.files.length === 0) {
                    return;
                }
                const formData = new FormData();
                formData.append('fileUpload', fileInput.files[0]);
                axios.post('http://127.0.0.100:8000/upload_case/', formData, {
                    headers: {'Content-Type': 'multipart/form-data'}
                }).then(res => {
                    if (res.data.cases) {
                        this.edit_form.cases_json = JSON.stringify(res.data.cases, null, 2);
                        this.edit_form.uploaded_filename = res.data.filename || '';
                    } else {
                        alert(res.data.msg || '解析失败');
                    }
                }).catch(err => {
                    alert('上传失败: ' + (err.response?.data?.msg || err.message));
                })
            },
            upload_script(){
                const scriptInput = this.$refs.scriptInput;
                if (!scriptInput || !scriptInput.files || scriptInput.files.length === 0) {
                    return;
                }
                const formData = new FormData();
                formData.append('fileUpload', scriptInput.files[0]);
                axios.post('http://127.0.0.100:8000/upload_script/', formData, {
                    headers: {'Content-Type': 'multipart/form-data'}
                }).then(res => {
                    if (res.data.filename) {
                        this.edit_form.script_filename = res.data.filename;
                        this.edit_form.uploaded_script = res.data.filename;  // 标记本次新上传
                    } else {
                        alert(res.data.msg || '上传失败');
                    }
                }).catch(err => {
                    alert('上传失败: ' + (err.response?.data?.msg || err.message));
                })
            },
            clear_script(){
                this.edit_form.script_filename = '';
                this.edit_form.uploaded_script = '';
                if (this.$refs.scriptInput) {
                    this.$refs.scriptInput.value = '';
                }
            },
            clear_file(){
                this.edit_form.uploaded_filename = '';
                if (this.$refs.fileInput) {
                    this.$refs.fileInput.value = '';
                }
            },
            save_edit(){
                let cases = [];
                if (this.edit_form.cases_json) {
                    try {
                        cases = JSON.parse(this.edit_form.cases_json);
                    } catch (e) {
                        alert('用例 JSON 格式错误');
                        return;
                    }
                }
                const isScript = this.edit_form.type === 2;
                const payload = {
                    id: this.edit_form.is_create ? null : this.edit_form.id,
                    second_tag_id: this.edit_form.second_tag_id,
                    name: this.edit_form.name,
                    type: this.edit_form.type,
                    description: this.edit_form.description,
                    // type=1 传接口和用例，type=2 置空
                    interface_id: isScript ? null : this.edit_form.interface_id,
                    cases: isScript ? [] : cases,
                    // type=1 传 xlsx，type=2 传脚本
                    uploaded_filename: isScript ? '' : this.edit_form.uploaded_filename,
                    uploaded_script: isScript ? this.edit_form.uploaded_script : '',
                };
                axios.post('http://127.0.0.100:8000/update_test_item/', payload).then(res => {
                    if (res.data.code === 0) {
                        this.show_modal = false;
                        this.get_groups();
                    } else {
                        alert(res.data.message || '保存失败');
                    }
                }).catch(err => {
                    alert('请求失败: ' + err.message);
                })
            },
            soft_delete(){
                if (!confirm('确定要删除这个测试项吗？')) return;
                axios.post('http://127.0.0.100:8000/update_test_item/', {
                    id: this.edit_form.id,
                    is_del: true
                }).then(res => {
                    if (res.data.code === 0) {
                        this.show_modal = false;
                        this.get_groups();
                    } else {
                        alert(res.data.message || '删除失败');
                    }
                }).catch(err => {
                    alert('请求失败: ' + err.message);
                })
            },
        },
        watch:{
            '$route'(){
                this.get_groups()
            }
        }
    }
</script>

<style scoped>
    .item-group{
        margin-bottom: 80px;
    }
    .modal-overlay{
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0,0,0,0.5);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 9999;
    }
    .form-row{
        display: flex;
        align-items: center;
        margin-bottom: 12px;
        gap: 12px;
    }
    .form-label-fixed{
        width: 110px;
        min-width: 110px;
        margin: 0;
        text-align: middle;
        font-size: 16px;
    }
    .script-badge{
        color: #0d6efd;
        font-size: 12px;
        font-weight: 600;
        margin-left: 6px;
    }
</style>