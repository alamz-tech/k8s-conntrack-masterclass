{{/*
Expand the name of the chart.
*/}}
{{- define "checkout-service.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "checkout-service.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "checkout-service.labels" -}}
helm.sh/chart: {{ include "checkout-service.name" . }}
app.kubernetes.io/name: {{ include "checkout-service.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
tier: payment-processing
{{- end }}

{{/*
Selector labels
*/}}
{{- define "checkout-service.selectorLabels" -}}
app.kubernetes.io/name: {{ include "checkout-service.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}
