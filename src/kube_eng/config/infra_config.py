from pydantic import Field

from .base import RootConfigAware
from .infra_dns_config import InfraDNSConfig, LocalDNSConfig
from .infra_idp_config import InfraIdPConfig, LocalIdPConfig
from .infra_kafka_config import InfraKafkaConfig, LocalKafkaConfig
from .infra_net_config import InfraNetConfig
from .infra_pg_config import InfraPGConfig, LocalPGConfig
from .infra_pki_config import InfraPKIConfig
from .infra_registry_config import InfraRegistryConfig, LocalRegistryConfig
from .infra_s3_config import InfraS3Config, LocalS3Config


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
