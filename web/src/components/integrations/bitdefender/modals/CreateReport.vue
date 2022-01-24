<template>
    <q-dialog ref="dialogRef" @hide="onDialogHide" persistent>
        <q-card class="q-dialog-plugin" style="width: 60vw">
            <q-bar>
                Create Report
                <q-space />
                <q-btn dense flat icon="close" v-close-popup>
                    <q-tooltip class="bg-white text-primary">Close</q-tooltip>
                </q-btn>
            </q-bar>
            <q-card-section>
                <q-input
                    filled
                    v-model="reportName"
                    label="Report Name *"
                    dense
                    :rules="[(val) => !!val || '*Required']"
                />
                <q-select
                    v-if="reportName"
                    filled
                    dense
                    v-model="reportType"
                    label="Report Type *"
                    :options="reportTypeOptions"
                    :rules="[(val) => !!val || '*Required']"
                />
                <q-select
                    v-if="reportType.value"
                    filled
                    dense
                    v-model="reportOccurrence"
                    label="Frequency *"
                    :options="reportOccurrenceOptions"
                    :rules="[(val) => !!val || '*Required']"
                />
                <q-select
                    v-if="reportOccurrence.value"
                    filled
                    dense
                    v-model="reportInterval"
                    label="Reporting Interval *"
                    :options="reportIntervalOptions"
                    :rules="[(val) => !!val || '*Required']"
                />
                <q-select
                    v-if="reportOccurrence.value === 2 && reportOccurrence.value"
                    filled
                    dense
                    v-model="interval"
                    label="Interval (Hours) *"
                    :options="intervalOptions"
                    :rules="[(val) => !!val || '*Required']"
                />
                <q-select
                    v-if="reportOccurrence.value === 4 && reportOccurrence.value"
                    filled
                    dense
                    v-model="days"
                    label="Days *"
                    :options="daysOptions"
                    :rules="[(val) => !!val || '*Required']"
                />
                <q-select
                    v-if="reportOccurrence.value === 5 && reportOccurrence.value || reportOccurrence.value == 6 && reportOccurrence.value"
                    filled
                    dense
                    v-model="day"
                    label="Day *"
                    :options="dayOptions"
                    :rules="[(val) => !!val || '*Required']"
                />
                <q-select
                    v-if="reportOccurrence.value === 6 && reportOccurrence.value"
                    filled
                    dense
                    v-model="month"
                    label="Month *"
                    :options="monthOptions"
                    :rules="[(val) => !!val || '*Required']"
                />
                <q-select
                    v-if="reportName && reportType.value && reportOccurrence.value"
                    stack-label
                    dense
                    clearable
                    filled
                    use-input
                    use-chips
                    multiple
                    hide-dropdown-icon
                    input-debounce="0"
                    new-value-mode="add-unique"
                    v-model="reportRecipients"
                ></q-select>
            </q-card-section>
            <q-card-actions align="right">
                <q-btn label="Save" v-close-popup @click="createReport()" />
            </q-card-actions>
        </q-card>
    </q-dialog>
</template>

<script>
import axios from "axios";
// composable imports
import { ref, onMounted, watch } from "vue";
import { useQuasar, useDialogPluginComponent, date } from "quasar";
import { notifySuccess, notifyError } from "@/utils/notify";

export default {
    name: "CreateReport",
    emits: [...useDialogPluginComponent.emits],
    props: ['endpoint'],

    setup(props) {
        const { dialogRef, onDialogOK, onDialogHide } = useDialogPluginComponent();
        const $q = useQuasar();

        const reportTypeOptions = ref([
            { value: 1, label: 'Antiphishing Activity' },
            { value: 2, label: 'Blocked Applications' },
            { value: 3, label: 'Blocked Websites' },
            { value: 4, label: 'Customer Status Overview' },
            { value: 5, label: 'Data Protection' },
            { value: 6, label: 'Device Control Activity' },
            { value: 7, label: 'Endpoint Modules Status' },
            { value: 8, label: 'Endpoint Protection Status' },
            { value: 9, label: 'Firewall Activity' },
            { value: 10, label: 'License Status' },
            { value: 12, label: 'Malware Status' },
            { value: 13, label: 'Monthly License Usage' },
            { value: 14, label: 'Network Status' },
            { value: 15, label: 'On demand scanning' },
            { value: 16, label: 'Policy Compliance' },
            { value: 17, label: 'Security Audit' },
            { value: 18, label: 'Security Server Status' },
            { value: 19, label: 'Top 10 Detected Malware' },
            { value: 20, label: 'Top 10 Infected Companies' },
            { value: 21, label: 'Top 10 Infected Endpoints' },
            { value: 22, label: 'Update Status' },
            { value: 23, label: 'Upgrade Status' },
            { value: 24, label: 'AWS Monthly Usage' },
            { value: 29, label: 'Email Security Usage' },
            { value: 30, label: 'Endpoint Encryption Status' },
            { value: 31, label: 'HyperDetect Activity' },
            { value: 32, label: 'Network Patch Status' },
            { value: 33, label: 'Sandbox Analyzer Failed Submissions' },
            { value: 34, label: 'Network Incidents' },
        ])
        const intervalOptions = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24]
        const dayOptions = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31]
        const reportOccurrenceOptions = ref([{ value: 2, label: 'Hourly' }, { value: 3, label: 'Daily' }, { value: 4, label: 'Weekly' }, { value: 5, label: 'Monthly' }])
        const reportIntervalOptions = ref([{ value: 0, label: 'Today' },
        { value: 1, label: 'Last day' },
        { value: 2, label: 'This week' },
        { value: 3, label: 'Last week' },
        { value: 4, label: 'This month' },
        { value: 5, label: 'Last month' },
        { value: 6, label: 'Last 2 months' },
        { value: 7, label: 'Last 3 months' }])
        const daysOptions = ref([{ value: 0, label: 'Sunday' }, { value: 1, label: 'Monday' }, { value: 2, label: 'Tuesday' }, { value: 3, label: 'Wedensday' }, { value: 4, label: 'Thursday' }, { value: 5, label: 'Friday' }, { value: 6, label: 'Saturday' }])
        const reportName = ref("")
        const reportType = ref("")
        const reportOccurrence = ref("")
        const interval = ref("")
        const reportInterval = ref("")
        const days = ref("")
        const day = ref("")
        const monthOptions = ref([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12])
        const month = ref('')
        const reportRecipients = ref([])

        function createReport() {
            let now = new Date();
            const formattedString = date.formatDate(now, 'h:m').split(':')

            let data = {
                name: reportName.value,
                type: reportType.value.value,
                occurrence: reportOccurrence.value.value,
                interval: interval.value ? interval.value : null,
                reportingInterval: reportInterval.value ? reportInterval.value.value : null,
                days: days.value ? days.value.value : null,
                day: reportOccurrence.value.value === 5 || reportOccurrence.value.value === 6 ? day.value : null,
                month: reportOccurrence.value.value === 6 ? month.value.value : null,
                startHour: reportOccurrence.value.value === 3 || reportOccurrence.value.value === 4 || reportOccurrence.value.value === 5 ? formattedString[0] : null,
                startMinute: reportOccurrence.value.value === 3 || reportOccurrence.value.value === 4 || reportOccurrence.value.value === 5 ? formattedString[1] : null,
                reportRecipients: reportRecipients.value
            }

            axios
                .post(`/bitdefender/reports/create/` + props.endpoint.id + `/`, data)
                .then(r => {
                    console.log(r.data)
                    if (r.data.error) {
                        if (r.data.error.data.details === 'Validation exception.') {
                            notifyError(r.data.error.data.details + ' You may not have access to the feature you are trying to generate a report for.')

                        } else {
                            notifyError(r.data.error.data.details)
                        }
                    } else {
                        notifySuccess('The report has been created for Bitdefender GravityZone')
                    }
                })
                .catch(e => {
                    console.log(e.response.data)
                });
        }

        watch([reportOccurrence, reportInterval, reportType], ([newOccurrence, newReportInterval, newType], [prevOccurrence, prevReportInterval, prevType]) => {
            console.log(newOccurrence, newReportInterval, newType)

            if (newOccurrence.value === 2) {
                reportIntervalOptions.value = [{ value: 0, label: 'Today' }]
            } else if (newOccurrence.value === 3) {
                reportIntervalOptions.value = [{ value: 0, label: 'Today' },
                { value: 1, label: 'Last day' },
                { value: 2, label: 'This week' }]
            } else if (newOccurrence.value === 4) {
                reportIntervalOptions.value = [{ value: 0, label: 'Today' },
                { value: 1, label: 'Last day' },
                { value: 2, label: 'This week' },
                { value: 3, label: 'Last week' },
                { value: 4, label: 'This month' }]
            } else if (newOccurrence.value === 5) {
                reportIntervalOptions.value = [{ value: 0, label: 'Today' },
                { value: 1, label: 'Last day' },
                { value: 2, label: 'This week' },
                { value: 3, label: 'Last week' },
                { value: 4, label: 'This month' },
                { value: 5, label: 'Last month' },
                { value: 6, label: 'Last 2 months' },
                { value: 7, label: 'Last 3 months' }]
            }
            // } else if (newOccurrence.value === 3) {
            //     reportIntervalOptions.value = []
            //     reportIntervalOptions.value = [{ value: 0, label: 'Today' },
            //     { value: 1, label: 'Last day' },
            //     { value: 2, label: 'This week' }]

            // } else if (newOccurrence.value === 4) {
            //     reportIntervalOptions.value = []
            //     reportIntervalOptions.value = [{ value: 0, label: 'Today' },
            //     { value: 1, label: 'Last day' },
            //     { value: 2, label: 'This week' },
            //     { value: 3, label: 'Last week' },
            //     { value: 4, label: 'This month' }]
            // } else if (newOccurrence.value === 5 && newType.value !== 13 || newOccurrence.value === 5 && newType.value !== 24 || newOccurrence.value === 5 && newType.value !== 29) {
            //     reportIntervalOptions.value = []
            //     reportIntervalOptions.value = [{ value: 0, label: 'Today' },
            //     { value: 1, label: 'Last day' },
            //     { value: 2, label: 'This week' },
            //     { value: 3, label: 'Last week' },
            //     { value: 4, label: 'This month' },
            //     { value: 5, label: 'Last month' },
            //     { value: 6, label: 'Last 2 months' },
            //     { value: 7, label: 'Last 3 months' }]
            // } else if (newOccurrence.value === 5 && newType.value === 13 || newOccurrence.value === 5 && newType.value === 24 || newOccurrence.value === 5 && newType.value === 29) {
            //     console.log("in")
            //     reportOccurrenceOptions.value = []
            //     reportIntervalOptions.value = []
            //     reportOccurrenceOptions.value = [{ value: 4, label: 'Weekly' }]
            //     if (reportOccurrence.value)
            //         reportIntervalOptions.value = [{ value: 4, label: 'This month' }]

            // } else if (newOccurrence.value === 5 && newType.value === 13 || newOccurrence.value === 5 && newType.value === 24 || newOccurrence.value === 5 && newType.value === 29) {
            //     reportOccurrenceOptions.value = []
            //     reportIntervalOptions.value = []
            //     reportOccurrenceOptions.value = [{ value: 4, label: 'Weekly' }, { value: 5, label: 'Monthly' }]
            //     reportIntervalOptions.value = [{ value: 4, label: 'This month' }, { value: 5, label: 'Last month' },]


            // }

        });

        // watch(report, (val) => {
        //     if (selected.value.length > 0) {
        //         actionBtnDisabled.value = false
        //     } else {
        //         actionBtnDisabled.value = true
        //     }
        // })

        return {
            reportName,
            reportType,
            reportTypeOptions,
            reportOccurrence,
            reportOccurrenceOptions,
            reportInterval,
            reportIntervalOptions,
            interval,
            intervalOptions,
            days,
            daysOptions,
            day,
            dayOptions,
            reportRecipients,
            createReport,
            // quasar dialog plugin
            dialogRef,
            onDialogHide,
        }
    }
}
</script>