import pathlib
import getpass
import secrets
from typing import Any

import yaml

from pydantic import BaseModel, Field, computed_field

from .root_config_aware import RootConfigAware

from .cluster_config import ClusterConfig
from .host_config import HostConfig
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
    def config_file_path(self) -> pathlib.Path:
        """
        The actual configuration file within the config directory
        Returns:
            Path to the cluster configuration file
        """
        return self.config_path / "kube-eng.yaml"

    @computed_field
    @property
    def dist_path(self) -> pathlib.Path:
        """
        Directory to store downloaded artefacts in.
        Returns:
            Path to the dist directory.
        """
        return self.config_path / "dist"

    @computed_field
    @property
    def pki_path(self) -> pathlib.Path:
        """
        Directory to store PKI files in.
        Returns:
            Path to the PKI directory.
        """
        return self.config_path / "pki"

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
    def registry_path(self) -> pathlib.Path:
        """
        Directory to store registry configuration in.
        Returns:
            Path to the registry directory.
        """
        return self.config_path / "registry"

    @computed_field
    @property
    def artifacts_path(self) -> pathlib.Path:
        """
        Directory to store logs in.
        Returns:
            Path to the log directory.
        """
        return self.config_path / "artifacts"

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

        Args:
            context (): Undocumented parameter, appears to always be None
        """
        super().model_post_init(context)
        for field in dict(self).values():
            if issubclass(type(field), RootConfigAware):
                field.propagate_root_config(self)

