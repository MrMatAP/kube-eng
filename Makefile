#
# Convenience Makefile
# Useful reference: https://makefiletutorial.com

GIT_SHA := $(shell git rev-parse --short HEAD)
VERSION ?= 0.0.0-dev0.$(GIT_SHA)

SRCDIR := $(CURDIR)/src
DISTDIR := $(CURDIR)/.dist
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


PROMETHEUS_SOURCES := $(shell find $(HELMDIR)/kube-eng-prometheus)
PROMETHEUS_CHART := $(CHARTDIR)/kube-eng-prometheus-$(VERSION).tgz
POSTGRES_SOURCES := $(shell find $(HELMDIR)/kube-eng-postgres)
POSTGRES_CHART := $(CHARTDIR)/kube-eng-postgres-$(VERSION).tgz
KEYCLOAK_SOURCES := $(shell find $(HELMDIR)/kube-eng-keycloak)
KEYCLOAK_CHART := $(CHARTDIR)/kube-eng-keycloak-$(VERSION).tgz
GRAFANA_SOURCES := $(shell find $(HELMDIR)/kube-eng-grafana)
GRAFANA_CHART := $(CHARTDIR)/kube-eng-grafana-$(VERSION).tgz
JAEGER_SOURCES := $(shell find $(HELMDIR)/kube-eng-jaeger)
JAEGER_CHART := $(CHARTDIR)/kube-eng-jaeger-$(VERSION).tgz
KIALI_SOURCES := $(shell find $(HELMDIR)/kube-eng-kiali)
KIALI_CHART := $(CHARTDIR)/kube-eng-kiali-$(VERSION).tgz

COLLECTION_SOURCES :=$(shell find $(SRCDIR)/ansible/kube_eng)

CHARTS := $(PROMETHEUS_CHART) $(KEYCLOAK_CHART) \
		  $(GRAFANA_CHART) $(JAEGER_CHART) $(KIALI_CHART) \
		  $(ALLOY_CHART)
COLLECTION := $(DISTDIR)/mrmat-kube_eng-$(VERSION).tar.gz

ANSIBLE_PLAYBOOK_EXEC = ANSIBLE_PYTHON_INTERPRETER=$(VENVDIR)/bin/python3 \
						$(ansible-playbook) -v -i $(ANSIBLEDIR)/inventory.yml \
							-e @$(CLUSTER_VARS) \
							-e dist_dir=$(DISTDIR) \
							-e admin_password="$(shell cat $(admin-password-file))" \
							-e cloud_provider_mdns=$(cloud-provider-mdns) \
							-e user_id="$(shell whoami)" \
							-e cluster_name=$(CLUSTER_NAME) \
							-e prometheus_chart=$(PROMETHEUS_CHART) \
							-e keycloak_chart=$(KEYCLOAK_CHART) \
							-e grafana_chart=$(GRAFANA_CHART) \
							-e jaeger_chart=$(JAEGER_CHART) \
							-e kiali_chart=$(KIALI_CHART) \
							-e cert_manager_chart=$(CERT_MANAGER_CHART)


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
	$(ANSIBLE_PLAYBOOK_EXEC) mrmat.kube_eng.create_host_infra

host-infra-start: $(COLLECTION)
	$(ANSIBLE_PLAYBOOK_EXEC) --ask-become-pass mrmat.kube_eng.start_host_infra

host-infra-stop: $(COLLECTION)
	$(ANSIBLE_PLAYBOOK_EXEC) --ask-become-pass mrmat.kube_eng.stop_host_infra

#
# Airgap

preheat: $(COLLECTION)
	$(ANSIBLE_PLAYBOOK_EXEC) mrmat.kube_eng.preheat_registry

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

$(PROMETHEUS_CHART): $(PROMETHEUS_SOURCES) $(CHARTDIR)
	$(helm) dep update $(HELMDIR)/kube-eng-prometheus --skip-refresh
	$(helm) package --version $(VERSION) --destination $(CHARTDIR) $(HELMDIR)/kube-eng-prometheus

$(KEYCLOAK_CHART): $(KEYCLOAK_SOURCES) $(CHARTDIR)
	$(helm) package --version $(VERSION) --destination $(CHARTDIR) $(HELMDIR)/kube-eng-keycloak

$(GRAFANA_CHART): $(GRAFANA_SOURCES) $(CHARTDIR)
	$(helm) dep update $(HELMDIR)/kube-eng-grafana --skip-refresh
	$(helm) package --version $(VERSION) --destination $(CHARTDIR) $(HELMDIR)/kube-eng-grafana

$(JAEGER_CHART): $(JAEGER_SOURCES) $(CHARTDIR)
	$(helm) dep update $(HELMDIR)/kube-eng-jaeger --skip-refresh
	$(helm) package --version $(VERSION) --destination $(CHARTDIR) $(HELMDIR)/kube-eng-jaeger

$(KIALI_CHART): $(KIALI_SOURCES) $(CHARTDIR)
	$(helm) dep update $(HELMDIR)/kube-eng-kiali --skip-refresh
	$(helm) package --version $(VERSION) --destination $(CHARTDIR) $(HELMDIR)/kube-eng-kiali
