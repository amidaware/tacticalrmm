<template>
    <div v-if="Object.keys(summary).length === 0">
        No agent selected
    </div>
    <div v-else>
        {{ summary.operating_system }}
    </div>
</template>

<script>
import axios from 'axios';
export default {
    name: 'SummaryTab',
    data() {
        return {

        }
    },
    computed: {
        summary() {
            return this.$store.state.agentSummary;
        }
    }
}
</script>

