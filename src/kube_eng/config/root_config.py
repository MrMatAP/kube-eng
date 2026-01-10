import base64
import pathlib
import getpass
import secrets
from typing import Any

import yaml

from pydantic import BaseModel, Field, computed_field

from kube_eng import __version__
from .base import RootConfigAware

from .cluster_config import ClusterConfig
from .host_config import HostConfig, HostDNSKindEnum
from .stack_config import StackConfig


class RootConfig(BaseModel):
    """
    Configuration of the kube-eng cluster
    """
    config_path: pathlib.Path = Field(description='Path to the configuration directory')
    admin_password: str = Field(default_factory=secrets.token_urlsafe, description="Admin password for the cluster and its services")
    user_id: str = Field(default_factory=getpass.getuser, description="Real user id of the current user")

    host: HostConfig = Field(default_factory=HostConfig, description="Host configuration")
    cluster: ClusterConfig = Field(default_factory=ClusterConfig, description="Cluster configuration")
    stack: StackConfig = Field(default_factory=StackConfig, description="Stack configuration")

    @computed_field
    @property
    def version(self) -> str:
        """
        The current version of kube-eng

        Returns:
            The current version of kube-eng
        """
        return __version__

    @computed_field
    @property
    def config_file_path(self) -> pathlib.Path:
        """
        The actual configuration file within the config directory
        Returns:
            Path to the cluster configuration file
        """
        return self.config_path / "kube-eng.yaml"

    @computed_field
    @property
    def preheat_path(self) -> pathlib.Path:
        """
        Directory to store preheat files in.
        Returns:
            Path to the preheat directory.
        """
        return self.config_path / "preheat"

    @computed_field
    @property
    def ansible_artifacts_path(self) -> pathlib.Path:
        """
        Directory to store Ansible artefacts in.
        Returns:
            Path to the Ansible artefacts directory.
        """
        return self.config_path / "ansible"

    def save(self) -> None:
        """
        Save the current in-memory configuration to disk.
        Returns:
            Nothing
        """
        self.config_path.mkdir(parents=True, exist_ok=True)
        yaml.dump(self.model_dump(mode="json"), self.config_file_path.open("w"))

    @classmethod
    def load(cls, config_path: pathlib.Path) -> "RootConfig":
        """
        Load the configuration from disk.
        Args:
            config_path (Path): Path to the configuration directory.

        Returns:
            An initialised Config object.
        """
        config_file_path = config_path / "kube-eng.yaml"
        if config_file_path.exists():
            return cls.model_validate(yaml.safe_load(config_file_path.open()))
        else:
            return cls(config_path=config_path)

    def model_post_init(self, context: Any, /) -> None:
        """
        Propagate a reference to this root configuration instance down the
        hierarchy. Pydantic invokes this method to let us know that the
        instance is fully initialised.

        Massaging of initial, unset defaults within the hierarchy must occur
        here because individual model_post_init methods within the hierarchy
        execute before this sets a reference to the root config.

        Args:
            context (): Undocumented parameter, appears to always be None
        """
        super().model_post_init(context)
        for field in dict(self).values():
            if issubclass(type(field), RootConfigAware):
                field.propagate_root_config(self)

        # If we are to use the local default DNS server and have not been
        # given a key_secret, we default to the base64-encoded admin password
        if self.host.dns.kind == HostDNSKindEnum.local and self.host.dns.key_secret == "":
            self.host.dns.key_secret = base64.b64encode(
                bytes(self.admin_password, encoding='utf-8')
            ).decode('utf-8')
