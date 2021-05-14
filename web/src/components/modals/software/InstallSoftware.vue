<template>
  <q-card style="width: 40vw; max-width: 50vw">
    <q-card-section>
      <q-table
        class="remote-bg-tbl-sticky"
        :table-class="{ 'table-bgcolor': !$q.dark.isActive, 'table-bgcolor-dark': $q.dark.isActive }"
        title="Software"
        dense
        :rows="chocos"
        :columns="columns"
        v-model:pagination="pagination"
        :filter="filter"
        binary-state-sort
        hide-bottom
        virtual-scroll
        :rows-per-page-options="[0]"
        row-key="name"
      >
        <template v-slot:top>
          <q-input v-model="filter" outlined label="Search" dense clearable>
            <template v-slot:prepend>
              <q-icon name="search" />
            </template>
          </q-input>
          <q-space />
          <q-btn icon="close" flat round dense v-close-popup />
        </template>
        <template v-slot:body="props">
          <q-tr :props="props">
            <q-td auto-width>
              <q-btn size="sm" color="grey-5" icon="fas fa-plus" text-color="black" @click="install(props.row.name)" />
            </q-td>
            <q-td @click="showDescription(props.row.name)">
              <span style="cursor: pointer; text-decoration: underline" class="text-primary">{{ props.row.name }}</span>
            </q-td>
          </q-tr>
        </template>
      </q-table>
    </q-card-section>
  </q-card>
</template>

<script>
import { mapGetters } from "vuex";
import mixins from "@/mixins/mixins";
export default {
  name: "InstallSoftware",
  emits: ["close"],
  props: ["agentpk"],
  mixins: [mixins],
  data() {
    return {
      filter: "",
      chocos: [],
      pagination: {
        rowsPerPage: 0,
        sortBy: "name",
        descending: false,
      },
      columns: [
        { name: "install", align: "left", label: "Install", sortable: false },
        {
          name: "name",
          align: "left",
          label: "Name",
          field: "name",
          sortable: true,
        },
      ],
    };
  },
  methods: {
    getChocos() {
      this.$axios.get("/software/chocos/").then(r => {
        this.chocos = r.data;
      });
    },
    showDescription(name) {
      window.open(`https://chocolatey.org/packages/${name}`, "_blank");
    },
    install(name) {
      const data = { name: name, pk: this.agentpk };
      this.$q
        .dialog({
          title: `Install ${name} on ${this.agentHostname}?`,
          persistent: true,
          ok: { label: "Install" },
          cancel: true,
        })
        .onOk(() => {
          this.$q.loading.show();
          this.$axios
            .post("/software/install/", data)
            .then(r => {
              this.$q.loading.hide();
              this.$emit("close");
              this.notifySuccess(r.data, 5000);
            })
            .catch(e => {
              this.$q.loading.hide();
            });
        });
    },
  },
  computed: {
    ...mapGetters(["agentHostname"]),
  },
  created() {
    this.getChocos();
  },
};
</script>