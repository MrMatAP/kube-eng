
{{/* Common labels */}}
{{ define "common.labels" }}
app: tempo
version: {{ .Chart.AppVersion }}
app.kubernetes.io/name: tempo
app.kubernetes.io/component: kube-eng
app.kubernetes.io/version: {{ .Chart.AppVersion }}
app.kubernetes.io/part-of: kube-eng-stack
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version | replace "+" "_" }}
{{ end }}
