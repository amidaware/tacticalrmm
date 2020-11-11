<template>
  <q-card style="width: 50vw; max-width: 80vw">
    <q-card-section>
      <q-table
        class="remote-bg-tbl-sticky"
        title="Software"
        dense
        :data="chocos"
        :columns="columns"
        :pagination.sync="pagination"
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
        <template slot="body" slot-scope="props" :props="props">
          <q-tr :props="props">
            <q-td auto-width>
              <q-btn
                size="sm"
                color="grey-5"
                icon="fas fa-plus"
                text-color="black"
                @click="install(props.row.name, props.row.version)"
              />
            </q-td>
            <q-td @click="showDescription(props.row.name)">
              <span style="cursor: pointer; text-decoration: underline" class="text-primary">{{ props.row.name }}</span>
            </q-td>
            <q-td>{{ props.row.version }}</q-td>
          </q-tr>
        </template>
      </q-table>
    </q-card-section>
  </q-card>
</template>

<script>
import axios from "axios";
import { mapState } from "vuex";
import { mapGetters } from "vuex";
import mixins from "@/mixins/mixins";
export default {
  name: "InstallSoftware",
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
        {
          name: "version",
          align: "left",
          label: "Version",
          field: "version",
          sortable: false,
        },
      ],
    };
  },
  methods: {
    getChocos() {
      axios.get("/software/chocos/").then(r => {
        this.chocos = r.data;
      });
    },
    showDescription(name) {
      window.open(`https://chocolatey.org/packages/${name}`, "_blank");
    },
    install(name, version) {
      const data = { name: name, version: version, pk: this.agentpk };
      this.$q
        .dialog({
          title: "Install Software",
          message: `Install ${name} on ${this.agentHostname}?`,
          persistent: true,
          ok: { label: "Install" },
          cancel: { color: "negative" },
        })
        .onOk(() => {
          axios
            .post("/software/install/", data)
            .then(r => {
              this.$emit("close");
              this.notifySuccess(r.data);
            })
            .catch(e => {
              this.notifyError("Something went wrong");
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