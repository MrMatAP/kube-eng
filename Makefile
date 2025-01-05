#
# Convenience Makefile
# Useful reference: https://makefiletutorial.com

GIT_SHA := $(shell git rev-parse --short HEAD)
VERSION ?= 0.0.0-dev0.$(GIT_SHA)

KEYCLOAK_ADMIN_PASSWORD ?= $(shell openssl rand -base64 12)

KEYCLOAK_SOURCES := $(shell find infrastructure/mrmat-keycloak)
KEYCLOAK_TARGET := dist/mrmat-keycloak-$(VERSION).tgz
PROMETHEUS_SOURCES := $(shell find infrastructure/mrmat-prometheus)
PROMETHEUS_TARGET := dist/mrmat-prometheus-$(VERSION).tgz
GRAFANA_SOURCES := $(shell find infrastructure/mrmat-grafana)
GRAFANA_TARGET := dist/mrmat-grafana-$(VERSION).tgz

all: infrastructure
infrastructure: keycloak prometheus grafana
keycloak: $(KEYCLOAK_TARGET)
prometheus: $(PROMETHEUS_TARGET)
grafana: $(GRAFANA_TARGET)

keycloak-install: $(KEYCLOAK_TARGET)
	helm upgrade \
		mrmat-keycloak \
		$(KEYCLOAK_TARGET) \
		--install \
		--wait \
		--create-namespace \
		--namespace keycloak \
		--set kc_admin_password=${KEYCLOAK_ADMIN_PASSWORD}
	helm test mrmat-keycloak --namespace keycloak
	kubectl delete po -n keycloak mrmat-keycloak-test-connection

keycloak-uninstall:
	helm uninstall \
		mrmat-keycloak \
		--namespace keycloak

$(KEYCLOAK_TARGET): $(KEYCLOAK_SOURCES) dist
	helm package \
		--version $(VERSION) \
		--destination dist/ \
		infrastructure/mrmat-keycloak

prometheus-install: $(PROMETHEUS_TARGET)
	helm upgrade \
		mrmat-prometheus \
		$(PROMETHEUS_TARGET) \
		--install \
		--wait \
		--create-namespace \
		--namespace prometheus \
		--set
	helm test mrmat-prometheus --namespace prometheus
	kubectl delete po -n prometheus mrmat-prometheus-test-connection


$(PROMETHEUS_TARGET): $(PROMETHEUS_SOURCES) dist
	helm dep update infrastructure/mrmat-prometheus --skip-refresh
	helm package \
		--version $(VERSION) \
		--destination dist/ \
		infrastructure/mrmat-prometheus

grafana-install: $(GRAFANA_TARGET)
	# TODO: Obtain the client secret from the registration in Keycloak
	helm upgrade \
		mrmat-grafana \
		$(GRAFANA_TARGET) \
		--install \
		--wait \
		--create-namespace \
		--namespace grafana \
		--set grafana.envRenderSecret.GF_AUTH_GENERIC_OAUTH_CLIENT_ID=mrmat-grafana \
		--set grafana.envRenderSecret.GF_AUTH_GENERIC_OAUTH_CLIENT_SECRET=#TODO
	helm test mrmat-grafana --namespace grafana
	kubectl delete po -n grafana mrmat-grafana-test-connection

grafana-uninstall:
	helm uninstall \
		mrmat-grafana \
		--namespace grafana

$(GRAFANA_TARGET): $(GRAFANA_SOURCES) dist
	helm dep update infrastructure/mrmat-grafana --skip-refresh
	helm package \
		--version $(VERSION) \
		--destination dist/ \
		infrastructure/mrmat-grafana

dist:
	mkdir -p dist

clean:
	rm -rf dist
