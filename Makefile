#
# Convenience Makefile
# Useful reference: https://makefiletutorial.com

GIT_SHA := $(shell git rev-parse --short HEAD)
VERSION ?= 0.0.0-dev0.$(GIT_SHA)

BINDIR := $(CURDIR)/bin
TMPDIR := $(CURDIR)/.tmp
VENVDIR := $(CURDIR)/.venv
ANSIBLEDIR := $(CURDIR)/var/ansible
HELMDIR := $(CURDIR)/var/helm
DISTDIR := $(CURDIR)/.dist

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

CHARTS := $(PROMETHEUS_CHART) $(POSTGRES_CHART )$(KEYCLOAK_CHART) $(GRAFANA_CHART) $(KIALI_CHART)
CLOUD_PROVIDER_KIND_URL := https://github.com/kubernetes-sigs/cloud-provider-kind/releases/download/v0.6.0/cloud-provider-kind_0.6.0_darwin_arm64.tar.gz
.PHONY: clean dist all

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
cloud-provider-kind := $(BINDIR)/cloud-provider-kind
cloud-provider-mdns := $(VENVDIR)/bin/cloud-provider-mdns
ansible-playbook := $(VENVDIR)/bin/ansible-playbook
docker := /usr/local/bin/docker

deps: $(admin-password-file) $(docker) $(istioctl) $(kind) $(cloud-provider-kind) $(cloud-provider-mdns) $(ansible)
	@echo "All deps installed"

$(admin-password-file):
	@echo "$(shell openssl rand -base64 12)" > $@

$(BINDIR) $(TMPDIR) $(VENVDIR) $(DISTDIR):
	mkdir -p $@

$(docker):
	@echo "You must install a container runtime. If it is not docker then adjust its path in the 'docker' variable of the Makefile"
	@exit 1

$(kind):
	brew install kind

$(istioctl):
	brew install istioctl

$(cloud-provider-kind): | $(TMPDIR) $(BINDIR)
	curl -Lo $(TMPDIR)/cloud-provider-kind.tar.gz $(CLOUD_PROVIDER_KIND_URL)
	tar xfv $(TMPDIR)/cloud-provider-kind.tar.gz -C $(TMPDIR) cloud-provider-kind
	mv $(TMPDIR)/cloud-provider-kind $@

$(cloud-provider-mdns): | $(VENVDIR)
	$(VENVDIR)/bin/pip3 install -U git+https://github.com/MrMatAP/cloud-provider-mdns.git

$(ansible-playbook): | $(VENVDIR)
	python -mvenv $(VENVDIR)
	$(VENVDIR)/bin/pip3 install -U pip
	$(VENVDIR)/bin/pip3 install -r $(CURDIR)/requirements.txt

#
# Airgap Registry

registry: deps
	$(ansible-playbook) $(ANSIBLEDIR)/kube-eng-registry.yml

#
# Cluster installation

cluster: $(kind) $(registry)
	$(kind) create cluster --name $(CLUSTER_NAME) --config $(CLUSTER_CONFIG)

cluster-uninstall:
	kind delete cluster --name $(CLUSTER_NAME)

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

$(PROMETHEUS_CHART): $(PROMETHEUS_SOURCES) dist
	helm dep update helm/kube-eng-prometheus --skip-refresh
	helm package --version $(VERSION) --destination dist/ helm/kube-eng-prometheus

$(POSTGRES_CHART): $(POSTGRES_SOURCES) dist
	helm package --version $(VERSION) --destination dist/ helm/kube-eng-postgres

$(KEYCLOAK_CHART): $(KEYCLOAK_SOURCES) dist
	helm package --version $(VERSION) --destination dist/ helm/kube-eng-keycloak

$(GRAFANA_CHART): $(GRAFANA_SOURCES) dist
	helm dep update helm/kube-eng-grafana --skip-refresh
	helm package --version $(VERSION) --destination dist/ helm/kube-eng-grafana

$(KIALI_CHART): $(KIALI_SOURCES) dist
	helm dep update helm/kube-eng-kiali --skip-refresh
	helm package --version $(VERSION) --destination dist/ helm/kube-eng-kiali

#
# Utilities

clean:
	rm -rf $(DISTDIR) $(TMPDIR) $(BINDIR) $(VENVDIR) $(DISTDIR)
