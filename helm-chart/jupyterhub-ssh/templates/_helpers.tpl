{{/*
name is used to set the app.kubernetes.io/name label and influences the fullname
function if fullnameOverride isn't specified.
*/}}
{{- define "jupyterhub-ssh.name" -}}
{{- .Values.nameOverride | default .Chart.Name | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
fullname is used to name k8s resources either directly based on fullnameOverride,
or by combining the helm release name with the chart name. If the release name
contains the chart name, the chart name won't be repeated.
*/}}
{{- define "jupyterhub-ssh.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := .Values.nameOverride | default .Chart.Name }}
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
chart is used to set the helm.sh/chart label.
*/}}
{{- define "jupyterhub-ssh.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
labels are selectorLabels and other common labels k8s resources get
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
selectorLabels are used to taget specific resources, such as how Services and
Deployment resources target Pods. Changes to this will be breaking changes.
Deployment's matchLabels field are for example immutable and will require the
resource to be recreated. Handling breaking changes was quite easy to do with
`helm2 upgrade --force` but require manual intervention in `helm3 upgrade` by
manually deleting the Deployment resources first.
*/}}
{{- define "jupyterhub-ssh.selectorLabels" -}}
app.kubernetes.io/name: {{ include "jupyterhub-ssh.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{- define "jupyterhub-ssh.sftp.selectorLabels" -}}
{{ include "jupyterhub-ssh.selectorLabels" . }}
app.kubernetes.io/component: sftp
{{- end }}

{{- define "jupyterhub-ssh.ssh.selectorLabels" -}}
{{ include "jupyterhub-ssh.selectorLabels" . }}
app.kubernetes.io/component: ssh
{{- end }}

{{- /*
This named template is used to return the explicitly set hostKey, lookup an
previously set hostKey, or generate and return a new hostKey.
*/}}
{{- define "jupyterhub-ssh.hostKey" -}}
    {{- if .Values.hostKey }}
        {{- .Values.hostKey }}
    {{- else }}
        {{- $k8s_state := lookup "v1" "Secret" .Release.Namespace (include "jupyterhub-ssh.ssh.fullname" .) | default (dict "data" (dict)) }}
        {{- if hasKey $k8s_state.data "hostKey" }}
            {{- index $k8s_state.data "hostKey" }}
        {{- else }}
            {{- /* While ed25519 is preferred, using it with jupyterhub-sftp seem to fail. */}}
            {{- genPrivateKey "rsa" }}
        {{- end }}
    {{- end }}
{{- end }}
