<template>
  <div v-if="!this.selectedAgentPk">No agent selected</div>
  <div v-else-if="!Array.isArray(software) || !software.length">No software</div>
  <div v-else>
    <q-btn
      size="sm"
      color="grey-5"
      icon="fas fa-plus"
      label="Install Software"
      text-color="black"
      @click="showInstallSoftware = true"
    />
    <q-btn dense flat push @click="refreshSoftware" icon="refresh" />
    <q-table
      class="tabs-tbl-sticky"
      dense
      :data="software"
      :columns="columns"
      :pagination.sync="pagination"
      binary-state-sort
      hide-bottom
      row-key="name"
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
    InstallSoftware
  },
  mixins: [mixins],
  data() {
    return {
      showInstallSoftware: false,
      loading: false,
      pagination: {
        rowsPerPage: 0,
        sortBy: "name",
        descending: false
      },
      columns: [
        {
          name: "name",
          align: "left",
          label: "Name",
          field: "name",
          sortable: true
        },
        {
          name: "version",
          align: "left",
          label: "Version",
          field: "version",
          sortable: false
        }
      ]
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
    }
  },
  computed: {
    ...mapGetters(["selectedAgentPk"]),
    ...mapState({
      software: state => state.installedSoftware
    })
  }
};
</script>

