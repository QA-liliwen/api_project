import Vue from 'vue'
import VueRouter from 'vue-router'
import HomeView from '../views/HomeView.vue'
import InterfaceView from '../views/InterfaceView.vue'
import RunResultView from '../views/RunResultView.vue'
import ToolsView from '../views/ToolsView.vue'

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
    path: '/tools/:tool_key/',
    name: 'tools',
    component: ToolsView
  },
  {
    path: '/tools/',
    name: 'tools_index',
    component: ToolsView
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