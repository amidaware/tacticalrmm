<template>
  <q-dialog ref="dialog" @hide="onHide">
    <div class="q-dialog-plugin" style="min-width: 90vw; max-width: 90vw">
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
            <q-btn ref="new" label="New" dense flat push unelevated no-caps icon="add" @click="showAddPolicyForm" />
            <q-btn
              ref="edit"
              label="Edit"
              :disable="!selectedPolicy"
              dense
              flat
              push
              unelevated
              no-caps
              icon="edit"
              @click="showEditPolicyForm(selectedPolicy)"
            />
            <q-btn
              ref="delete"
              label="Delete"
              :disable="!selectedPolicy"
              dense
              flat
              push
              unelevated
              no-caps
              icon="delete"
              @click="deletePolicy(selectedPolicy)"
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
            :table-class="{ 'table-bgcolor': !$q.dark.isActive, 'table-bgcolor-dark': $q.dark.isActive }"
            :data="policies"
            :columns="columns"
            :pagination.sync="pagination"
            row-key="id"
            binary-state-sort
            hide-pagination
            virtual-scroll
            dense
            flat
            :rows-per-page-options="[0]"
            no-data-label="No Policies"
          >
            <!-- header slots -->
            <template v-slot:header-cell-active="props">
              <q-th :props="props" auto-width>
                <q-icon name="power_settings_new" size="1.5em">
                  <q-tooltip>Enable Policy</q-tooltip>
                </q-icon>
              </q-th>
            </template>

            <template v-slot:header-cell-enforced="props">
              <q-th :props="props" auto-width>
                <q-icon name="security" size="1.5em">
                  <q-tooltip>Enforce Policy (Will override Agent tasks/checks)</q-tooltip>
                </q-icon>
              </q-th>
            </template>

            <!-- body slots -->
            <template v-slot:body="props">
              <q-tr
                :props="props"
                class="cursor-pointer"
                @click="selectedPolicy = props.row"
                @contextmenu="selectedPolicy = props.row"
              >
                <!-- context menu -->
                <q-menu context-menu>
                  <q-list dense style="min-width: 200px">
                    <q-item clickable v-close-popup @click="showEditPolicyForm(props.row)">
                      <q-item-section side>
                        <q-icon name="edit" />
                      </q-item-section>
                      <q-item-section>Edit</q-item-section>
                    </q-item>

                    <q-item clickable v-close-popup @click="showAddPolicyForm(props.row)">
                      <q-item-section side>
                        <q-icon name="content_copy" />
                      </q-item-section>
                      <q-item-section>Copy</q-item-section>
                    </q-item>

                    <q-item clickable v-close-popup @click="deletePolicy(props.row.id)">
                      <q-item-section side>
                        <q-icon name="delete" />
                      </q-item-section>
                      <q-item-section>Delete</q-item-section>
                    </q-item>

                    <q-separator></q-separator>

                    <q-item clickable v-close-popup @click="showRelations(props.row)">
                      <q-item-section side>
                        <q-icon name="account_tree" />
                      </q-item-section>
                      <q-item-section>Show Relations</q-item-section>
                    </q-item>

                    <q-item clickable v-close-popup @click="showPatchPolicyForm(props.row)">
                      <q-item-section side>
                        <q-icon name="system_update" />
                      </q-item-section>
                      <q-item-section>{{ patchPolicyText(props.row) }}</q-item-section>
                    </q-item>

                    <q-item clickable v-close-popup @click="showAlertTemplateAdd(props.row)">
                      <q-item-section side>
                        <q-icon name="warning" />
                      </q-item-section>
                      <q-item-section>{{ alertTemplateText(props.row) }}</q-item-section>
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
                    style="cursor: pointer; text-decoration: underline"
                    class="text-primary"
                    @click="showRelations(props.row)"
                    >{{ `Show Relations (${props.row.agents_count}+)` }}</span
                  >
                </q-td>
                <q-td>
                  <span
                    style="cursor: pointer; text-decoration: underline"
                    class="text-primary"
                    @click="showPatchPolicyForm(props.row)"
                    >{{ patchPolicyText(props.row) }}</span
                  >
                </q-td>
                <q-td>
                  <span
                    style="cursor: pointer; text-decoration: underline"
                    class="text-primary"
                    @click="showAlertTemplateAdd(props.row)"
                    >{{ alertTemplateText(props.row) }}</span
                  >
                </q-td>
                <q-td>
                  <q-icon name="content_copy" size="1.5em" @click="showAddPolicyForm(props.row)">
                    <q-tooltip>Create a copy of this policy</q-tooltip>
                  </q-icon>
                </q-td>
              </q-tr>
            </template>
          </q-table>
        </div>

        <q-card-section>
          <q-tabs
            v-model="subtab"
            dense
            inline-label
            class="text-grey"
            active-color="primary"
            indicator-color="primary"
            align="left"
            narrow-indicator
            no-caps
          >
            <q-tab name="checks" icon="fas fa-check-double" label="Checks" />
            <q-tab name="tasks" icon="fas fa-tasks" label="Tasks" />
          </q-tabs>
          <q-separator />
          <q-tab-panels v-model="subtab" :animated="false">
            <q-tab-panel name="checks">
              <PolicyChecksTab :selectedPolicy="selectedPolicy" />
            </q-tab-panel>
            <q-tab-panel name="tasks">
              <PolicyAutomatedTasksTab :selectedPolicy="selectedPolicy" />
            </q-tab-panel>
          </q-tab-panels>
        </q-card-section>
      </q-card>
    </div>
  </q-dialog>
</template>

<script>
import mixins from "@/mixins/mixins";
import DialogWrapper from "@/components/ui/DialogWrapper";
import PolicyForm from "@/components/automation/modals/PolicyForm";
import PolicyOverview from "@/components/automation/PolicyOverview";
import RelationsView from "@/components/automation/modals/RelationsView";
import PatchPolicyForm from "@/components/modals/agents/PatchPolicyForm";
import AlertTemplateAdd from "@/components/modals/alerts/AlertTemplateAdd";
import PolicyChecksTab from "@/components/automation/PolicyChecksTab";
import PolicyAutomatedTasksTab from "@/components/automation/PolicyAutomatedTasksTab";

export default {
  name: "AutomationManager",
  components: { PolicyChecksTab, PolicyAutomatedTasksTab },
  mixins: [mixins],
  data() {
    return {
      subtab: "checks",
      policies: [],
      selectedPolicy: null,
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
          name: "alert_template",
          label: "Alert Template",
          field: "alert_template",
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
        rowsPerPage: 0,
        sortBy: "name",
        descending: true,
      },
    };
  },
  methods: {
    getPolicies() {
      this.$axios.get("/automation/policies/").then(r => {
        console.log(r.data);
        this.policies = r.data;
      });
    },
    clearRow() {
      this.selectedPolicy = null;
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
          this.$axios
            .delete(`/automation/policies/${pk}/`)
            .then(r => {
              this.notifySuccess("Policy was deleted!");
            })
            .catch(error => {
              this.notifyError("An Error occured while deleting policy");
            });
        });
    },
    showRelations(policy) {
      this.$q.dialog({
        component: RelationsView,
        parent: this,
        policy: policy,
      });
    },
    showPolicyOverview() {
      this.$q.dialog({
        component: PolicyOverview,
        parent: this,
      });
    },
    showAddPolicyForm(policy) {
      this.$q
        .dialog({
          component: PolicyForm,
          parent: this,
          copyPolicy: policy,
        })
        .onOk(() => {
          this.refresh();
        });
    },
    showEditPolicyForm(policy) {
      this.$q
        .dialog({
          component: PolicyForm,
          parent: this,
          policy: policy,
        })
        .onOk(() => {
          this.refresh();
        });
    },
    showAlertTemplateAdd(policy) {
      this.$q
        .dialog({
          component: AlertTemplateAdd,
          parent: this,
          type: "policy",
          object: policy,
        })
        .onOk(() => {
          this.refresh();
        });
    },
    showPatchPolicyForm(policy) {
      this.$q
        .dialog({
          component: DialogWrapper,
          parent: this,
          title: policy.winupdatepolicy.length > 0 ? "Edit Patch Policy" : "Add Patch Policy",
          vuecomponent: PatchPolicyForm,
          componentProps: {
            policy: policy,
          },
        })
        .onOk(() => {
          this.refresh();
        });
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

      this.$axios
        .put(`/automation/policies/${data.id}/`, data)
        .then(r => {
          this.notifySuccess(text);
        })
        .catch(error => {
          this.notifyError("An Error occured while editing policy");
        });
    },
    patchPolicyText(policy) {
      return policy.winupdatepolicy.length > 0 ? "Show Patch Policy" : "Create Patch Policy";
    },
    alertTemplateText(policy) {
      return policy.alert_template ? "Modify Alert Template" : "Assign Alert Template";
    },
    show() {
      this.$refs.dialog.show();
    },
    hide() {
      this.$refs.dialog.hide();
    },
    onHide() {
      this.$emit("hide");
    },
  },
  mounted() {
    this.getPolicies();
  },
};
</script>