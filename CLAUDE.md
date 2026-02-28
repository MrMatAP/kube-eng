# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

`kube-eng` is a Python tool for managing a local Kubernetes cluster suitable for local engineering. It provides:
- A **CLI** (`kube-eng`) for scripted/Makefile-driven operations
- A **TUI** (`kube-eng-tui`) built with [Textual](https://textual.textualize.io/) for interactive configuration and cluster management

The Python layer wraps Ansible playbooks that do the actual provisioning work. Ansible runs against `localhost` and drives Docker containers (DNS/registry/postgres/minio/kafka) and a [kind](https://kind.sigs.k8s.io/) Kubernetes cluster.

## Development Commands

```bash
# Install in editable mode (sets up kube-eng and kube-eng-tui entry points)
uv pip install -e .

# Run tests
uv run pytest

# Run a single test
uv run pytest tests/test_config.py::test_root_config_propagates_when_loaded

# Lint
uv run ruff check src/

# Format
uv run ruff format src/

# Type check
uv run pyrefly check
```

## Makefile Targets (cluster lifecycle)

These require Homebrew tools (`kind`, `helm`, `kubectl`, `istioctl`) and Docker:

```bash
make deps          # Verify/install all host dependencies
make host-infra    # Create host-side infra (DNS, registry, postgres, etc.)
make host-infra-start  # Start host services (requires sudo via --ask-become-pass)
make host-infra-stop   # Stop host services
make cluster       # Create the kind Kubernetes cluster
make cluster-destroy   # Destroy the cluster
make stack         # Deploy observability/auth stack (Prometheus, Grafana, Keycloak, etc.)
make charts        # Build all Helm charts into .dist/charts/
```

## Architecture

### Configuration Model (`src/kube_eng/config/`)

The configuration hierarchy is built on Pydantic models:

- `RootConfig` — top-level model, loaded from/saved to `~/.kube-eng/kube-eng.yaml` by default
  - `host: HostConfig` — Docker containers and host tools (DNS, registry, postgres, minio, kafka, kind, kubectl, helm)
  - `cluster: ClusterConfig` — kind cluster settings (CNI, mesh/Istio, PKI/cert-manager, edge/ingress)
  - `stack: StackConfig` — observability/auth components (Prometheus, Grafana, Loki, Alloy, Keycloak, Jaeger, Kiali)

All config classes except `RootConfig` extend `RootConfigAware` (from `config/base.py`), which holds a `_root_config` back-reference. This allows leaf configs to access sibling config values (e.g., `self._root_config.config_path`). The reference is propagated in `RootConfig.model_post_init()` after full initialisation.

Config is serialized as YAML (`~/.kube-eng/kube-eng.yaml`). Many fields use `computed_field` properties to derive paths from `_root_config.config_path`.

### Ansible Execution (`src/kube_eng/common/ansible_execution.py`)

`AnsibleExecution` wraps `ansible_runner.run_async()`. It:
1. Receives a `RootConfig` instance and serializes it as `extravars` to the playbook
2. Calls a `ui_event_callback` with `AnsibleEvent` dataclass instances for each Ansible event
3. Runs playbooks from `src/kube_eng/ansible/project/` (embedded in the package)

The `cmd_to_playbook` dict maps CLI subcommand names to playbook filenames.

### CLI (`src/kube_eng/cli/main.py`)

Subcommands:
- `config list / get / set` — inspect and modify config values by dot-path (e.g., `host.registry.port`)
- `host-apply`, `cluster-apply`, `cluster-destroy`, `stack-apply` — trigger Ansible playbooks
- `helm-repackage`, `dns-update` — additional playbook shortcuts

### TUI (`src/kube_eng/tui/`)

Built with Textual. Entry point: `tui/main.py` → `KubeEngApp`.

- `config_tab.py` — editable forms for the full config hierarchy
- `status_tab.py` — cluster status display
- `widgets/` — shared widgets: `AppHeader`, `AppBody`, `AnsibleExecutionModal`, `ActionsModal`, form components
- `tui.tcss` — Textual CSS stylesheet
- `validators.py` — Textual input validators (path, port)

Playbooks are triggered from the TUI via keyboard bindings (`a` = Actions modal, `r` = helm-repackage, `d` = dns-update) which call `execute_playbook()` → `AnsibleExecution`.

### Ansible Playbooks (`src/kube_eng/ansible/project/`)

Playbooks: `host_apply.yml`, `cluster_apply.yml`, `cluster_destroy.yml`, `stack_apply.yml`, `helm_repackage.yml`, `dns_update.yml`.

The `RootConfig` model is dumped as JSON and passed as `extravars`, so Ansible variables mirror the Python config hierarchy (e.g., `host.registry.port`).

### Helm Charts (`src/kube_eng/helm/`)

Wrapper charts for: cert-manager, edge (Traefik/Istio gateway), Prometheus, Alloy, Loki, Keycloak operator + Keycloak, Grafana, Jaeger (v1 + v2), Kiali. Charts are packaged by `make charts` into `.dist/charts/`.

## Key File Locations

| What | Where |
|---|---|
| Default config dir | `~/.kube-eng/` |
| Config file | `~/.kube-eng/kube-eng.yaml` |
| Ansible playbooks | `src/kube_eng/ansible/project/` |
| Helm chart sources | `src/kube_eng/helm/` |
| Packaged charts | `.dist/charts/` |
| PKI files | `var/pki/` (not `.dist/`, to avoid accidental deletion) |
| Ansible artifacts | `~/.kube-eng/ansible/` |

## Code Style

- Python 3.14, formatted with `ruff` (single quotes, 88-char line length)
- Pydantic v2 models for all configuration
- All config sub-models must extend `RootConfigAware` so the root back-reference propagates
- Prefer `import x.y` over `from x import y` unless the module to be imported is in this python package
- Imports from the standard Python library must come before imports from dependency packages. Imports from this python package must come last.
