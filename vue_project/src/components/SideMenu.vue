<template>
    <div class="list-group">
        <a href="#" class="list-group-item list-group-item-action"
           v-for="tag in second_tags" :key="tag.id"
           @click.prevent="select_second(tag)"
           :class="{active: tag.id === active_second_id}">{{ tag.name }}</a>
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
                axios.get('http://localhost:8000/get_second_tags/', {
                    params: {first_tag_id: tag_id}
                }).then(res=>{
                    this.second_tags = res.data.second_tags;
                    this.active_second_id = null;
                })
            },
            select_second(tag){
                this.active_second_id = tag.id;
                this.$emit('upSecond', {second_tag_id: tag.id, second_tag_name: tag.name})
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
        width: 200px;
    }
</style>