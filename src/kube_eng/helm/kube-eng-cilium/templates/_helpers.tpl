
{{/* Common labels */}}
{{ define "common.labels" }}
app: cilium
version: {{ .Chart.AppVersion }}
app.kubernetes.io/part-of: stack
app.kubernetes.io/component: cilium
app.kubernetes.io/version: {{ .Chart.AppVersion }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{ end }}
