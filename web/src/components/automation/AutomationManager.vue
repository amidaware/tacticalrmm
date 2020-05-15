<template>
  <div style="width: 900px; max-width: 90vw;">
    <q-card>
      <q-bar>
        <q-btn
          ref="refresh"
          @click="clearRow"
          class="q-mr-sm"
          dense
          flat
          push
          icon="refresh"
        />Automation Manager
        <q-space />
        <q-btn dense flat icon="close" v-close-popup>
          <q-tooltip content-class="bg-white text-primary">Close</q-tooltip>
        </q-btn>
      </q-bar>
      <div class="q-pa-md">
        <div class="q-gutter-sm">
          <q-btn
            ref="new"
            label="New"
            dense
            flat
            push
            unelevated
            no-caps
            icon="add"
            @click="showPolicyFormModal = true;"
          />
          <q-btn
            ref="edit"
            label="Edit"
            :disable="selectedRow === null"
            dense
            flat
            push
            unelevated
            no-caps
            icon="edit"
            @click="showPolicyFormModal = true"
          />
          <q-btn
            ref="delete"
            label="Delete"
            :disable="selectedRow === null"
            dense
            flat
            push
            unelevated
            no-caps
            icon="delete"
            @click="deletePolicy"
          />
          <q-btn
            ref="overview"
            label="Policy Overview"
            dense
            flat
            push
            unelevated
            no-caps
            icon="remove_red_eye"
            @click="showPolicyOverviewModal = true"
          />
        </div>
        <q-table
          dense
          class="automation-sticky-header-table"
          :data="policies"
          :columns="columns"
          :visible-columns="visibleColumns"
          :pagination.sync="pagination"
          :selected.sync="selected"
          @selection="policyRowSelected"
          selection="single"
          row-key="id"
          binary-state-sort
          hide-bottom
          flat
        >
          <template v-slot:header="props">
            <q-tr :props="props">
              <q-th v-for="col in props.cols" :key="col.name" :props="props">{{ col.label }}</q-th>
            </q-tr>
          </template>
          <template v-slot:body="props">
            <q-tr :props="props" class="cursor-pointer" @click="props.selected = true">
              <q-td>{{ props.row.name }}</q-td>
              <q-td>{{ props.row.desc }}</q-td>
              <q-td>{{ props.row.active }}</q-td>
              <q-td>{{ props.row.clients.length }}</q-td>
              <q-td>{{ props.row.sites.length }}</q-td>
              <q-td>{{ props.row.agents.length }}</q-td>
            </q-tr>
          </template>
        </q-table>
      </div>

      <q-card-section>
        <PolicySubTableTabs :policypk="selectedRow" />
      </q-card-section>
    </q-card>
    <q-dialog v-model="showPolicyFormModal">
      <PolicyForm :pk="selectedRow" @close="showPolicyFormModal = false" @refresh="clearRow" />
    </q-dialog>
    <q-dialog v-model="showPolicyOverviewModal">
      <PolicyOverview @close="showPolicyOverviewModal = false" />
    </q-dialog>
  </div>
</template>

<script>
import mixins from "@/mixins/mixins";
import { mapState } from "vuex";
import PolicyForm from "@/components/automation/modals/PolicyForm";
import PolicyOverview from "@/components/automation/PolicyOverview";
import PolicySubTableTabs from "@/components/automation/PolicySubTableTabs";

export default {
  name: "AutomationManager",
  components: { PolicyForm, PolicyOverview, PolicySubTableTabs },
  mixins: [mixins],
  data() {
    return {
      showPolicyFormModal: false,
      showPolicyOverviewModal: false,
      selected: [],
      pagination: {
        rowsPerPage: 0,
        sortBy: "id",
        descending: false
      },
      columns: [
        { name: "id", label: "ID", field: "id" },
        {
          name: "name",
          label: "Name",
          field: "name",
          align: "left",
          sortable: true
        },
        {
          name: "desc",
          label: "Description",
          field: "desc",
          align: "left",
          sortable: false
        },
        {
          name: "active",
          label: "Active",
          field: "active",
          align: "left",
          sortable: true
        },
        {
          name: "clients",
          label: "Clients",
          field: "clients",
          align: "left",
          sortable: false
        },
        {
          name: "sites",
          label: "Sites",
          field: "sites",
          align: "left",
          sortable: false
        },
        {
          name: "agents",
          label: "Agents",
          field: "agents",
          align: "left",
          sortable: false
        }
      ],
      visibleColumns: ["name", "desc", "active", "clients", "sites", "agents"]
    };
  },
  methods: {
    getPolicies() {
      this.$store.dispatch("automation/loadPolicies");
    },
    policyRowSelected({ added, keys, rows }) {
      // First key of the array is the selected row pk
      this.$store.commit("automation/setSelectedPolicy", keys[0]);
      this.$store.dispatch("automation/loadPolicyChecks", keys[0]);
      this.$store.dispatch("automation/loadPolicyAutomatedTasks", keys[0]);
    },
    clearRow () {
      this.getPolicies();
      this.$store.commit("automation/setSelectedPolicy", null);
      this.$store.commit("automation/setPolicyChecks", {});
      this.$store.commit("automation/setPolicyAutomatedTasks", {});
    },
    deletePolicy() {
      this.$q
        .dialog({
          title: "Delete policy?",
          cancel: true,
          ok: { label: "Delete", color: "negative" }
        })
        .onOk(() => {
          this.$store
            .dispatch("automation/deletePolicy", this.selectedRow)
            .then(response => {
              this.notifySuccess(`Policy was deleted!`);
            })
            .catch(error => {
              this.notifyError(`An Error occured while deleting policy`);
            });
        });
    }
  },
  computed: {
    ...mapState({
      policies: state => state.automation.policies,
      selectedRow: state => state.automation.selectedPolicy
    })
  },
  mounted() {
    this.getPolicies();
  }
};
</script>

<style lang="stylus">
.automation-sticky-header-table {
  /* max height is important */
  .q-table__middle {
    max-height: 500px;
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
</style>