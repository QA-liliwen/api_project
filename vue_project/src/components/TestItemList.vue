<template>
    <div style="text-align: center;width: 100%;margin-top: 40px">
        <div v-for="group in groups" :key="group.second_tag_id" class="item-group">
            <h5 style="margin-bottom: 15px">{{ group.second_tag_name }}</h5>
            <table class="table table-bordered table-hover" style="text-align: center; margin: 0 auto">
                <thead>
                    <tr>
                        <th style="width: 75px">选择</th>
                        <th style="width: 40%">测试项名称</th>
                        <th style="width: 100px">项目类型</th>
                        <th>描述</th>
                        <th style="width: 75px">操作</th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="item in group.test_items" :key="item.id">
                        <td><input type="checkbox" class="form-check-input" :value="item.id" v-model="checked_ids" @change="up_checked"></td>
                        <td>{{ item.name }}</td>
                        <td>{{ type_name(item.type) }}</td>
                        <td>{{ item.description }}</td>
                        <td><button>编辑</button></td>
                    </tr>
                    <tr v-if="group.test_items.length === 0">
                        <td colspan="5" style="color: gray">暂无测试项</td>
                    </tr>
                </tbody>
            </table>
        </div>
    </div>
</template>

<script>
    import axios from 'axios'
    export default {
        data(){
            return{
                groups: [],
                checked_ids: [],
            }
        },
        mounted:function () {
            this.get_groups()
        },
        methods:{
            get_groups(){
                const tag_id = this.$route.params.tag_id;
                axios.get('http://localhost:8000/get_grouped_test_items/', {
                    params: {first_tag_id: tag_id}
                }).then(res=>{
                    this.groups = res.data.groups;
                    this.checked_ids = [];
                })
            },
            type_name(type){
                const map = {1: '单接口用例', 2: '多接口编排', 3: '自定义脚本'}
                return map[type] || '未知'
            },
            up_checked(){
                this.$emit('upItems', {checked_ids: this.checked_ids, count: this.checked_ids.length})
            }
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
</style>