<template>
  <div v-if="!this.selectedAgentPk">No agent selected</div>
  <div v-else>
    <div class="row q-pt-xs items-start">
      <q-btn
        size="xs"
        color="grey-5"
        icon="fas fa-plus"
        label="Install Software"
        text-color="black"
        @click="showInstallSoftware = true"
      />
      <q-btn dense flat push @click="refreshSoftware" icon="refresh" />
      <q-space />
      <q-input v-model="filter" outlined label="Search" dense clearable>
        <template v-slot:prepend>
          <q-icon name="search" color="primary" />
        </template>
      </q-input>
    </div>

    <q-table
      :table-class="{ 'table-bgcolor': !$q.dark.isActive, 'table-bgcolor-dark': $q.dark.isActive }"
      class="tabs-tbl-sticky"
      :style="{ 'max-height': tabsTableHeight }"
      dense
      :data="software"
      :columns="columns"
      :filter="filter"
      :pagination.sync="pagination"
      binary-state-sort
      hide-bottom
      row-key="id"
      :loading="loading"
    >
      <template v-slot:loading>
        <q-inner-loading showing color="primary" />
      </template>
    </q-table>

    <q-dialog v-model="showInstallSoftware">
      <InstallSoftware @close="showInstallSoftware = false" :agentpk="selectedAgentPk" />
    </q-dialog>
  </div>
</template>

<script>
import axios from "axios";
import mixins from "@/mixins/mixins";
import { mapGetters } from "vuex";
import { mapState } from "vuex";
import InstallSoftware from "@/components/modals/software/InstallSoftware";
export default {
  name: "SoftwareTab",
  components: {
    InstallSoftware,
  },
  mixins: [mixins],
  data() {
    return {
      showInstallSoftware: false,
      loading: false,
      filter: "",
      pagination: {
        rowsPerPage: 0,
        sortBy: "name",
        descending: false,
      },
      columns: [
        {
          name: "name",
          align: "left",
          label: "Name",
          field: "name",
          sortable: true,
        },
        {
          name: "publisher",
          align: "left",
          label: "Publisher",
          field: "publisher",
          sortable: true,
        },
        {
          name: "install_date",
          align: "left",
          label: "Installed On",
          field: "install_date",
          sortable: false,
        },
        {
          name: "size",
          align: "left",
          label: "Size",
          field: "size",
          sortable: false,
        },
        {
          name: "version",
          align: "left",
          label: "Version",
          field: "version",
          sortable: false,
        },
      ],
    };
  },
  methods: {
    refreshSoftware() {
      const pk = this.selectedAgentPk;
      this.loading = true;
      axios
        .get(`/software/refresh/${pk}`)
        .then(r => {
          this.$store.dispatch("loadInstalledSoftware", pk);
          this.loading = false;
        })
        .catch(e => {
          this.loading = false;
          this.notifyError(e.response.data);
        });
    },
  },
  computed: {
    ...mapGetters(["selectedAgentPk", "tabsTableHeight"]),
    ...mapState({
      software: state => state.installedSoftware,
    }),
  },
};
</script>

