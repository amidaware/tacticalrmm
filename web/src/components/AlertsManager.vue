<template>
  <q-dialog ref="dialog" @hide="onHide">
    <div class="q-dialog-plugin" style="width: 90vw; max-width: 90vw">
      <q-card>
        <q-bar>
          <q-btn ref="refresh" @click="refresh" class="q-mr-sm" dense flat push icon="refresh" />Alerts Manager
          <q-space />
          <q-btn dense flat icon="close" v-close-popup>
            <q-tooltip content-class="bg-white text-primary">Close</q-tooltip>
          </q-btn>
        </q-bar>
        <div class="q-pa-md" style="min-height: 65vh; max-height: 65vh">
          <div class="q-gutter-sm">
            <q-btn ref="new" label="New" dense flat push unelevated no-caps icon="add" @click="showAddTemplateModal" />
            <q-btn
              ref="edit"
              label="Edit"
              :disable="selected.length === 0"
              dense
              flat
              push
              unelevated
              no-caps
              icon="edit"
              @click="showEditTemplateModal(selected[0])"
            />
            <q-btn
              ref="delete"
              label="Delete"
              :disable="selected.length === 0"
              dense
              flat
              push
              unelevated
              no-caps
              icon="delete"
              @click="deleteTemplate(selected[0])"
            />
          </div>
          <q-table
            dense
            :data="templates"
            :columns="columns"
            :pagination.sync="pagination"
            row-key="id"
            binary-state-sort
            hide-pagination
            virtual-scroll
            :rows-per-page-options="[0]"
            no-data-label="No Alert Templates"
          >
            <!-- header slots -->
            <template v-slot:header-cell-is_active="props">
              <q-th :props="props" auto-width>
                <q-icon name="power_settings_new" size="1.5em">
                  <q-tooltip>Enable Template</q-tooltip>
                </q-icon>
              </q-th>
            </template>

            <template v-slot:header-cell-email_severity="props">
              <q-th :props="props" auto-width>
                {{ props.name }}
              </q-th>
            </template>

            <template v-slot:header-cell-text_severity="props">
              <q-th :props="props" auto-width>
                {{ props.name }}
              </q-th>
            </template>
            <!-- body slots -->
            <template v-slot:body="props">
              <q-tr
                :props="props"
                class="cursor-pointer"
                :class="rowSelectedClass(props.row.id, selected)"
                @click="selected = props.row"
                @contextmenu="selected = props.row"
              >
                <!-- context menu -->
                <q-menu context-menu>
                  <q-list dense style="min-width: 200px">
                    <q-item clickable v-close-popup @click="showEditTemplateModal(props.row)" id="context-edit">
                      <q-item-section side>
                        <q-icon name="edit" />
                      </q-item-section>
                      <q-item-section>Edit</q-item-section>
                    </q-item>
                    <q-item clickable v-close-popup @click="deleteTemplate(props.row)" id="context-delete">
                      <q-item-section side>
                        <q-icon name="delete" />
                      </q-item-section>
                      <q-item-section>Delete</q-item-section>
                    </q-item>

                    <q-separator></q-separator>

                    <q-item clickable v-close-popup>
                      <q-item-section>Close</q-item-section>
                    </q-item>
                  </q-list>
                </q-menu>
                <!-- enabled checkbox -->
                <q-td>
                  <q-checkbox dense @input="toggleEnabled(props.row)" v-model="props.row.is_active" />
                </q-td>
                <!-- name -->
                <q-td>{{ props.row.name }}</q-td>
                <!-- email severity -->
                <q-td>
                  <q-icon v-if="props.row.email_alert_severity.includes('info')" color="primary" name="info" size="sm">
                    <q-tooltip>Sends email alert on informational severity</q-tooltip>
                  </q-icon>
                  <q-icon
                    v-if="props.row.email_alert_severity.includes('warning')"
                    color="warning"
                    name="warning"
                    size="sm"
                  >
                    <q-tooltip>Sends email alert on warning severity</q-tooltip>
                  </q-icon>
                  <q-icon
                    v-if="props.row.email_alert_severity.includes('error')"
                    color="negative"
                    name="error"
                    size="sm"
                  >
                    <q-tooltip>Sends email alert on error severity</q-tooltip>
                  </q-icon>
                </q-td>
                <!-- text severity -->
                <q-td>
                  <q-icon v-if="props.row.email_alert_severity.includes('info')" color="primary" name="info" size="sm">
                    <q-tooltip>Sends text alert on informational severity</q-tooltip>
                  </q-icon>
                  <q-icon
                    v-if="props.row.text_alert_severity.includes('warning')"
                    color="warning"
                    name="warning"
                    size="sm"
                  >
                    <q-tooltip>Sends text alert on warning severity</q-tooltip>
                  </q-icon>
                  <q-icon
                    v-if="props.row.text_alert_severity.includes('error')"
                    color="negative"
                    name="error"
                    size="sm"
                  >
                    <q-tooltip>Sends text alert on error severity</q-tooltip>
                  </q-icon>
                </q-td>
                <!-- applied to -->
                <q-td>Applied To Placeholder</q-td>
                <!-- actions -->
                <q-td>{{ props.row.actions.length }} actions</q-td>
              </q-tr>
            </template>
          </q-table>
        </div>
      </q-card>
    </div>
  </q-dialog>
</template>

<script>
import mixins from "@/mixins/mixins";
import AlertTemplateForm from "@/components/modals/alerts/AlertTemplateForm";

export default {
  name: "AlertsManager",
  mixins: [mixins],
  data() {
    return {
      selected: [],
      templates: [],
      columns: [
        { name: "is_active", label: "Active", field: "is_active", align: "left" },
        { name: "name", label: "Name", field: "name", align: "left" },
        {
          name: "email_severity",
          label: "Email Severity",
          field: "email_severity",
          align: "center",
        },
        {
          name: "text_severity",
          label: "Text Severity",
          field: "text_severity",
          align: "center",
        },
        {
          name: "applied_to",
          label: "Applied To",
          field: "applied_to",
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
    getTemplates() {
      this.$q.loading.show();
      this.$axios
        .get("alerts/alerttemplates/")
        .then(r => {
          this.templates = r.data;
          this.$q.loading.hide();
        })
        .catch(e => {
          this.$q.loading.hide();
          this.notifyError("Unable to pull Alert Templates.");
        });
    },
    clearRow() {
      this.selected = [];
    },
    refresh() {
      this.getTemplates();
      this.clearRow();
    },
    deleteTemplate(template) {
      this.$q
        .dialog({
          title: `Delete alert template ${template.name}?`,
          cancel: true,
          ok: { label: "Delete", color: "negative" },
        })
        .onOk(() => {
          this.$q.loading.show();
          this.$axios
            .delete(`alerts/alerttemplates/${template.id}/`)
            .then(r => {
              this.getTemplates();
              this.$q.loading.hide();
              this.notifySuccess(`Alert template ${template.name} was deleted!`);
            })
            .catch(error => {
              this.$q.loading.hide();
              this.notifyError(`An Error occured while deleting alert template: ${template.name}`);
            });
        });
    },
    showEditTemplateModal(template) {
      this.$q
        .dialog({
          component: AlertTemplateForm,
          parent: this,
          alertTemplate: template,
        })
        .onOk(() => {
          this.refresh();
        });
    },
    showAddTemplateModal() {
      this.clearRow();
      this.$q
        .dialog({
          component: AlertTemplateForm,
          parent: this,
        })
        .onOk(() => {
          this.refresh();
        });
    },
    toggleEnabled(template) {
      let text = template.is_active ? "Template enabled successfully" : "Template disabled successfully";

      const data = {
        id: template.id,
        is_active: template.is_active,
      };

      this.$axios
        .put(`alerts/alerttemplates/${template.id}/`, data)
        .then(r => {
          this.notifySuccess(text);
        })
        .catch(error => {
          this.notifyError("An Error occured while editing the template");
        });
    },
    rowSelectedClass(id, selected) {
      if (selected.length !== 0 && selected[0].id === id) return this.$q.dark.isActive ? "highlight-dark" : "highlight";
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
    this.getTemplates();
  },
};
</script>