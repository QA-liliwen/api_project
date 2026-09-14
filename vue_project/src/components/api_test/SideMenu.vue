<template>
    <div class="list-group">
        <a href="#" class="list-group-item list-group-item-action"
           v-for="tag in second_tags" :key="tag.id"
           @click.prevent="select_second(tag)">{{ tag.name }}</a>
    </div>
</template>

<script>
    import axios from 'axios'
    export default {
        data(){
            return{
                second_tags: [],
                active_second_id: null,
            }
        },
        mounted:function () {
            this.get_second_tags()
        },
        methods:{
            get_second_tags(){
                const tag_id = this.$route.params.tag_id;
                axios.get('http://172.16.2.60:8000/get_second_tags/', {
                    params: {first_tag_id: tag_id}
                }).then(res=>{
                    this.second_tags = res.data.second_tags;
                    this.active_second_id = null;
                })
            },
            select_second(tag){
                this.active_second_id = tag.id;
                this.$emit('upSecond', {second_tag_id: tag.id, second_tag_name: tag.name})
                const el = document.getElementById('second-tag-' + tag.id);
                if (el) {
                    el.scrollIntoView({behavior: 'smooth', block: 'start'});
                }
            }
        },
        watch:{
            '$route'(){
                this.get_second_tags()
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
    .list-group-item{
        font-size: 16px;
        border: none;
        border-radius: 0;
    }
</style>