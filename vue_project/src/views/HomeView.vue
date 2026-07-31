<template>
  <div class="home">
    <TopMenu></TopMenu>
    <div class="d-flex">
      <div class="p-2" style="width: 20%">
        <SideMenu @upSecond="upSecond"></SideMenu>
      </div>
      <div class="p-2 flex-grow-1" style="width: 60%">
        <TestItemList @upItems="upItems"></TestItemList>
      </div>
      <div class="p-2 flex-grow-1" style="width: 20%">
<!--        <TestItemList @upItems="upItems"></TestItemList>-->
      </div>
    </div>
  </div>
</template>

<script>
import TopMenu from '../components/TopMenu.vue'
import SideMenu from '../components/SideMenu.vue'
import TestItemList from '../components/TestItemList.vue'

export default {
  name: 'HomeView',
  components: {
    TopMenu,
    SideMenu,
    TestItemList
  },
  methods: {
    upSecond(e) {
      console.log('选中的二级标签：', e.second_tag_id, e.second_tag_name)
    },
    upItems(e) {
      console.log('勾选的测试项：', e.checked_ids, '共', e.count, '个')
    }
  }
}
</script>