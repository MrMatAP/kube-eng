# kube-eng

A local Kubernetes cluster suitable for local engineering.

> **Note:** This project is perpetually under construction, but you can expect that the sources in the main branch more or less work.

## Usage

kube-eng provides both a command-line interface (CLI) and a text-based user interface (TUI) for managing your local Kubernetes cluster. There are three major stages involved:

* `host-apply` - will configure the host infrastructure, such as DNS and a local PKI
* `cluster-apply` - will configure the cluster itself
* `stack-apply` - will deploy the remaining stack

Since `host-apply` creates a local PKI, you will have to tell your OS to trust it the first time it was created. After `cluster-apply`, you must start `cloud-provider-kind` in a separate terminal window and keep it running.

### How to install this

At this stage of development, you are bound to operate within the sources, clone the repository, then

```shell
$ uv sync
$ . .venv/bin/activate
```

### Command-Line Interface (CLI)

The CLI provides direct access to all kube-eng commands.

```shell
(kube-eng) $ uv run kube-eng --help
usage: Kube-Eng 0.0.0.dev0 [-h] [--config CONFIG_PATH] [--verbose]
                           {config,host-apply,cluster-apply,cluster-destroy,stack-apply,helm-repackage,dns-update} ...

positional arguments:
  {config,host-apply,cluster-apply,cluster-destroy,stack-apply,helm-repackage,dns-update}
                        Sub-commands
    config              Configuration commands
    host-apply          Apply the host configuration
    cluster-apply       Apply the cluster configuration
    cluster-destroy     Destroy the cluster
    stack-apply         Apply the stack configuration
    helm-repackage      Repackage Helm charts
    dns-update          Update DNS records

options:
  -h, --help            show this help message and exit
  --config CONFIG_PATH  Path to the config file, defaults to /Users/imfeldma/.kube-eng
  --verbose, -v         Enable verbose output
```

### Text-Based User Interface (TUI)

The TUI provides an interactive, visual interface for managing your cluster configuration and deploy it. Use tab to move between fields, use 'Enter' to toggle checkboxes and activate buttons, use 'q' to quit.

```shell
(kube-eng) $ uv run kube-eng-tui
```

## Kubernetes Auth/z/n

kube-eng will integrate the Kubernetes API server with the local IdP and create three roles:

* kube-eng-admin - has the `cluster-admin` cluster-role
* kube-eng-viewer - has the `view` cluster-role
* kube-eng-user - has the `edit` cluster-role

These roles are assigned to users within the IdP and prefixed with `oidc:` for the Kubernetes API server (see `src/kube_eng/ansible/project/roles/kind_configuration/templates/kube-eng-auth.yaml.j2`). The cluster-role-bindings are deployed as part of cluster-apply.

kind switches the kubectl context to its admin context by default. `cluster-apply` will create two new 'users' and contexts in your kubeconfig, one called `kube-eng-CLUSTERNAME-console` and another `kube-eng-CLUSTERNAME-idp`. The console variant is for when no local browser is available. Switch to these to perform IdP authenticated logins. It is a prerequisite to have krew and oidc-login installed for these.

```shell
$ brew install krew
$ kubectl krew install oidc-login
$ kubectl oidc-login setup 
```

## Debugging

### Debugging OIDC

You can use the `oidc-login` CLI to debug OIDC issues:

```shell
k oidc-login setup --oidc-issuer-url=https://idp.nostromo.k8s:8443/realms/master --oidc-client-id=kube-eng-nostromo --grant-type=authcode --oidc-redirect-url=http://localhost:8000 --grant-type=authcode
```

### Debug pod

`var/debug/debug-pod.yaml` provides a minimal pod with `curl` available, useful for testing connectivity and HTTP endpoints from within the cluster.

```shell
# Deploy
$ kubectl apply -f var/debug/debug-pod.yaml

# Wait for it to be running
$ kubectl wait --for=condition=Ready pod/debug

# Exec into it
$ kubectl exec -it debug -- sh

# Clean up when done
$ kubectl delete -f var/debug/debug-pod.yaml
```

To target a specific namespace, pass `-n <namespace>` to each command. For example, to test a service from within the `prometheus` namespace:

```shell
$ kubectl apply -n prometheus -f var/debug/debug-pod.yaml
$ kubectl exec -n prometheus -it debug -- sh
```
