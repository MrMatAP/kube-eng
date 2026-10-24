# Recent Changes Summary

## October 2026 Updates
- Updated zot registry to version v2.1.22
- Added missing HTTP routes

## Infrastructure & Configuration
- Replaced infra_registry with configuration
- Added PostgreSQL database support (local and remote)
- Created dedicated password for Grafana admin
- Removed top-level shared admin_password
- Refactored TUI with new config structure and mrmat.css color scheme

## Networking & Services
- Added Loki and Alloy for logging
- Scoped client IDs and Mimir's Kafka topic to cluster.name
- Integrated S3 with OIDC federation and native IAM
- Added Mimir Helm chart (not yet configured)
- Version bump to Kubernetes 1.37.0

## Security & PKI
- Switched to central CA trust
- Enabled DB and fixed OAuth for Grafana
- Removed Keycloak from stack
- Rebranded cert-manager to PKI and added PKI-trust

## Development & Tooling
- Improved Ansible event handling and output formatting
- Updated cluster configurations and Helm charts
- Kubernetes OIDC authentication improvements
- Added CLAUDE.md with architecture overview and dev commands

## Bug Fixes & Improvements
- Fixed remote to local provider switch in TUI
- Fixed idempotency when checking for preheated images
- Various dependency version bumps
- Cleaned up monitoring and dashboards