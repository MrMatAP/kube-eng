import typing

import pytest
from kube_eng import __default_config_path__
from kube_eng.ansible.project.module_utils.idp_utils import IdPAdmin, IdPClient
from kube_eng.ansible.project.module_utils.s3_utils import S3Admin
from kube_eng.config import RootConfig


@pytest.fixture(scope="session")
def config() -> RootConfig:
    return RootConfig.load(config_path=__default_config_path__)

@pytest.fixture(scope='session')
def idp_admin(config: RootConfig) -> typing.Generator[IdPAdmin]:
    idp = IdPAdmin(
        idp_url=str(config.infra.idp.client_base_url),
        idp_admin_user=config.infra.idp.admin_user,
        idp_admin_password=config.infra.idp.admin_password,
        idp_realm=config.infra.idp.realm,
        idp_ca_path=str(config.infra.pki.ca_truststore_path),
    )
    yield idp

@pytest.fixture(scope='session')
def s3_admin(config: RootConfig) -> typing.Generator[S3Admin]:
    s3 = S3Admin(
        s3_endpoint=str(config.infra.s3.endpoint),
        s3_access_key=config.infra.s3.access_key,
        s3_secret_key=config.infra.s3.secret_key,
        s3_region=config.infra.s3.region,
        s3_ca_path=str(config.infra.pki.ca_truststore_path),
    )
    yield s3

@pytest.fixture
def idp_client(idp_admin: IdPAdmin) -> typing.Generator[IdPClient]:
    client = IdPAdmin.client_template(client_id='kube-eng-it',
                                      name='kube-eng-it',
                                      description='Client for kube-eng integration testing',
                                      root_url='https://kube-eng-it')
    created_client = idp_admin.client_create(client)
    yield client
    idp_admin.client_remove(created_client.client_id)
