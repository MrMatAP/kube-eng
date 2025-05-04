
{{/* Common labels */}}
{{ define "common.labels" }}
app: keycloak
version: {{ .Chart.AppVersion }}
app.kubernetes.io/part-of: stack
app.kubernetes.io/component: keycloak
app.kubernetes.io/version: {{ .Chart.AppVersion }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{ end }}
