{{/*
Expand the name of the chart.
*/}}
{{- define "jupyterhub-ssh.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "jupyterhub-ssh.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{- define "jupyterhub-ssh.sftp.fullname" -}}
{{ include "jupyterhub-ssh.fullname" . }}-sftp
{{- end }}

{{- define "jupyterhub-ssh.ssh.fullname" -}}
{{ include "jupyterhub-ssh.fullname" . }}-ssh
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "jupyterhub-ssh.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "jupyterhub-ssh.labels" -}}
helm.sh/chart: {{ include "jupyterhub-ssh.chart" . }}
{{ include "jupyterhub-ssh.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{- define "jupyterhub-ssh.sftp.labels" -}}
{{ include "jupyterhub-ssh.labels" . }}
app.kubernetes.io/component: sftp
{{- end }}

{{- define "jupyterhub-ssh.ssh.labels" -}}
{{ include "jupyterhub-ssh.labels" . }}
app.kubernetes.io/component: ssh
{{- end }}

{{/*
Selector labels
*/}}
{{- define "jupyterhub-ssh.selectorLabels" -}}
app.kubernetes.io/name: {{ include "jupyterhub-ssh.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{- define "jupyterhub-ssh.sftp.selectorLabels" -}}
{{ include "jupyterhub-ssh.selectorLabels" . }}
app.kubernetes.io/component: sftp-server
{{- end }}

{{- define "jupyterhub-ssh.ssh.selectorLabels" -}}
{{ include "jupyterhub-ssh.selectorLabels" . }}
app.kubernetes.io/component: ssh-server
{{- end }}
