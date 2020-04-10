<template>
  <div class="q-pa-md q-gutter-sm">
    <q-dialog :value="toggleAutomationManager" @hide="hideAutomationManager" @show="getPolicies">
      <q-card style="width: 900px; max-width: 90vw;">
        <q-bar>
          <q-btn @click="getPolicies" class="q-mr-sm" dense flat push icon="refresh" />Automation Manager
          <q-space />
          <q-btn dense flat icon="close" v-close-popup>
            <q-tooltip content-class="bg-white text-primary">Close</q-tooltip>
          </q-btn>
        </q-bar>
        <div class="q-pa-md">
          <div class="q-gutter-sm">
            <q-btn
              label="New"
              dense
              flat
              push
              unelevated
              no-caps
              icon="add"
              @click="showAddPolicyModal = true; clearRow"
            />
            <q-btn
              label="Edit"
              :disable="selectedRow === null"
              dense
              flat
              push
              unelevated
              no-caps
              icon="edit"
              @click="showEditPolicyModal = true"
            />
            <q-btn
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
            row-key="id"
            binary-state-sort
            hide-bottom
            virtual-scroll
            flat
            :rows-per-page-options="[0]"
          >
            <template slot="body" slot-scope="props" :props="props">
              <q-tr
                :class="{highlight: selectedRow === props.row.id}"
                @click="policyRowSelected(props.row.id)"
              >
                <q-td>{{ props.row.name }}</q-td>
                <q-td>{{ props.row.desc }}</q-td>
                <q-td>{{ props.row.applied_to }}</q-td>
                <q-td>{{ props.row.actions }}</q-td>
              </q-tr>
            </template>
          </q-table>
        </div>
        <q-card-section></q-card-section>
        <q-separator />
        <q-card-section></q-card-section>
      </q-card>
    </q-dialog>
    <q-dialog v-model="showAddPolicyModal">
      <AddPolicy @close="showAddPolicyModal = false" @added="getPolicies" />
    </q-dialog>
    <q-dialog v-model="showEditPolicyModal">
      <EditPolicy :pk="selectedRow" @close="showEditPolicyModal = false" @edited="getPolicies" />
    </q-dialog>
    <q-dialog v-model="showPolicyOverviewModal">
      <PolicyOverview @close="showPolicyOverviewModal = false" />
    </q-dialog>
  </div>
</template>

<script>
import axios from "axios";
import mixins from "@/mixins/mixins";
import { mapState } from "vuex";
import AddPolicy from "@/components/modals/automation/AddPolicy";
import EditPolicy from "@/components/modals/automation/EditPolicy";
import PolicyOverview from "@/components/modals/automation/PolicyOverview";

export default {
  name: "AutomationManager",
  components: { AddPolicy, EditPolicy, PolicyOverview },
  mixins: [mixins],
  data() {
    return {
      selectedRow: null,
      showAddPolicyModal: false,
      showEditPolicyModal: false,
      showPolicyOverviewModal: false,
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
          name: "applied_to",
          label: "Applied To",
          field: "applied_to",
          align: "left",
          sortable: false
        }
      ],
      visibleColumns: ["name", "desc", "active", "applied_to"]
    };
  },
  methods: {
    getPolicies() {
      this.clearRow();
      this.$store.dispatch("getPolicies");
    },
    hideAutomationManager() {
      this.$store.commit("TOGGLE_AUTOMATION_MANAGER", false);
    },
    policyRowSelected(pk) {
      this.selectedRow = pk;
    },
    clearRow() {
      this.selectedRow = null;
    },
    deletePolicy() {
      this.$q
        .dialog({
          title: "Delete policy?",
          cancel: true,
          ok: { label: "Delete", color: "negative" }
        })
        .onOk(() => {
          axios.delete(`/automation/policies/${this.selectedRow}`).then(r => {
            this.getPolicies();
            this.notifySuccess(`Policy ${r.data} was deleted!`);
          });
        });
    }
  },
  computed: {
    ...mapState({
      toggleAutomationManager: state => state.toggleAutomationManager,
      policies: state => state.policies
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