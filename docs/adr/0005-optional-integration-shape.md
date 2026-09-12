# Optional cross-component integrations are `{enabled, uri}` plus one resolved computed field

The stack has several optional edges where one component sends data to another: Prometheus can remote_write into Mimir, Alloy can scrape metrics into Mimir, Alloy can tail logs into Loki. Each edge needs the same three things: a way to turn it on independent of whether the target is locally installed, a way to point it at a target that isn't the local install, and a way to fail loudly instead of silently when neither is available.

## Decision

Every such edge is a nested config model with exactly this shape:

- `enabled: bool` — off by default *unless* the edge already existed unconditionally before this convention did, in which case it must default on to preserve upgrade behaviour (see below).
- `uri: str` — a stored, user-settable override. Empty means "no override, resolve from the local install."
- `push_url` — a `computed_field` `@property` that resolves the above: return `''` if `enabled` is `False`; return `uri` if it's set; otherwise return the target component's own `push_url` if that component is locally `enabled`; otherwise `raise ValueError` naming exactly which two things are missing (`stack.mimir` disabled and `stack.<x>.uri` empty).

This mirrors the existing `RemoteKafkaConfig.client_fqdn` / `RegistryConfig.client_fqdn` pattern of raising from a `computed_field` rather than a `model_validator` — Pydantic only evaluates it once the full hierarchy (and `_root_config`) is available, and it's what every other cross-field validation in this config tree already does.

Each locally-installable target (`StackMimirConfig`, `StackLokiConfig`) exposes its own canonical `push_url`/`query_url` computed fields, so the URL is constructed in exactly one place and every consumer — the integration's resolver, `stack_apply.yml`, Grafana's datasource wiring — reads it rather than re-deriving `http://<svc>.<ns>.svc.cluster.local:<port>/...` from `ns` themselves.

Errors raised this way surface whenever the full config is dumped with computed fields included (`config list`, `config get`, Ansible extravars serialization in `AnsibleExecution`) but never during `config set` or `RootConfig.save()`, both of which only touch stored fields (`save()` explicitly passes `exclude_computed_fields=True`). A broken combination is always recoverable with a follow-up `config set stack.<x>.enabled false` — it can't lock you out of your own config file.

**Upgrade-safety consequences**: two of these three edges replaced behaviour that was previously unconditional, so both had to default `enabled: True` to avoid silently changing what an existing `~/.kube-eng/kube-eng.yaml` does on upgrade:

- `stack.alloy.logs.enabled` — `stack.alloy`'s log shipping used to run whenever `stack.loki.enabled` was true, with no separate switch.
- `stack.prometheus.mimir.enabled` — the old `remoteWrite` line wrote into Mimir whenever `stack.mimir.enabled` was true (the default), again with no separate switch.

`stack.alloy.metrics.enabled` also now defaults `True`, on request, once `stack.alloy` was in general use: with `stack.alloy.enabled` itself defaulting `True`, both signals should collect out of the box, matching `logs`. Because `StackPrometheusConfig.chart_enabled` depends on `alloy.metrics.enabled`, it must also check `alloy.enabled` itself — otherwise disabling Alloy entirely (while its `metrics.enabled` default is left untouched) still installs the whole `kube-eng-prometheus` chart for CRDs nothing would consume. `chart_enabled` is therefore `self.enabled or (alloy.enabled and alloy.metrics.enabled)`, not just the second term.

At the time this default changed, `stack.alloy.metrics` still worked by selecting `ServiceMonitor`/`PodMonitor` CRs, and defaulting `enabled: True` with an inert selector was a real gap: Alloy would run, have RBAC, and remote_write zero series by default. That whole selector-based mechanism was replaced shortly after by native `discovery.kubernetes` scraping (see "Alloy and Prometheus each deploy their own scraping configuration" below), which has real, non-inert default coverage — the gap this paragraph originally described no longer exists.

## Grafana only declares a datasource for what's actually installed and populated

`kube-eng-grafana`'s `templates/datasource-*.yaml` each gate on `.Values.integration.<x>.enabled`, which `stack_apply.yml` sets from the matching `stack.<x>.enabled` — except Mimir, which additionally requires something to actually write into it (`stack.prometheus.mimir.enabled or stack.alloy.metrics.enabled`); otherwise it's a query datasource pointed at a permanently empty store, which is worse than not declaring one. Exactly one of the metrics-capable datasources (`prometheus`, `mimir`) is `isDefault`, preferring Prometheus when both are present.

## Alloy and Prometheus each deploy their own scraping configuration

Two earlier designs for `stack.alloy.metrics` were tried and abandoned in favour of a third:

1. **Same selector as Prometheus** (`stack.alloy.metrics.selector = "prometheus"`) — byte-identical coverage since it's literally the same `ServiceMonitor`/`PodMonitor` objects, but running both Prometheus and Alloy together double-scrapes every target into Mimir with no way to decouple them.
2. **A second, Alloy-only selector value** (`monitored-by: alloy`, distinct from Prometheus's `monitored-by: prometheus`) on the same CRs — avoids the double-scrape, but nothing in this repo ever labelled anything for it, so it shipped briefly as a real but *inert* default: Alloy ran, had RBAC, and found zero targets.

Both were CRD-dependent: Alloy's `prometheus.operator.servicemonitors`/`podmonitors` components need the `monitoring.coreos.com` CRDs to exist, which in this stack only ever come from the `kube-eng-prometheus` chart. The decision landed on:

3. **Native discovery, no CRDs at all.** `templates/cm.yaml`'s metrics block uses `discovery.kubernetes{role="endpoints"}` and `discovery.kubernetes{role="node"}` plus `discovery.relabel`/`prometheus.scrape` pairs that replicate each Prometheus `ServiceMonitor`'s selector/port/scheme/auth directly — one pair per target, mirroring the ServiceMonitor it stands in for. Alloy never reads a `ServiceMonitor`/`PodMonitor` CR, so `templates/rbac-metrics.yaml` only needs `get/list/watch` on core `endpoints`, `nodes`, `pods`, `services` — no `monitoring.coreos.com` grant, no dependency on the CRDs or the Prometheus Operator existing at all. This is what "Alloy and Prometheus deploy scraping configurations respectively" means in this stack: two independent scrape configurations that happen to describe the same targets, not one shared selection mechanism with two labels.

Verified with the real `grafana/alloy` binary via `docker run grafana/alloy:latest validate <extracted config.alloy>` (not just `helm template` rendering) across all four `logging`/`metrics` enablement combinations — this catches component-graph errors (bad references, unknown attributes, cycles) that Helm's template engine can't see since it only produces text, and it caught nothing.

### Completeness/sanity review: what each job does and doesn't cover

| Target | Prometheus source | Alloy job | Status |
|---|---|---|---|
| kubelet `/metrics` | kube-prometheus-stack `kubelet` ServiceMonitor | `kubelet` | Verified — `role="node"` discovery, direct HTTPS to `<node-ip>:10250`, in-cluster CA + bearer token. Independent of `stack.prometheus`. |
| kubelet cAdvisor | same ServiceMonitor, `/metrics/cadvisor` | `kubelet_cadvisor` | Verified, same as above. |
| kubelet resource probes | same ServiceMonitor, `/metrics/probes` | `kubelet_probes` | Verified, same as above. |
| kube-apiserver | kube-prometheus-stack `apiserver` ServiceMonitor (built-in `kubernetes` Service, `default` ns) | `apiserver` | Verified. Independent of `stack.prometheus`. |
| CoreDNS | kube-prometheus-stack `coreDns` (built-in `kube-dns` Service, `kube-system`) | `coredns` | Verified. Independent of `stack.prometheus`. |
| kube-state-metrics | kube-prometheus-stack subchart, port `http`/8080 | `kube_state_metrics` | Verified selector/port. **Requires `stack.prometheus.chart_enabled`** — the workload only exists via that chart. |
| node-exporter | kube-prometheus-stack subchart, port `metrics`/9100 | `node_exporter` | Verified selector/port. **Requires `stack.prometheus.chart_enabled`.** |
| kube-etcd | kube-prometheus-stack `kubeEtcd` (Service wrapping the kubeadm static pod, `scheme: http`, port 2381 per this chart's override) | `kube_etcd` | Selector/scheme replicated. **Requires `stack.prometheus.chart_enabled`** for the Service to exist, *and* is expected unreachable regardless: kubeadm defaults etcd's metrics listener to loopback-only, and nothing in `kind_configuration` patches that. Same limitation Prometheus's own ServiceMonitor has today. |
| kube-scheduler | kube-prometheus-stack `kubeScheduler` (Service wrapping the static pod) | `kube_scheduler` | Selector/https/bearer-token replicated for the modern secure-port default. Same chart_enabled + loopback-binding caveat as kube-etcd. |
| kube-controller-manager | kube-prometheus-stack `kubeControllerManager` | `kube_controller_manager` | Same as kube-scheduler. |
| kube-proxy | kube-prometheus-stack `kubeProxy` | `kube_proxy` | Same chart_enabled + loopback-binding caveat (kube-proxy's metrics port is plain HTTP, no TLS/token needed if ever reachable). |
| cert-manager controller | `kube-eng-prometheus/templates/sm-cert-manager.yaml` | `cert_manager` | Verified selector/port/10s interval. Independent of `stack.prometheus`. |
| cert-manager webhook | `sm-cert-manager-webhook.yaml` | `cert_manager_webhook` | Verified, same as above. |
| Edge gateway | `sm-edge-gw.yaml` | `edge_gateway` | Verified selector/port/10s interval. Only matches when `cluster.edge.kind` uses the Istio Gateway API, same condition the ServiceMonitor it replicates has. |
| Kiali | `kube-eng-kiali/templates/sm-kiali.yml` | `kiali` | Verified. Independent of `stack.prometheus`. |
| Loki | `kube-eng-loki/templates/sm-loki.yaml` | `loki` | Verified, explicitly excludes the canary the way the ServiceMonitor's selector does. |
| Loki canary | `sm-loki-canary.yaml` | `loki_canary` | Verified selector. Finds nothing unless `loki.lokiCanary.enabled` (itself default `false`), same as the ServiceMonitor it replicates. |
| Tempo (2 ports) | vendored `tempo` subchart's `templates/servicemonitor.yaml` | `tempo` | Verified both port names (`tempo-prom-metrics`, `jaeger-metrics`). |
| grafana-operator | vendored `grafana-operator` subchart's `templates/servicemonitor.yaml` | `grafana_operator` | Verified. |
| istiod | `kube-eng-istio/templates/sm-istio-istiod.yaml` | *(none)* | Deliberately omitted — gated on `monitoring.enabled`, which nothing in `cluster_apply.yml` ever sets, so it isn't part of "currently deployed" today. |

**Known approximations, not silent guesses**: the app-level jobs replicate their source ServiceMonitor's explicit `interval: 10s`. The kube-prometheus-stack-bundled jobs (kubelet, apiserver, coredns, kube-state-metrics, node-exporter, the four control-plane ones) have no per-`ServiceMonitor` interval override in `kube-eng-prometheus/values.yaml`, so they inherit whatever Prometheus Operator's effective global default is — not statically readable from the chart's defaults alone. Alloy's jobs use `30s` for these; close to, but not guaranteed identical to, Prometheus's own resolved value.

**Two dependencies this design does *not* remove**, despite CRDs no longer being one: `stack.prometheus.chart_enabled` still gates kube-state-metrics, node-exporter, and the four control-plane jobs (the workloads/Services only exist via that chart), and `ap-prometheus-allow.yaml`'s `AuthorizationPolicy` was extended to allow `sa-alloy` the same ports (9090/8080/10250) already granted to Prometheus's own service accounts, since kube-state-metrics sits behind an Istio ambient waypoint. node-exporter needs no such entry: its chart default is `hostNetwork: true`, which ambient mesh doesn't intercept.

`infra_apply.yml` separately downloads the `ServiceMonitor`/`PodMonitor` CRD YAML to `preheat_path` (`stack.prometheus.service_monitor_crd`/`pod_monitor_crd`) but never applies them anywhere — that download has no consumer, and with Alloy no longer needing those CRDs either, has even less reason to grow one. Left as-is, unrelated to this change.

## Every chart-owned `ServiceMonitor` is gated on `stack.prometheus.chart_enabled`, not just Grafana's

Making `stack.prometheus.enabled = False` a real, reachable state (rather than something nobody actually ran) surfaced that four charts render a `ServiceMonitor` unconditionally or on a default-`true` switch, with no check that the `monitoring.coreos.com` CRDs the kind even requires are installed: `kube-eng-grafana` (`operator.serviceMonitor.enabled: true`, the one that first broke), `kube-eng-tempo` (`tempo.serviceMonitor.enabled: true`), and `kube-eng-kiali`/`kube-eng-loki`'s own `templates/sm-{kiali,loki}.y*ml` (no gate at all — the CRD didn't even have to be a Prometheus/chart_enabled scenario to hit this, any bare `helm install` of either chart standalone would already fail today). All four now default `enabled: false` on a `serviceMonitor.enabled`-shaped value (matching Alloy's existing `logging`/`metrics` convention), with `stack_apply.yml` setting it from `stack.prometheus.chart_enabled` — the same field that gates whether the CRDs get installed in the first place. `kube-eng-loki`'s `sm-loki-canary.yaml` was already correctly gated (on `loki.lokiCanary.enabled`, itself default `false`) and needed no change. `kube-eng-prometheus`'s own internal `ServiceMonitor`s (`sm-cert-manager*`, `sm-edge-gw`, plus the kube-prometheus-stack-bundled ones) need no gate: they ship in the same Helm release as the CRDs, so ordering can't skew.
