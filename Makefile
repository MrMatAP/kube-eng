#
# Convenience Makefile
# Useful reference: https://makefiletutorial.com

GIT_SHA := $(shell git rev-parse --short HEAD)
VERSION ?= 0.0.0-dev0.$(GIT_SHA)

KEYCLOAK_SOURCES := $(shell find infrastructure/mrmat-keycloak)
KEYCLOAK_TARGET := dist/mrmat-keycloak-$(VERSION).tgz

all: infrastructure
infrastructure: keycloak
keycloak: $(KEYCLOAK_TARGET)

keycloak-install: $(KEYCLOAK_TARGET)
	helm upgrade \
		mrmat-keycloak \
		$(KEYCLOAK_TARGET) \
		--install \
		--create-namespace \
		--namespace keycloak

$(KEYCLOAK_TARGET): $(KEYCLOAK_SOURCES) dist
	helm package \
		--version $(VERSION) \
		--destination dist/ \
		infrastructure/mrmat-keycloak

dist:
	mkdir -p dist

clean:
	rm -rf dist
