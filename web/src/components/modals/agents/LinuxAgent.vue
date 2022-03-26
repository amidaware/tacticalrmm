<template>
  <q-card style="min-width: 70vw">
    <q-card-section class="row">
      <q-card-actions align="left">
        <div class="text-h6">Linux Installation Instructions</div>
      </q-card-actions>
      <q-space />
      <q-card-actions align="right">
        <q-btn v-close-popup flat round dense icon="close" />
      </q-card-actions>
    </q-card-section>
    <q-card-section>
      <p class="text-subtitle1">Run the following command on your terminal.</p>
      <p>
        <q-field outlined :color="$q.dark.isActive ? 'white' : 'black'">
          <code>{{ info.data.cmd }}</code>
        </q-field>
      </p>
      <q-expansion-item
        switch-toggle-side
        header-class="text-primary"
        expand-separator
        label="View optional command line args"
      >
        <div class="q-pa-xs q-gutter-xs">
          <q-badge class="text-caption q-mr-xs" color="grey" text-color="black">
            <code>-p proxy_url</code>
          </q-badge>
          <span>Use a proxy during installation.</span>
        </div>
        <div class="q-pa-xs q-gutter-xs">
          <q-badge class="text-caption q-mr-xs" color="grey" text-color="black">
            <code>-debug</code>
          </q-badge>
          <span>To enable verbose output during the install</span>
        </div>
      </q-expansion-item>
      <br />
      <p class="text-italic">Note: the auth token above will be valid for {{ info.expires }} hours.</p>
    </q-card-section>
  </q-card>
</template>

<script>
import mixins from "@/mixins/mixins";

export default {
  name: "LinuxAgent",
  mixins: [mixins],
  props: ["info"],
};
</script>