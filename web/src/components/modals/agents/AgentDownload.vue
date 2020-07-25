<template>
  <q-card style="min-width: 60vw">
    <q-card-section class="row">
      <q-card-actions align="left">
        <div class="text-h6">Installation Instructions</div>
      </q-card-actions>
      <q-space />
      <q-card-actions align="right">
        <q-btn v-close-popup flat round dense icon="close" />
      </q-card-actions>
    </q-card-section>
    <q-card-section>
      <p>Download the agent then run the following command from an elevated command prompt on the device you want to add.</p>
      <br />
      <p>
        <code>
          {{ info.exe }} /VERYSILENT /SUPPRESSMSGBOXES
          && timeout /t 20 /nobreak > NUL
          && "C:\Program Files\TacticalAgent\tacticalrmm.exe" -m install --api "{{ info.api }}"
          --client-id {{ info.data.client }} --site-id {{ info.data.site }} --desc "{{ info.desc }}"
          --agent-type "{{ info.agenttype }}" --auth "{{ info.data.token }}"
        </code>
      </p>
      <br />
      <p class="text-italic">Note: the auth token above will be valid for 1 hour.</p>
      <q-btn type="a" :href="info.download" color="primary" label="Download Agent" />
    </q-card-section>
  </q-card>
</template>

<script>
export default {
  name: "AgentDownload",
  props: ["info"]
};
</script>