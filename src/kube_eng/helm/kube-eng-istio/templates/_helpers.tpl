
{{/* Common labels */}}
{{ define "common.labels" }}
app: istio
version: {{ .Chart.AppVersion }}
app.kubernetes.io/part-of: stack
app.kubernetes.io/component: istio
app.kubernetes.io/version: {{ .Chart.AppVersion }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{ end }}
