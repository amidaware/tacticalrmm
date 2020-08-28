<template>
  <div id="q-app">
    <router-view />
  </div>
</template>

<script>
export default {
  name: "App",
};
</script>

<style lang="sass">
.tabs-tbl-sticky

  .q-table__top,
  .q-table__bottom,
  thead tr:first-child th
    background-color: #f5f4f2

  thead tr th
    position: sticky
    z-index: 1
  thead tr:first-child th
    top: 0

.remote-bg-tbl-sticky
  max-height: 70vh

  .q-table__top,
  .q-table__bottom,
  thead tr:first-child th
    background-color: #f5f4f2

  thead tr th
    position: sticky
    z-index: 1
  thead tr:first-child th
    top: 0

.settings-tbl-sticky
  max-height: 60vh

  .q-table__top,
  .q-table__bottom,
  thead tr:first-child th
    background-color: #CBCBCB

  thead tr th
    position: sticky
    z-index: 1
  thead tr:first-child th
    top: 0

.agents-tbl-sticky

  .q-table__top,
  .q-table__bottom,
  thead tr:first-child th
    background-color: #f5f4f2

  thead tr th
    position: sticky
    z-index: 1
  thead tr:first-child th
    top: 0

.highlight
  background-color: #c9e6ff

.action-completed
  background-color: #baf5cc

.agent-offline
  background: gray !important

.agent-overdue
  background: red !important
</style>