<template>
    <div class="list-group">
        <div v-for="group in groups" :key="group.category">
            <div class="group-title">{{ group.category }}</div>
            <a href="#" class="list-group-item list-group-item-action"
               v-for="tool in group.tools" :key="tool.tool_key"
               :class="{active: tool.tool_key === active_tool_key}"
               @click.prevent="select_tool(tool)">{{ tool.name }}</a>
        </div>
        <div v-if="groups.length === 0" style="padding: 10px; color: gray; font-size: 14px">暂无工具</div>
    </div>
</template>

<script>
    import api from '../api'
    export default {
        data(){
            return{
                groups: [],
            }
        },
        computed:{
            active_tool_key(){
                return this.$route.params.tool_key || ''
            }
        },
        mounted:function () {
            this.get_tools()
        },
        methods:{
            get_tools(){
                api.get('/get_tools/').then(res=>{
                    this.groups = res.data.groups || [];
                    this.$emit('upTools', this.groups);
                    // 未指定工具时自动落到第一个
                    if (!this.active_tool_key) {
                        const first = this.first_tool();
                        if (first) {
                            this.$router.replace('/tools/' + first.tool_key + '/');
                        }
                    }
                }).catch(()=>{})
            },
            first_tool(){
                for (const group of this.groups) {
                    if (group.tools.length > 0) {
                        return group.tools[0];
                    }
                }
                return null;
            },
            select_tool(tool){
                if (tool.tool_key === this.active_tool_key) {
                    return;
                }
                this.$router.push('/tools/' + tool.tool_key + '/');
            }
        }
    }
</script>

<style scoped>
    .list-group{
        width: 18%;
        margin-top: 20px;
        padding: 15px 0;
        position: fixed;
        top: 40px;
        left: 1%;
    }
    .group-title{
        padding: 8px 12px 4px;
        font-size: 13px;
        color: #888;
    }
    .list-group-item{
        font-size: 16px;
        border: none;
        border-radius: 0;
    }
</style>
