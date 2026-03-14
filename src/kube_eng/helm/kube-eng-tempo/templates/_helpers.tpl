
{{/* Common labels */}}
{{ define "common.labels" }}
app: prometheus
version: {{ .Chart.AppVersion }}
app.kubernetes.io/part-of: stack
app.kubernetes.io/component: prometheus
app.kubernetes.io/version: {{ .Chart.AppVersion }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{ end }}
