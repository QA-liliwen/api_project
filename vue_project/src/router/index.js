import Vue from 'vue'
import VueRouter from 'vue-router'
import HomeView from '../views/HomeView.vue'

Vue.use(VueRouter)

const routes = [
  {
    path: '/api_list/:tag_id/',
    name: 'home',
    component: HomeView
  },
  {
    path: '/api_list/',
    redirect: '/api_list/1/'
  }
]

const router = new VueRouter({
  mode: 'history',
  routes
})

export default router