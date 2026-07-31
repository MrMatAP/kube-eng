import pathlib

from pydantic import Field, computed_field

from .base import RootConfigAware


class InfraPKIConfig(RootConfigAware):
    key_type: str = Field(default='ECC')
    key_curve: str = Field(default='secp384r1')
    key_size: int = Field(default=4096)
    crt_validity: str = Field(default='+825d')
    extra_ca_path: list[pathlib.Path] = Field(
        default_factory=list,
        description='Path to any extra certificates to add to the trust store',
    )

    @computed_field
    @property
    def config_path(self) -> pathlib.Path:
        """
        Directory to store PKI files in.
        Returns:
            Path to the PKI directory.
        """
        return self._root_config.config_path / 'pki'

    @computed_field
    @property
    def ca_key_path(self) -> pathlib.Path:
        """
        Constructed path to the CA key file on the host
        Returns:
            Path to the CA key file on the host
        """
        return self.config_path / 'ca.key'

    @computed_field
    @property
    def ca_path(self) -> pathlib.Path:
        """
        Constructed path to the CA certificate file on the host
        Returns:
            Path the CA certificate file on the host
        """
        return self.config_path / 'ca.pem'

    @computed_field
    @property
    def ca_truststore_path(self) -> pathlib.Path:
        """
        Computed path to the CA truststore file on the host
        Returns:
            Path to the CA truststore file on the host
        """
        return self.config_path / 'truststore.pem'
