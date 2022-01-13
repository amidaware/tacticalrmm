<template>
  <q-btn dense color="primary" icon-right="archive" @click="exportTable">
    <q-tooltip>Export table as CSV</q-tooltip>
  </q-btn>
</template>

<script>
import { exportTableToCSV } from "@/utils/csv";

export default {
  name: "export-table-btn",
  props: {
    columns: !Array,
    data: !Array,
  },
  setup(props) {
    return {
      exportTable: () => exportTableToCSV(props.data, props.columns),
    };
  },
};
</script>