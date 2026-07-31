from pydantic import Field

from .base import RootConfigAware
from .infra_net_config import InfraNetConfig
from .infra_pki_config import InfraPKIConfig
from .infra_dns_config import LocalDNSConfig, InfraDNSConfig
from .infra_idp_config import LocalIdPConfig, InfraIdPConfig
from .infra_kafka_config import LocalKafkaConfig, InfraKafkaConfig
from .infra_pg_config import LocalPGConfig, InfraPGConfig
from .infra_registry_config import LocalRegistryConfig, InfraRegistryConfig
from .infra_s3_config import LocalS3Config, InfraS3Config


class InfraConfig(RootConfigAware):
    """Core infrastructure the cluster and stack depend on."""

    net: InfraNetConfig = Field(default_factory=InfraNetConfig)
    pki: InfraPKIConfig = Field(default_factory=InfraPKIConfig)
    dns: InfraDNSConfig = Field(default_factory=LocalDNSConfig)
    pg: InfraPGConfig = Field(default_factory=LocalPGConfig)
    idp: InfraIdPConfig = Field(default_factory=LocalIdPConfig)
    s3: InfraS3Config = Field(default_factory=LocalS3Config)
    registry: InfraRegistryConfig = Field(default_factory=LocalRegistryConfig)
    kafka: InfraKafkaConfig = Field(default_factory=LocalKafkaConfig)
