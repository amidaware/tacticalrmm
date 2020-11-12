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

.audit-mgr-tbl-sticky
  max-height: 75vh

  thead tr th
    position: sticky
    z-index: 1
  thead tr:first-child th
    top: 0

.settings-tbl-sticky
  max-height: 60vh

  thead tr th
    position: sticky
    z-index: 1
  thead tr:first-child th
    top: 0

.agents-tbl-sticky

  thead tr th
    position: sticky
    z-index: 1
  thead tr:first-child th
    top: 0

.table-bgcolor
  .q-table__top,
  .q-table__bottom,
  thead tr:first-child th
    background-color: #f5f4f2

.table-bgcolor-dark
  .q-table__top,
  .q-table__bottom,
  thead tr:first-child th
    background-color: #1d1d1d

.highlight
  background-color: #c9e6ff

.highlight-dark
  background-color: #343434

.action-completed
  background-color: $positive

.agent-offline
  background: gray !important

.agent-overdue
  background: red !important
</style>