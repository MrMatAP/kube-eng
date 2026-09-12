"""
Stack configuration tests covering cluster-scoped client Ids and topics.

Client Ids registered against infra.idp, and topics on infra.kafka, must
include cluster.name -- both may be central infrastructure shared across
clusters (provider == 'remote'), so the <resource>-<cluster.name> pattern
keeps each cluster's registration/topic distinct there.
"""

import pathlib

from kube_eng.config import RootConfig
from kube_eng.config.cluster_config import ClusterConfig


def make_config(tmp_path: pathlib.Path, **stack) -> RootConfig:
    """Build a RootConfig with deterministic identity and the given stack overrides."""
    return RootConfig(
        config_path=tmp_path,
        cluster=ClusterConfig(name='testcluster'),
        stack=stack,
    )


class TestGrafana:
    def test_client_id_includes_cluster_name(self, tmp_path: pathlib.Path):
        assert make_config(tmp_path).stack.grafana.client_id == 'grafana-testcluster'


class TestKiali:
    def test_client_id_includes_cluster_name(self, tmp_path: pathlib.Path):
        assert make_config(tmp_path).stack.kiali.client_id == 'kiali-testcluster'


class TestMimir:
    def test_kafka_topic_includes_cluster_name(self, tmp_path: pathlib.Path):
        assert (
            make_config(tmp_path).stack.mimir.kafka_topic == 'mimir-ingest-testcluster'
        )
