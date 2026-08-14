<template>
  <nav class="navbar navbar-expand-sm navbar-light border-bottom" style="padding: 0">
    <div class="container-fluid">
      <div class="collapse navbar-collapse" id="topMenuCollapse">
        <ul class="navbar-nav mx-auto">
          <li class="nav-item" v-for="tag in first_tags" :key="tag.id">
            <a class="nav-link" style="margin-right: 20px;font-size: 20px" href="#" @click.prevent="select_tag(tag)"
             :class="{active: tag.id === active_tag_id}">{{ tag.name }}</a>
          </li>
        </ul>
        <ul class="navbar-nav">
          <li class="nav-item">
            <a class="nav-link" href="http://127.0.0.1:8000/admin/" target="_blank">后台</a>
          </li>
        </ul>
      </div>
    </div>
  </nav>
</template>

<script>
    import axios from 'axios'
    export default {
        data(){
            return{
                first_tags: [],
                active_tag_id: null,
            }
        },
        mounted:function () {
            this.active_tag_id = this.$route.params.tag_id;
            axios.get('http://localhost:8000/get_top_menu/').then(res=>{
                this.first_tags = res.data.first_tags;
            })
        },
        methods:{
            select_tag(tag){
                const path = '/api_list/' + tag.id + '/'
                if (this.$route.path !== path) {
                    this.$router.push(path)
                }
            }
        },
        watch: {
          '$route'(to) {
            this.active_tag_id = to.params.tag_id;
          }
        }
    }
</script>

<style scoped>
</style>
