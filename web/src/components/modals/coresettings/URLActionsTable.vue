<template>
  <div>
    <div class="row">
      <div class="text-subtitle2">URL Actions</div>
      <q-space />
      <q-btn
        size="sm"
        color="grey-5"
        icon="fas fa-plus"
        text-color="black"
        label="Add URL Action"
        @click="addAction"
      />
    </div>
    <q-separator />
    <q-table
      dense
      :rows="actions"
      :columns="columns"
      v-model:pagination="pagination"
      row-key="id"
      binary-state-sort
      hide-pagination
      virtual-scroll
      :rows-per-page-options="[0]"
      no-data-label="No URL Actions added yet"
    >
      <!-- body slots -->
      <template v-slot:body="props">
        <q-tr
          :props="props"
          class="cursor-pointer"
          @dblclick="editAction(props.row)"
        >
          <!-- context menu -->
          <q-menu context-menu>
            <q-list dense style="min-width: 200px">
              <q-item clickable v-close-popup @click="editAction(props.row)">
                <q-item-section side>
                  <q-icon name="edit" />
                </q-item-section>
                <q-item-section>Edit</q-item-section>
              </q-item>
              <q-item clickable v-close-popup @click="deleteAction(props.row)">
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
          <!-- name -->
          <q-td>
            {{ props.row.name }}
          </q-td>
          <!-- desc -->
          <q-td>
            {{ props.row.desc }}
          </q-td>
          <!-- pattern -->
          <q-td>
            {{ props.row.pattern }}
          </q-td>
        </q-tr>
      </template>
    </q-table>
  </div>
</template>

<script>
import URLActionsForm from "@/components/modals/coresettings/URLActionsForm";
import mixins from "@/mixins/mixins";

export default {
  name: "URLActionTable",
  mixins: [mixins],
  data() {
    return {
      actions: [],
      pagination: {
        rowsPerPage: 0,
        sortBy: "name",
        descending: true,
      },
      columns: [
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
          sortable: true,
        },
        {
          name: "pattern",
          label: "Pattern",
          field: "pattern",
          align: "left",
          sortable: true,
        },
      ],
    };
  },
  methods: {
    getURLActions() {
      this.$q.loading.show();

      this.$axios
        .get("/core/urlaction/")
        .then((r) => {
          this.$q.loading.hide();
          this.actions = r.data;
        })
        .catch(() => {
          this.$q.loading.hide();
        });
    },
    addAction() {
      this.$q
        .dialog({
          component: URLActionsForm,
        })
        .onOk(() => {
          this.getURLActions();
        });
    },
    editAction(action) {
      this.$q
        .dialog({
          component: URLActionsForm,
          componentProps: {
            action: action,
          },
        })
        .onOk(() => {
          this.getURLActions();
        });
    },
    deleteAction(action) {
      this.$q
        .dialog({
          title: `Delete URL Action: ${action.name}?`,
          cancel: true,
          ok: { label: "Delete", color: "negative" },
        })
        .onOk(() => {
          this.$q.loading.show();
          this.$axios
            .delete(`/core/urlaction/${action.id}/`)
            .then(() => {
              this.getURLActions();
              this.$q.loading.hide();
              this.notifySuccess(`URL Action: ${action.name} was deleted!`);
            })
            .catch(() => {
              this.$q.loading.hide();
            });
        });
    },
  },
  mounted() {
    this.getURLActions();
  },
};
</script>
