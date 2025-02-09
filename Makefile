#
# Convenience Makefile
# Useful reference: https://makefiletutorial.com

GIT_SHA := $(shell git rev-parse --short HEAD)
VERSION ?= 0.0.0-dev0.$(GIT_SHA)

ADMIN_PASSWORD := .admin-password

PROMETHEUS_SOURCES := $(shell find helm/mrmat-prometheus)
PROMETHEUS_CHART := dist/mrmat-prometheus-$(VERSION).tgz
POSTGRES_SOURCES := $(shell find helm/kube-eng-pg)
POSTGRES_CHART := dist/kube-eng-pg-$(VERSION).tgz
KEYCLOAK_SOURCES := $(shell find helm/mrmat-keycloak)
KEYCLOAK_CHART := dist/mrmat-keycloak-$(VERSION).tgz
GRAFANA_SOURCES := $(shell find helm/mrmat-grafana)
GRAFANA_CHART := dist/mrmat-grafana-$(VERSION).tgz
KIALI_SOURCES := $(shell find helm/mrmat-kiali)
KIALI_CHART := dist/mrmat-kiali-$(VERSION).tgz

CHARTS := $(PROMETHEUS_CHART) $(POSTGRES_CHART )$(KEYCLOAK_CHART) $(GRAFANA_CHART) $(KIALI_CHART)


all: helm
password: $(ADMIN_PASSWORD)
prometheus: $(PROMETHEUS_CHART)
postgres: $(POSTGRES_CHART)
keycloak: $(KEYCLOAK_CHART)
grafana: $(GRAFANA_TARGET)
kiali: $(KIALI_TARGET)

$(ADMIN_PASSWORD):
	@echo "$(shell openssl rand -base64 12)" > $@

prometheus-install: $(PROMETHEUS_CHART)
	helm upgrade \
		mrmat-prometheus \
		$(PROMETHEUS_CHART) \
		--install \
		--wait \
		--create-namespace \
		--namespace prometheus
	helm test mrmat-prometheus --namespace prometheus
	kubectl delete po -n prometheus mrmat-prometheus-test-connection

prometheus-uninstall:
	helm uninstall mrmat-prometheus --namespace prometheus

postgres-install: $(POSTGRES_CHART)
	helm upgrade \
		kube-eng-pg \
		$(POSTGRES_CHART) \
		--install \
		--wait \
		--create-namespace \
		--namespace ke-pg

postgres-uninstall:
	helm uninstall kube-eng-pg --namespace ke-pg

keycloak-install: $(KEYCLOAK_CHART) $(ADMIN_PASSWORD)
	helm upgrade \
		mrmat-keycloak \
		$(KEYCLOAK_CHART) \
		--install \
		--wait \
		--create-namespace \
		--namespace keycloak \
		--set kc_admin_password="$(shell cat $(ADMIN_PASSWORD))"
	helm test mrmat-keycloak --namespace keycloak
	kubectl delete po -n keycloak mrmat-keycloak-test-connection
	ansible-playbook -e admin_password="$(shell cat $(ADMIN_PASSWORD))" ansible/keycloak_postinstall.yml

keycloak-uninstall:
	helm uninstall mrmat-keycloak --namespace keycloak

grafana-install: $(GRAFANA_CHART)
	helm upgrade \
		mrmat-grafana \
		$(GRAFANA_CHART) \
		--install \
		--wait \
		--create-namespace \
		--namespace grafana \
		--set grafana.envRenderSecret.GF_AUTH_GENERIC_OAUTH_CLIENT_ID=mrmat_grafana \
		--set grafana.envRenderSecret.GF_AUTH_GENERIC_OAUTH_CLIENT_SECRET="$(shell cat $(ADMIN_PASSWORD))"
	helm test mrmat-grafana --namespace grafana
	kubectl delete po -n grafana mrmat-grafana-test-connection

grafana-configure:
	ansible-playbook -e admin_password="$(shell cat $(ADMIN_PASSWORD))" ansible/grafana_postinstall.yml

grafana-uninstall:
	helm uninstall mrmat-grafana --namespace grafana



kiali-install: $(KIALI_CHART)
	kubectl create secret generic -n kiali kiali --from-literal="oidc-secret=$(shell cat $(ADMIN_PASSWORD))"
	helm upgrade \
		mrmat-kiali \
		$(KIALI_CHART) \
		--install \
		--wait \
		--create-namespace \
		--namespace kiali
	helm test mrmat-kiali --namespace kiali
	kubectl delete po -n kiali mrmat-kiali-test-connection

kiali-uninstall:
	helm uninstall mrmat-kiali --namespace kiali

#
# Charts

charts: $(CHARTS)

$(PROMETHEUS_CHART): $(PROMETHEUS_SOURCES) dist
	helm dep update helm/mrmat-prometheus --skip-refresh
	helm package --version $(VERSION) --destination dist/ helm/mrmat-prometheus

$(POSTGRES_CHART): $(POSTGRES_SOURCES) dist
	helm package --version $(VERSION) --destination dist/ helm/kube-eng-pg

$(KEYCLOAK_CHART): $(KEYCLOAK_SOURCES) dist
	helm package --version $(VERSION) --destination dist/ helm/mrmat-keycloak

$(KIALI_CHART): $(KIALI_SOURCES) dist
	helm dep update helm/mrmat-kiali --skip-refresh
	helm package --version $(VERSION) --destination dist/ helm/mrmat-kiali

$(GRAFANA_CHART): $(GRAFANA_SOURCES) dist
	helm dep update helm/mrmat-grafana --skip-refresh
	helm package --version $(VERSION) --destination dist/ helm/mrmat-grafana

#
# Utilities

dist:
	mkdir -p dist

clean:
	rm -rf dist
