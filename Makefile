#
# Convenience Makefile
# Useful reference: https://makefiletutorial.com

GIT_SHA := $(shell git rev-parse --short HEAD)
VERSION ?= 0.0.0-dev0.$(GIT_SHA)

SRCDIR := $(CURDIR)/src
DISTDIR := $(CURDIR)/.dist
PKIDIR := $(CURDIR)/var/pki
TMPDIR := $(CURDIR)/.tmp
BINDIR := $(CURDIR)/bin
ETCDIR := $(CURDIR)/etc
VENVDIR := $(CURDIR)/.venv
ANSIBLEDIR := $(SRCDIR)/ansible
HELMDIR := $(SRCDIR)/helm
CHARTDIR := $(DISTDIR)/charts

CLUSTER_VARS := $(CURDIR)/cluster.yaml
CLUSTER_NAME := $(shell hostname -s)
NAMESPACE := kube-eng

CERT_MANAGER_SOURCES := $(shell find $(HELMDIR)/kube-eng-cert-manager)
CERT_MANAGER_CHART := $(CHARTDIR)/kube-eng-cert-manager-$(VERSION).tgz
EDGE_SOURCES := $(shell find $(HELMDIR)/kube-eng-edge)
EDGE_CHART := $(CHARTDIR)/kube-eng-edge-$(VERSION).tgz
PROMETHEUS_SOURCES := $(shell find $(HELMDIR)/kube-eng-prometheus)
PROMETHEUS_CHART := $(CHARTDIR)/kube-eng-prometheus-$(VERSION).tgz
ALLOY_SOURCES := $(shell find $(HELMDIR)/kube-eng-alloy)
ALLOY_CHART := $(CHARTDIR)/kube-eng-alloy-$(VERSION).tgz
LOKI_SOURCES := $(shell find $(HELMDIR)/kube-eng-loki)
LOKI_CHART := $(CHARTDIR)/kube-eng-loki-$(VERSION).tgz
KEYCLOAK_OPERATOR_SOURCES := $(shell find $(HELMDIR)/kube-eng-keycloak-operator)
KEYCLOAK_OPERATOR_CHART := $(CHARTDIR)/kube-eng-keycloak-operator-$(VERSION).tgz
KEYCLOAK_SOURCES := $(shell find $(HELMDIR)/kube-eng-keycloak)
KEYCLOAK_CHART := $(CHARTDIR)/kube-eng-keycloak-$(VERSION).tgz
GRAFANA_SOURCES := $(shell find $(HELMDIR)/kube-eng-grafana)
GRAFANA_CHART := $(CHARTDIR)/kube-eng-grafana-$(VERSION).tgz
JAEGER_SOURCES := $(shell find $(HELMDIR)/kube-eng-jaeger)
JAEGER_CHART := $(CHARTDIR)/kube-eng-jaeger-$(VERSION).tgz
JAEGER_V2_SOURCES := $(shell find $(HELMDIR)/kube-eng-jaeger-v2)
JAEGER_V2_CHART := $(CHARTDIR)/kube-eng-jaeger-v2-$(VERSION).tgz
KIALI_SOURCES := $(shell find $(HELMDIR)/kube-eng-kiali)
KIALI_CHART := $(CHARTDIR)/kube-eng-kiali-$(VERSION).tgz

COLLECTION_SOURCES :=$(shell find $(SRCDIR)/ansible/kube_eng)

CHARTS := $(CERT_MANAGER_CHART) $(EDGE_CHART) \
		  $(PROMETHEUS_CHART) $(ALLOY_CHART) $(LOKI_CHART) $(GRAFANA_CHART) \
		  $(KEYCLOAK_OPERATOR_CHART) $(KEYCLOAK_CHART) \
		  $(JAEGER_CHART) $(JAEGER_V2_CHART) \
		  $(KIALI_CHART)
COLLECTION := $(DISTDIR)/mrmat-kube_eng-$(VERSION).tar.gz

ANSIBLE_PLAYBOOK_EXEC = ANSIBLE_PYTHON_INTERPRETER=$(VENVDIR)/bin/python3 \
						$(ansible-playbook) -v -i $(ANSIBLEDIR)/inventory.yml \
							-e @$(CLUSTER_VARS) \
							-e dist_dir=$(DISTDIR) \
							-e pki_dir=$(PKIDIR) \
							-e admin_password="$(shell cat $(admin-password-file))" \
							-e user_id="$(shell whoami)" \
							-e cluster_name=$(CLUSTER_NAME) \
							-e host_tool_kind=$(kind) \
							-e host_tool_istioctl=$(istioctl) \
							-e host_tool_kubectl=$(kubectl) \
							-e host_tool_kustomize=$(kustomize) \
							-e host_tool_docker=$(docker) \
							-e host_tool_named=$(named) \
							-e host_tool_cloud_provider_mdns=$(cloud-provider-mdns) \
							-e chart_cert_manager=$(CERT_MANAGER_CHART) \
							-e chart_edge=$(EDGE_CHART) \
							-e chart_prometheus=$(PROMETHEUS_CHART) \
							-e chart_keycloak_operator=$(KEYCLOAK_OPERATOR_CHART) \
							-e chart_keycloak=$(KEYCLOAK_CHART) \
							-e chart_grafana=$(GRAFANA_CHART) \
							-e chart_jaeger=$(JAEGER_CHART) \
							-e chart_kiali=$(KIALI_CHART) \
							-e chart_alloy=$(ALLOY_CHART) \
							-e chart_loki=$(LOKI_CHART) \
							-e chart_jaeger_v2=$(JAEGER_V2_CHART)


.PHONY: clean dist all collection
clean:
	@rm -rf $(DISTDIR) $(TMPDIR) $(BINDIR) $(DISTDIR)

distclean: clean
	@rm -rf $(VENVDIR)

all: helm
password: $(admin-password)

#
# Dependencies

admin-password-file := $(CURDIR)/.admin-password
kind := /opt/homebrew/bin/kind
istioctl := /opt/homebrew/bin/istioctl
kubectl := /opt/homebrew/bin/kubectl
kustomize := /opt/homebrew/bin/kustomize
helm := /opt/homebrew/bin/helm
cloud-provider-mdns := $(VENVDIR)/bin/cloud-provider-mdns
ansible-galaxy := $(VENVDIR)/bin/ansible-galaxy
ansible-playbook := $(VENVDIR)/bin/ansible-playbook
bind := /opt/homebrew/bin/named
docker := /usr/local/bin/docker
gtar := /opt/homebrew/bin/gtar

deps: $(admin-password-file) $(docker) $(istioctl) $(kubectl) $(kind) \
	  $(helm) $(cloud-provider-mdns) $(ansible-playbook) $(ansible-galaxy) \
	  $(gtar)
	@echo "All deps installed"

$(admin-password-file):
	@echo "$(shell openssl rand -base64 12)" > $@

$(BINDIR) $(TMPDIR) $(DISTDIR) $(CHARTDIR) $(ETCDIR):
	mkdir -p $@

$(VENVDIR):
	python3 -mvenv $(VENVDIR)
	$(VENVDIR)/bin/pip3 install -U pip

$(docker):
	@echo "You must install a container runtime. If it is not docker then adjust its path in the 'docker' variable of the Makefile"
	@exit 1

$(kind):
	brew install kind

$(istioctl):
	brew install istioctl

$(kubectl):
	brew install kubectl

$(kustomize):
	brew install kustomize

$(helm):
	brew install helm

$(bind):
	brew install bind

$(gtar):
	brew install gnu-tar

$(cloud-provider-mdns): $(VENVDIR)
	$(VENVDIR)/bin/pip3 install -U git+https://github.com/MrMatAP/cloud-provider-mdns.git

$(ansible-playbook) $(ansible-galaxy): $(VENVDIR)
	$(VENVDIR)/bin/pip3 install -r $(CURDIR)/requirements.txt

#
# Artefacts

$(COLLECTION): $(COLLECTION_SOURCES) | deps
	rsync -zavuSH --delete --exclude galaxy.yml $(ANSIBLEDIR)/kube_eng $(TMPDIR)/
	cat $(ANSIBLEDIR)/kube_eng/galaxy.yml | sed -e "s/version:.*/version: $(VERSION)/" > $(TMPDIR)/kube_eng/galaxy.yml
	$(ansible-galaxy) collection build -f $(TMPDIR)/kube_eng --output-path $(DISTDIR)
	$(ansible-galaxy) collection install --force $(COLLECTION)

#
# Host infrastructure

host-infra: $(COLLECTION)
	$(helm) repo add jetstack https://charts.jetstack.io
	$(helm) repo add prometheus-community https://prometheus-community.github.io/helm-charts
	$(helm) repo add grafana https://grafana.github.io/helm-charts
	$(helm) repo add open-telemetry https://open-telemetry.github.io/opentelemetry-helm-charts
	$(helm) repo add jaegertracing https://jaegertracing.github.io/helm-charts
	$(helm) repo add kiali https://kiali.org/helm-charts
	$(ANSIBLE_PLAYBOOK_EXEC) mrmat.kube_eng.create_host_infra

host-infra-start: $(COLLECTION)
	$(ANSIBLE_PLAYBOOK_EXEC) --ask-become-pass mrmat.kube_eng.start_host_infra

host-infra-stop: $(COLLECTION)
	$(ANSIBLE_PLAYBOOK_EXEC) --ask-become-pass mrmat.kube_eng.stop_host_infra

#
# Cluster installation

cluster: $(COLLECTION)
	$(helm) repo add jetstack https://charts.jetstack.io
	$(ANSIBLE_PLAYBOOK_EXEC) mrmat.kube_eng.create_cluster

cluster-destroy: $(COLLECTION)
	$(ANSIBLE_PLAYBOOK_EXEC) mrmat.kube_eng.destroy_cluster
#
# Stack

stack: $(COLLECTION) $(CHARTS)
	$(ANSIBLE_PLAYBOOK_EXEC) mrmat.kube_eng.create_stack

#
# Charts

charts: $(CHARTS)

$(CERT_MANAGER_CHART): $(CERT_MANAGER_SOURCES) $(CHARTDIR)
	$(helm) dep update $(HELMDIR)/kube-eng-cert-manager --skip-refresh
	$(helm) package --version $(VERSION) --destination $(CHARTDIR) $(HELMDIR)/kube-eng-cert-manager

$(EDGE_CHART): $(EDGE_SOURCES) $(CHARTDIR)
	$(helm) dep update $(HELMDIR)/kube-eng-edge --skip-refresh
	$(helm) package --version $(VERSION) --destination $(CHARTDIR) $(HELMDIR)/kube-eng-edge

$(PROMETHEUS_CHART): $(PROMETHEUS_SOURCES) $(CHARTDIR)
	$(helm) dep update $(HELMDIR)/kube-eng-prometheus --skip-refresh
	$(helm) package --version $(VERSION) --destination $(CHARTDIR) $(HELMDIR)/kube-eng-prometheus

$(ALLOY_CHART): $(ALLOY_SOURCES) $(CHARTDIR)
	$(helm) dep update $(HELMDIR)/kube-eng-alloy --skip-refresh
	$(helm) package --version $(VERSION) --destination $(CHARTDIR) $(HELMDIR)/kube-eng-alloy

$(LOKI_CHART): $(LOKI_SOURCES) $(CHARTDIR)
	$(helm) dep update $(HELMDIR)/kube-eng-loki --skip-refresh
	$(helm) package --version $(VERSION) --destination $(CHARTDIR) $(HELMDIR)/kube-eng-loki

$(KEYCLOAK_OPERATOR_CHART): $(KEYCLOAK_OPERATOR_SOURCES) $(CHARTDIR)
	$(helm) package --version $(VERSION) --destination $(CHARTDIR) $(HELMDIR)/kube-eng-keycloak-operator

$(KEYCLOAK_CHART): $(KEYCLOAK_SOURCES) $(CHARTDIR)
	$(helm) package --version $(VERSION) --destination $(CHARTDIR) $(HELMDIR)/kube-eng-keycloak

$(GRAFANA_CHART): $(GRAFANA_SOURCES) $(CHARTDIR)
	$(helm) dep update $(HELMDIR)/kube-eng-grafana --skip-refresh
	$(helm) package --version $(VERSION) --destination $(CHARTDIR) $(HELMDIR)/kube-eng-grafana

$(JAEGER_CHART): $(JAEGER_SOURCES) $(CHARTDIR)
	$(helm) dep update $(HELMDIR)/kube-eng-jaeger --skip-refresh
	$(helm) package --version $(VERSION) --destination $(CHARTDIR) $(HELMDIR)/kube-eng-jaeger

$(JAEGER_V2_CHART): $(JAEGER_V2_SOURCES) $(CHARTDIR)
	$(helm) package --version $(VERSION) --destination $(CHARTDIR) $(HELMDIR)/kube-eng-jaeger-v2

$(KIALI_CHART): $(KIALI_SOURCES) $(CHARTDIR)
	$(helm) dep update $(HELMDIR)/kube-eng-kiali --skip-refresh
	$(helm) package --version $(VERSION) --destination $(CHARTDIR) $(HELMDIR)/kube-eng-kiali
