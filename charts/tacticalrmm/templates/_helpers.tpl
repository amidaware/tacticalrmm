{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "tacticalrmm.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "tacticalrmm.labels" -}}
helm.sh/chart: {{ include "tacticalrmm.chart" . }}
{{ include "tacticalrmm.selectorLabels" . }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "tacticalrmm.selectorLabels" -}}
app.kubernetes.io/name: tacticalrmm
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}
