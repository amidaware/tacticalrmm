<template>
  <div id="q-app">
    <router-view />
  </div>
</template>

<script>
export default {
  name: "App"
};
</script>

<style lang="stylus">
.tabs-tbl-sticky {
  .q-table__middle {
    max-height: 25vh;
  }

  .q-table__top, .q-table__bottom, thead tr:first-child th {
    background-color: #f5f4f2;
  }

  thead tr:first-child th {
    position: sticky;
    top: 0;
    opacity: 1;
    z-index: 1;
  }
}

.remote-bg-tbl-sticky {
  .q-table__middle {
    max-height: 70vh;
  }

  .q-table__top, .q-table__bottom, thead tr:first-child th {
    background-color: #f5f4f2;
  }

  thead tr:first-child th {
    position: sticky;
    top: 0;
    opacity: 1;
    z-index: 1;
  }
}

.settings-tbl-sticky {
  .q-table__middle {
    max-height: 60vh;
  }

  .q-table__top, .q-table__bottom, thead tr:first-child th {
    background-color: #CBCBCB;
  }

  thead tr:first-child th {
    position: sticky;
    top: 0;
    opacity: 1;
    z-index: 1;
  }
}

.agents-tbl-sticky {
  .q-table__middle {
    max-height: 35vh;
  }

  .q-table__top, .q-table__bottom, thead tr:first-child th {
    background-color: #f5f4f2;
  }

  thead tr:first-child th {
    position: sticky;
    top: 0;
    opacity: 1;
    z-index: 1;
  }
}

.highlight {
  background-color: #c9e6ff;
}

.action-completed {
  background-color: #baf5cc;
}

.agent-offline {
  background: gray !important;
}

.agent-overdue {
  background: red !important;
}
</style>