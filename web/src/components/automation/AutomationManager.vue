<template>
  <div style="width: 60vw; max-width: 90vw">
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
          <q-btn ref="new" label="New" dense flat push unelevated no-caps icon="add" @click="showAddPolicyModal" />
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
          :data="policies"
          :columns="columns"
          :pagination.sync="pagination"
          :selected.sync="selected"
          selection="single"
          @selection="policyRowSelected"
          row-key="id"
          binary-state-sort
          hide-pagination
          :hide-bottom="!!selected"
        >
          <!-- header slots -->
          <template v-slot:header="props">
            <q-tr :props="props">
              <template v-for="col in props.cols">
                <q-th v-if="col.name === 'active'" auto-width :key="col.name">
                  <q-icon name="power_settings_new" size="1.5em">
                    <q-tooltip>Enable Policy</q-tooltip>
                  </q-icon>
                </q-th>

                <q-th v-else-if="col.name === 'enforced'" auto-width :key="col.name">
                  <q-icon name="security" size="1.5em">
                    <q-tooltip>Enforce Policy (Will override Agent tasks/checks)</q-tooltip>
                  </q-icon>
                </q-th>

                <q-th v-else :key="col.name" :props="props">{{ col.label }}</q-th>
              </template>
            </q-tr>
          </template>
          <!-- No data Slot -->
          <template v-slot:no-data>
            <div class="full-width row flex-center q-gutter-sm">
              <span v-if="policies.length === 0">No Policies</span>
            </div>
          </template>
          <!-- body slots -->
          <template v-slot:body="props">
            <q-tr :props="props" class="cursor-pointer" @click="props.selected = true">
              <!-- context menu -->
              <q-menu context-menu>
                <q-list dense style="min-width: 200px">
                  <q-item clickable v-close-popup @click="showEditPolicyModal(props.row.id)" id="context-edit">
                    <q-item-section side>
                      <q-icon name="edit" />
                    </q-item-section>
                    <q-item-section>Edit</q-item-section>
                  </q-item>

                  <q-item clickable v-close-popup @click="showCopyPolicyModal(props.row)" id="context-copy">
                    <q-item-section side>
                      <q-icon name="content_copy" />
                    </q-item-section>
                    <q-item-section>Copy</q-item-section>
                  </q-item>

                  <q-item clickable v-close-popup @click="deletePolicy(props.row.id)" id="context-delete">
                    <q-item-section side>
                      <q-icon name="delete" />
                    </q-item-section>
                    <q-item-section>Delete</q-item-section>
                  </q-item>

                  <q-separator></q-separator>

                  <q-item clickable v-close-popup @click="showRelationsModal(props.row)" id="context-relation">
                    <q-item-section side>
                      <q-icon name="account_tree" />
                    </q-item-section>
                    <q-item-section>Show Relations</q-item-section>
                  </q-item>

                  <q-item clickable v-close-popup @click="showEditPatchPolicyModal(props.row)" id="context-winupdate">
                    <q-item-section side>
                      <q-icon name="system_update" />
                    </q-item-section>
                    <q-item-section>{{ patchPolicyText(props.row) }}</q-item-section>
                  </q-item>

                  <q-separator></q-separator>

                  <q-item clickable v-close-popup>
                    <q-item-section>Close</q-item-section>
                  </q-item>
                </q-list>
              </q-menu>
              <!-- enabled checkbox -->
              <q-td>
                <q-checkbox dense @input="toggleCheckbox(props.row, 'Active')" v-model="props.row.active" />
              </q-td>
              <!-- enforced checkbox -->
              <q-td>
                <q-checkbox dense @input="toggleCheckbox(props.row, 'Enforced')" v-model="props.row.enforced" />
              </q-td>
              <q-td>
                {{ props.row.name }}
                <q-chip v-if="props.row.default_server_policy" color="primary" text-color="white" size="sm"
                  >Default Server</q-chip
                >
                <q-chip v-if="props.row.default_workstation_policy" color="primary" text-color="white" size="sm"
                  >Default Workstation</q-chip
                >
              </q-td>
              <q-td>{{ props.row.desc }}</q-td>
              <q-td>
                <span
                  style="cursor: pointer; color: blue; text-decoration: underline"
                  @click="showRelationsModal(props.row)"
                  >{{ `Show Relations (${props.row.agents_count}+)` }}</span
                >
              </q-td>
              <q-td>
                <span
                  style="cursor: pointer; color: blue; text-decoration: underline"
                  @click="showEditPatchPolicyModal(props.row)"
                  >{{ patchPolicyText(props.row) }}</span
                >
              </q-td>
              <q-td>
                <q-icon name="content_copy" size="1.5em" @click="showCopyPolicyModal(props.row)">
                  <q-tooltip>Create a copy of this policy</q-tooltip>
                </q-icon>
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
    <q-dialog v-model="showPolicyFormModal" @hide="closePolicyFormModal">
      <PolicyForm :pk="editPolicyId" :copyPolicy="copyPolicy" @close="closePolicyFormModal" />
    </q-dialog>

    <!-- policy overview modal -->
    <q-dialog v-model="showPolicyOverviewModal" @hide="clearRow">
      <PolicyOverview />
    </q-dialog>

    <!-- policy relations modal -->
    <q-dialog v-model="showRelationsViewModal" @hide="closeRelationsModal">
      <RelationsView :policy="policy" />
    </q-dialog>

    <!-- patch policy modal -->
    <q-dialog v-model="showPatchPolicyModal" @hide="closePatchPolicyModal">
      <q-card style="width: 900px; max-width: 90vw">
        <q-bar>
          {{ patchPolicyModalText() }}
          <q-space />
          <q-btn dense flat icon="close" v-close-popup>
            <q-tooltip content-class="bg-white text-primary">Close</q-tooltip>
          </q-btn>
        </q-bar>
        <div class="scroll" style="height: 70vh">
          <PatchPolicyForm :policy="policy" @close="closePatchPolicyModal" />
        </div>
      </q-card>
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
import PatchPolicyForm from "@/components/modals/agents/PatchPolicyForm";

export default {
  name: "AutomationManager",
  components: { PolicyForm, PolicyOverview, PolicySubTableTabs, RelationsView, PatchPolicyForm },
  mixins: [mixins],
  data() {
    return {
      showPolicyFormModal: false,
      showPolicyOverviewModal: false,
      showRelationsViewModal: false,
      showPatchPolicyModal: false,
      policy: null,
      editPolicyId: null,
      copyPolicy: null,
      selected: [],
      columns: [
        { name: "active", label: "Active", field: "active", align: "left" },
        { name: "enforced", label: "Enforced", field: "enforced", align: "left" },
        {
          name: "name",
          label: "Name",
          field: "name",
          align: "left",
          sortable: true,
        },
        {
          name: "desc",
          label: "Description",
          field: "desc",
          align: "left",
        },
        {
          name: "relations",
          label: "Relations",
          field: "relations",
          align: "left",
        },
        {
          name: "winupdatepolicy",
          label: "Patch Policy",
          field: "winupdatepolicy",
          align: "left",
        },
        {
          name: "actions",
          label: "Actions",
          field: "actions",
          align: "left",
        },
      ],
      pagination: {
        rowsPerPage: 9999,
      },
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
      this.$store.commit("automation/setPolicyChecks", []);
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
          ok: { label: "Delete", color: "negative" },
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
    showCopyPolicyModal(policy) {
      this.copyPolicy = policy;
      this.showPolicyFormModal = true;
    },
    closePolicyFormModal() {
      this.showPolicyFormModal = false;
      this.editPolicyId = null;
      this.copyPolicyId = null;
      this.refresh();
    },
    showAddPolicyModal() {
      this.showPolicyFormModal = true;
    },
    showPolicyOverview() {
      this.showPolicyOverviewModal = true;
      this.clearRow();
    },
    toggleCheckbox(policy, type) {
      let text = "";

      if (type === "Active") {
        text = policy.active ? "Policy enabled successfully" : "Policy disabled successfully";
      } else if (type === "Enforced") {
        text = policy.enforced ? "Policy enforced successfully" : "Policy enforcement disabled";
      }

      const data = {
        id: policy.id,
        name: policy.name,
        desc: policy.desc,
        active: policy.active,
        enforced: policy.enforced,
      };

      this.$store
        .dispatch("automation/editPolicy", data)
        .then(response => {
          this.$q.notify(notifySuccessConfig(text));
        })
        .catch(error => {
          this.$q.notify(notifyErrorConfig("An Error occured while editing policy"));
        });
    },
    showEditPatchPolicyModal(policy) {
      this.policy = policy;
      this.showPatchPolicyModal = true;
    },
    closePatchPolicyModal(policy) {
      this.policy = null;
      this.showPatchPolicyModal = false;
      this.refresh();
    },
    patchPolicyText(policy) {
      return policy.winupdatepolicy.length === 1 ? "Show Patch Policy" : "Create Patch Policy";
    },
    patchPolicyModalText() {
      if (this.policy !== null) {
        return this.policy.winupdatepolicy.length === 1 ? "Edit Patch Policy" : "Add Patch Policy";
      }
    },
  },
  computed: {
    ...mapState({
      policies: state => state.automation.policies,
      selectedRow: state => state.automation.selectedPolicy,
    }),
  },
  mounted() {
    this.refresh();
  },
};
</script>