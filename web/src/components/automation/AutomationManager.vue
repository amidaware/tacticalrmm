<template>
  <div style="width: 900px; max-width: 90vw;">
    <q-card>
      <q-bar>
        <q-btn ref="refresh" @click="refresh" class="q-mr-sm" dense flat push icon="refresh" />Automation Manager
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
            @click="showEditPolicyModal(selectedRow)"
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
            @click="deletePolicy(selectedRow)"
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
            @click="showPolicyOverview"
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
              <!-- context menu -->
              <q-menu context-menu>
                <q-list dense style="min-width: 200px">
                  <q-item 
                    clickable 
                    v-close-popup 
                    @click="showEditPolicyModal(props.row.id)"
                    id="context-edit"
                  >
                    <q-item-section side>
                      <q-icon name="edit" />
                    </q-item-section>
                    <q-item-section>Edit</q-item-section>
                  </q-item>
                  <q-item
                    clickable
                    v-close-popup
                    @click="deletePolicy(props.row.id)"
                    id="context-delete"
                  >
                    <q-item-section side>
                      <q-icon name="delete" />
                    </q-item-section>
                    <q-item-section>Delete</q-item-section>
                  </q-item>

                  <q-separator></q-separator>

                  <q-item
                    clickable
                    v-close-popup
                    @click="showRelationsModal(props.row)"
                    id="context-relation"
                  >
                    <q-item-section side>
                      <q-icon name="account_tree" />
                    </q-item-section>
                    <q-item-section>Show Relations</q-item-section>
                  </q-item>

                  <q-separator></q-separator>

                  <q-item clickable v-close-popup>
                    <q-item-section>Close</q-item-section>
                  </q-item>
                </q-list>
              </q-menu>
              <q-td>{{ props.row.name }}</q-td>
              <q-td>{{ props.row.desc }}</q-td>
              <q-td>{{ props.row.active }}</q-td>
              <q-td>
                <span
                  style="cursor:pointer;color:blue;text-decoration:underline"
                  @click="showRelationsModal(props.row)"
                >
                  {{ `See Related (${props.row.clients.length + props.row.sites.length + props.row.agents.length}+)` }}
                </span>
              </q-td>
            </q-tr>
          </template>
        </q-table>
      </div>

      <q-card-section>
        <PolicySubTableTabs />
      </q-card-section>
    </q-card>

    <!-- policy form modal -->
    <q-dialog 
      v-model="showPolicyFormModal"
      @hide="closePolicyFormModal" 
    >
      <PolicyForm 
        :pk="editPolicyId" 
        @close="closePolicyFormModal" 
      />
    </q-dialog>

    <!-- policy overview modal -->
    <q-dialog 
      v-model="showPolicyOverviewModal"
      @hide="clearRow"
    >
      <PolicyOverview />
    </q-dialog>

    <!-- policy relations modal -->
    <q-dialog 
      v-model="showRelationsViewModal"
      @hide="closeRelationsModal"
    >
      <RelationsView :policy="policy" />
    </q-dialog>
  </div>
</template>

<script>
import mixins, { notifySuccessConfig, notifyErrorConfig } from "@/mixins/mixins";
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
      editPolicyId: null,
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
      // First item of the keys array is the selected policy pk
      this.$store.commit("automation/setSelectedPolicy", keys[0]);
      this.$store.dispatch("automation/loadPolicyChecks", keys[0]);
      this.$store.dispatch("automation/loadPolicyAutomatedTasks", keys[0]);
    },
    clearRow() {
      this.$store.commit("automation/setSelectedPolicy", null);
      this.$store.commit("automation/setPolicyChecks", {});
      this.$store.commit("automation/setPolicyAutomatedTasks", {});
    },
    refresh() {
      this.getPolicies();
      this.clearRow();
    },
    deletePolicy(id) {
      this.$q
        .dialog({
          title: "Delete policy?",
          cancel: true,
          ok: { label: "Delete", color: "negative" }
        })
        .onOk(() => {
          this.$store
            .dispatch("automation/deletePolicy", id)
            .then(response => {
              this.$q.notify(notifySuccessConfig("Policy was deleted!"));
            })
            .catch(error => {
              this.$q.notify(notifyErrorConfig("An Error occured while deleting policy"));
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
    showEditPolicyModal(id) {
      this.editPolicyId = id;
      this.showPolicyFormModal = true;
    },
    closePolicyFormModal() {
      this.showPolicyFormModal = false;
      this.editPolicyId = null;
      this.refresh();
    },
    showAddPolicyModal() {
      this.showPolicyFormModal = true;
    },
    showPolicyOverview() {
      this.showPolicyOverviewModal = true
      this.clearRow();
    }
  },
  computed: {
    ...mapState({
      policies: state => state.automation.policies,
      selectedRow: state => state.automation.selectedPolicy
    })
  },
  mounted() {
    this.refresh();
  }
};
</script>