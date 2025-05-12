
{{/* Common labels */}}
{{ define "common.labels" }}
app: edge
version: {{ .Chart.AppVersion }}
app.kubernetes.io/part-of: stack
app.kubernetes.io/component: edge
app.kubernetes.io/version: {{ .Chart.AppVersion }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{ end }}
