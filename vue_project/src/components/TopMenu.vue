<template>
  <nav class="navbar navbar-expand-sm navbar-light border-bottom" style="padding: 0">
    <div class="container-fluid">
      <div class="collapse navbar-collapse" id="topMenuCollapse">
        <ul class="navbar-nav" style="margin-left: 40px">
          <li class="nav-item" v-for="tag in first_tags" :key="tag.id">
            <a class="nav-link" style="color: black;margin-right: 20px;font-size: 20px" href="#" @click.prevent="select_tag(tag)"
             :class="{active: String(tag.id) === active_tag_id}">{{ tag.name }}</a>
          </li>
          <li class="nav-item">
            <a class="nav-link" style="color: black;margin-right: 20px;font-size: 20px" href="#" @click.prevent="$router.push('/interfaces/')"
             :class="{active: $route.path === '/interfaces/'}">接口列表</a>
          </li>
          <li class="nav-item">
            <a class="nav-link" style="color: black;margin-right: 20px;font-size: 20px" href="#" @click.prevent="$router.push('/run_results/')"
             :class="{active: $route.path === '/run_results/'}">测试结果</a>
          </li>
        </ul>
        <ul class="navbar-nav ms-auto">
          <li class="nav-item">
            <a class="nav-link" href="http://127.0.0.100:8000/admin/" target="_blank">后台</a>
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
            axios.get('http://127.0.0.100:8000/get_top_menu/').then(res=>{
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
    .nav-link.active {
        color: #0d6efd !important;
        border-bottom: 2px solid #0d6efd;
    }
</style>
