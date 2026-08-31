<template>
  <div>
    <TopMenu></TopMenu>
    <RunResultList></RunResultList>
  </div>
</template>

<script>
import TopMenu from '../components/TopMenu.vue'
import RunResultList from '../components/RunResultList.vue'

export default {
  name: 'RunResultView',
  components: {
    TopMenu,
    RunResultList
  }
}
</script>
