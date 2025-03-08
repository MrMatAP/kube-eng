#
# Convenience Makefile
# Useful reference: https://makefiletutorial.com

GIT_SHA := $(shell git rev-parse --short HEAD)
VERSION ?= 0.0.0-dev0.$(GIT_SHA)

SRCDIR := $(CURDIR)/src
DISTDIR := $(CURDIR)/.dist
TMPDIR := $(CURDIR)/.tmp

BINDIR := $(CURDIR)/bin
VENVDIR := $(CURDIR)/.venv
ANSIBLEDIR := $(SRCDIR)/ansible
HELMDIR := $(SRCDIR)/helm

CLUSTER_VARS := $(CURDIR)/cluster.yaml
CLUSTER_NAME := $(shell hostname -s)
CLUSTER_CONFIG := $(CURDIR)/var/kind-large.yaml
NAMESPACE := kube-eng


PROMETHEUS_SOURCES := $(shell find $(HELMDIR)/kube-eng-prometheus)
PROMETHEUS_CHART := $(DISTDIR)/kube-eng-prometheus-$(VERSION).tgz
POSTGRES_SOURCES := $(shell find $(HELMDIR)/kube-eng-postgres)
POSTGRES_CHART := $(DISTDIR)/kube-eng-postgres-$(VERSION).tgz
KEYCLOAK_SOURCES := $(shell find $(HELMDIR)/kube-eng-keycloak)
KEYCLOAK_CHART := $(DISTDIR)/kube-eng-keycloak-$(VERSION).tgz
GRAFANA_SOURCES := $(shell find $(HELMDIR)/kube-eng-grafana)
GRAFANA_CHART := $(DISTDIR)/kube-eng-grafana-$(VERSION).tgz
KIALI_SOURCES := $(shell find $(HELMDIR)/kube-eng-kiali)
KIALI_CHART := $(DISTDIR)/kube-eng-kiali-$(VERSION).tgz
COLLECTION_SOURCES :=$(shell find $(SRCDIR)/ansible/kube_eng)

CHARTS := $(PROMETHEUS_CHART) $(POSTGRES_CHART )$(KEYCLOAK_CHART) $(GRAFANA_CHART) $(KIALI_CHART)
COLLECTION := $(DISTDIR)/mrmat-kube_eng-$(VERSION).tar.gz

CLOUD_PROVIDER_KIND_URL := https://github.com/kubernetes-sigs/cloud-provider-kind/releases/download/v0.6.0/cloud-provider-kind_0.6.0_darwin_arm64.tar.gz


.PHONY: clean dist all collection
clean:
	@rm -rf $(DISTDIR) $(TMPDIR) $(BINDIR) $(VENVDIR) $(DISTDIR)

all: helm
password: $(admin-password)
prometheus: $(PROMETHEUS_CHART)
postgres: $(POSTGRES_CHART)
keycloak: $(KEYCLOAK_CHART)
grafana: $(GRAFANA_CHART)
kiali: $(KIALI_CHART)

#
# Dependencies

admin-password-file := $(CURDIR)/.admin-password
kind := /opt/homebrew/bin/kind
istioctl := /opt/homebrew/bin/istioctl
kubectl := /opt/homebrew/bin/kubectl
cloud-provider-kind := $(BINDIR)/cloud-provider-kind
cloud-provider-mdns := $(VENVDIR)/bin/cloud-provider-mdns
ansible-galaxy := $(VENVDIR)/bin/ansible-galaxy
ansible-playbook := $(VENVDIR)/bin/ansible-playbook
docker := /usr/local/bin/docker

deps: $(admin-password-file) $(docker) $(istioctl) $(kubectl) $(kind) $(cloud-provider-kind) $(cloud-provider-mdns) $(ansible-playbook) $(ansible-galaxy)
	@echo "All deps installed"

$(admin-password-file):
	@echo "$(shell openssl rand -base64 12)" > $@

$(BINDIR) $(TMPDIR) $(DISTDIR):
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

$(cloud-provider-kind): | $(TMPDIR) $(BINDIR)
	curl -Lo $(TMPDIR)/cloud-provider-kind.tar.gz $(CLOUD_PROVIDER_KIND_URL)
	tar xfv $(TMPDIR)/cloud-provider-kind.tar.gz -C $(TMPDIR) cloud-provider-kind
	mv $(TMPDIR)/cloud-provider-kind $@

$(cloud-provider-mdns): $(VENVDIR)
	$(VENVDIR)/bin/pip3 install -U git+https://github.com/MrMatAP/cloud-provider-mdns.git

$(ansible-playbook) $(ansible-galaxy): $(VENVDIR)
	$(VENVDIR)/bin/pip3 install -r $(CURDIR)/requirements.txt

#
# Artefacts

collection: $(COLLECTION)

$(COLLECTION): $(COLLECTION_SOURCES) | deps
	rsync -zavuSH --delete --exclude galaxy.yml $(ANSIBLEDIR)/kube_eng $(TMPDIR)/
	cat $(ANSIBLEDIR)/kube_eng/galaxy.yml | sed -e "s/version:.*/version: $(VERSION)/" > $(TMPDIR)/kube_eng/galaxy.yml
	$(ansible-galaxy) collection build -f $(TMPDIR)/kube_eng --output-path $(DISTDIR)
	$(ansible-galaxy) collection install --force $(COLLECTION)

#
# Airgap Registry

registry: deps
	$(ansible-playbook) -i $(ANSIBLEDIR)/inventory.yml -$(ANSIBLEDIR)/kube-eng-registry.yml

#
# Cluster installation

cluster: $(kind) $(COLLECTION)
	ANSIBLE_PYTHON_INTERPRETER=$(VENVDIR)/bin/python3 $(ansible-playbook) -v -i $(ANSIBLEDIR)/inventory.yml -e distdir=$(DISTDIR) -e @$(CLUSTER_VARS) mrmat.kube_eng.create_cluster

cluster-destroy: $(kind) $(COLLECTION)
	ANSIBLE_PYTHON_INTERPRETER=$(VENVDIR)/bin/python3 $(ansible-playbook) -v -i $(ANSIBLEDIR)/inventory.yml -e distdir=$(DISTDIR) -e @$(CLUSTER_VARS) mrmat.kube_eng.destroy_cluster

istio: cluster
	istioctl install -y --set profile=minimal
	kubectl apply -f https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.2.1/standard-install.yaml

istio-alpha: cluster
	istioctl install \
		-y \
		--set values.pilot.env.PILOT_ENABLE_ALPHA_GATEWAY_API=true \
		--set profile=minimal
	kubectl apply -f https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.2.1/experimental-install.yaml

edge-gateway:
	kubectl create ns edge
	kubectl label ns edge istio-injection=enabled
	kubectl apply -f var/gateway-api-edge.yaml

prometheus: $(PROMETHEUS_CHART)
	helm upgrade \
		kube-eng-prometheus \
		$(PROMETHEUS_CHART) \
		--install \
		--wait \
		--create-namespace \
		--namespace $(NAMESPACE)
	helm test kube-eng-prometheus --namespace $(NAMESPACE)
	kubectl delete po -n $(NAMESPACE) kube-eng-prometheus-test

prometheus-uninstall:
	helm uninstall kube-eng-prometheus --namespace $(NAMESPACE)

postgres: $(POSTGRES_CHART)
	helm upgrade \
		kube-eng-postgres \
		$(POSTGRES_CHART) \
		--install \
		--wait \
		--create-namespace \
		--namespace $(NAMESPACE) \
		--set pod.admin_password="$(shell cat $(admin-password))"

postgres-uninstall:
	helm uninstall kube-eng-postgres --namespace $(NAMESPACE)

keycloak: $(KEYCLOAK_CHART) $(admin-password)
	ansible-playbook \
		-e admin_password="$(shell cat $(admin-password))" \
		ansible/kube-eng-keycloak-preinstall.yml
	helm upgrade \
		kube-eng-keycloak \
		$(KEYCLOAK_CHART) \
		--install \
		--wait \
		--create-namespace \
		--namespace $(NAMESPACE) \
		--set pod.admin_password="$(shell cat $(admin-password))" \
		--set pod.db_password="$(shell cat $(admin-password))"
	helm test kube-eng-keycloak --namespace $(NAMESPACE)
	kubectl delete po -n $(NAMESPACE) kube-eng-keycloak-test
	ansible-playbook \
		-e admin_password="$(shell cat $(admin-password))" \
		ansible/kube-eng-keycloak-postinstall.yml

keycloak-uninstall:
	helm uninstall kube-eng-keycloak --namespace $(NAMESPACE)

grafana: $(GRAFANA_CHART)
	ansible-playbook \
		-e admin_password="$(shell cat $(admin_password))" \
		ansible/kube-eng-grafana-preinstall.yml
	helm upgrade \
		kube-eng-grafana \
		$(GRAFANA_CHART) \
		--install \
		--wait \
		--create-namespace \
		--namespace $(NAMESPACE) \
		--set grafana.envRenderSecret.GF_AUTH_GENERIC_OAUTH_CLIENT_ID=ke_grafana \
		--set grafana.envRenderSecret.GF_AUTH_GENERIC_OAUTH_CLIENT_SECRET="$(shell cat $(admin_password))" \
		--set grafana.adminUser=admin \
		--set grafana.adminPassword="$(shell cat $(admin_password))"
	helm test kube-eng-grafana --namespace $(NAMESPACE)
	kubectl delete po -n $(NAMESPACE) kube-eng-grafana-test
	ansible-playbook \
		-e admin_password="$(shell cat $(admin_password))" \
		ansible/kube-eng-grafana-postinstall.yml

grafana-uninstall:
	helm uninstall kube-eng-grafana --namespace $(NAMESPACE)

kiali: $(KIALI_CHART)
	#ansible-playbook \
	#	-e admin_password="$(shell cat $(ADMIN_PASSWORD))" \
	#	ansible/kube-eng-kiali-preinstall.yml
	#kubectl create secret generic -n $(NAMESPACE) kiali --from-literal="oidc-secret=$(shell cat $(ADMIN_PASSWORD))"
	helm upgrade \
		kube-eng-kiali \
		$(KIALI_CHART) \
		--install \
		--wait \
		--create-namespace \
		--namespace $(NAMESPACE) \
		--set kiali.cr.spec.external_services.grafana.auth.password="$(shell cat $(admin_password))"
	helm test kube-eng-kiali --namespace $(NAMESPACE)
	kubectl delete po -n $(NAMESPACE) kube-eng-kiali-test

kiali-uninstall:
	helm uninstall kube-eng-kiali --namespace $(NAMESPACE)

#
# Charts

charts: $(CHARTS)

$(PROMETHEUS_CHART): $(PROMETHEUS_SOURCES) $(DISTDIR)
	helm dep update $(HELMDIR)/kube-eng-prometheus --skip-refresh
	helm package --version $(VERSION) --destination $(DISTDIR) $(HELMDIR)/kube-eng-prometheus

$(POSTGRES_CHART): $(POSTGRES_SOURCES) $(DISTDIR)
	helm package --version $(VERSION) --destination $(DISTDIR) $(HELMDIR)/kube-eng-postgres

$(KEYCLOAK_CHART): $(KEYCLOAK_SOURCES) $(DISTDIR)
	helm package --version $(VERSION) --destination $(DISTDIR) $(HELMDIR)/kube-eng-keycloak

$(GRAFANA_CHART): $(GRAFANA_SOURCES) $(DISTDIR)
	helm dep update $(HELMDIR)/kube-eng-grafana --skip-refresh
	helm package --version $(VERSION) --destination $(DISTDIR) $(HELMDIR)/kube-eng-grafana

$(KIALI_CHART): $(KIALI_SOURCES) $(DISTDIR)
	helm dep update $(HELMDIR)/kube-eng-kiali --skip-refresh
	helm package --version $(VERSION) --destination $(DISTDIR) $(HELMDIR)/kube-eng-kiali

#
# Utilities


