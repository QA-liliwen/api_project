import Vue from 'vue'
import VueRouter from 'vue-router'
import HomeView from '../views/HomeView.vue'
import InterfaceView from '../views/InterfaceView.vue'
import RunResultView from '../views/RunResultView.vue'

Vue.use(VueRouter)

const routes = [
  {
    path: '/api_list/:tag_id/',
    name: 'home',
    component: HomeView
  },
  {
    path: '/interfaces/',
    name: 'interfaces',
    component: InterfaceView
  },
  {
    path: '/run_results/',
    name: 'run_results',
    component: RunResultView
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