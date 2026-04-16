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


{{/*
Common envFrom block for base services (backend, nats, websockets, celery, celerybeat)
*/}}
{{- define "tacticalrmm.baseEnvFrom" -}}
- configMapRef:
    name: tactical-backend
- configMapRef:
    name: tactical-postgres
- configMapRef:
    name: tactical-redis
- secretRef:
    name: tactical-postgres
{{- end }}

{{/*
SECRET_KEY env var injected from a K8s Secret
*/}}
{{- define "tacticalrmm.secretKeyEnv" -}}
- name: SECRET_KEY
  valueFrom:
    secretKeyRef:
      name: {{ .Values.tactical.existingSecret | default "tactical-backend" }}
      key: {{ .Values.tactical.secretKeyKey | default "SECRET_KEY" }}
{{- end }}
