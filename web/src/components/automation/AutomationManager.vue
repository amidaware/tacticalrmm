<template>
  <div style="width: 900px; max-width: 90vw;">
    <q-card>
      <q-bar>
        <q-btn ref="refresh" @click="clearRow" class="q-mr-sm" dense flat push icon="refresh" />Automation Manager
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
            @click="showAddPolicyModal"
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
          class="settings-tbl-sticky"
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
              <q-td>
                <q-btn
                  :label="`See Related (${props.row.clients.length + props.row.sites.length + props.row.agents.length}+)`"
                  color="primary"
                  dense
                  flat
                  unelevated
                  no-caps
                  @click="showRelationsModal(props.row)"
                  size="sm"
                />
              </q-td>
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
    <q-dialog v-model="showRelationsViewModal">
      <RelationsView :policy="policy" @close="closeRelationsModal" />
    </q-dialog>
  </div>
</template>

<script>
import mixins from "@/mixins/mixins";
import { mapState } from "vuex";
import PolicyForm from "@/components/automation/modals/PolicyForm";
import PolicyOverview from "@/components/automation/PolicyOverview";
import PolicySubTableTabs from "@/components/automation/PolicySubTableTabs";
import RelationsView from "@/components/automation/modals/RelationsView";

export default {
  name: "AutomationManager",
  components: { PolicyForm, PolicyOverview, PolicySubTableTabs, RelationsView },
  mixins: [mixins],
  data() {
    return {
      showPolicyFormModal: false,
      showPolicyOverviewModal: false,
      showRelationsViewModal: false,
      policy: null,
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
          name: "actions",
          label: "Actions",
          field: "actions",
          align: "left",
          sortable: false
        }
      ],
      visibleColumns: ["name", "desc", "active", "actions"]
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
    clearRow() {
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
    },
    showRelationsModal(policy) {
      this.policy = policy;
      this.showRelationsViewModal = true;
    },
    closeRelationsModal() {
      this.policy = null;
      this.showRelationsViewModal = false;
    },
    showAddPolicyModal() {
      this.clearRow();
      this.showPolicyFormModal = true;
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