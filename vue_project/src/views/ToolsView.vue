<template>
  <div>
    <TopMenu></TopMenu>
    <ToolSideMenu @upTools="on_tools"></ToolSideMenu>
    <div class="tool-content">
      <div v-if="current_tool" style="margin-bottom: 15px">
        <h5 style="margin: 0">{{ current_tool.name }}</h5>
        <div v-if="current_tool.description" style="color: #888; font-size: 13px; margin-top: 6px">
          {{ current_tool.description }}
        </div>
      </div>
      <component v-if="tool_component" :is="tool_component" :key="tool_key"></component>
      <div v-else-if="tool_key" style="color: gray; padding: 20px 0">该工具前端开发中</div>
      <div v-else style="color: gray; padding: 20px 0">请从左侧选择工具</div>
    </div>
  </div>
</template>

<script>
import TopMenu from '../components/TopMenu.vue'
import ToolSideMenu from '../components/ToolSideMenu.vue'
import TOOL_COMPONENTS from '../components/tools/index.js'

export default {
  name: 'ToolsView',
  components: {
    TopMenu,
    ToolSideMenu,
    // 映射表里的工具组件按 tool_key 作为组件名注册，异步加载
    ...TOOL_COMPONENTS
  },
  data(){
    return{
      groups: [],
    }
  },
  computed:{
    tool_key(){
      return this.$route.params.tool_key || ''
    },
    // 映射表里没有该 key 时返回空，由模板渲染占位提示
    tool_component(){
      return TOOL_COMPONENTS[this.tool_key] ? this.tool_key : ''
    },
    // 工具的名称与说明来自数据库，由左侧菜单加载后回传
    current_tool(){
      for (const group of this.groups) {
        for (const tool of group.tools) {
          if (tool.tool_key === this.tool_key) {
            return tool;
          }
        }
      }
      return null;
    }
  },
  methods:{
    on_tools(groups){
      this.groups = groups;
    }
  }
}
</script>

<style scoped>
  .tool-content{
    margin-left: 20%;
    margin-right: 2%;
    padding: 20px 15px;
  }
</style>
