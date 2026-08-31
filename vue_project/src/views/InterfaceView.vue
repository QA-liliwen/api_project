<template>
  <div>
    <TopMenu></TopMenu>
    <InterfaceList></InterfaceList>
  </div>
</template>

<script>
import TopMenu from '../components/TopMenu.vue'
import InterfaceList from '../components/InterfaceList.vue'

export default {
  name: 'InterfaceView',
  components: {
    TopMenu,
    InterfaceList
  }
}
</script>
