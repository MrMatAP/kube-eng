from kube_eng.ansible.project.library.idp_client import (
    IdP,
    IdPClient,
    IdPClientScope,
    IdPException,
    IdPProtocolMapper,
)


def test_idp_create_client(config):
    idp = IdP(idp_url=str(config.infra.idp.client_base_url),
                          idp_admin_user=config.infra.idp.admin_user,
                          idp_admin_password=config.infra.idp.admin_password,
                          idp_realm=config.infra.idp.realm,
                          idp_ca_path=config.infra.pki.ca_truststore_path)
    test_client = idp.get_client('test')
    client = IdPClient(client_id='test2',
                       name='test2',
                       description='Test Client 2',
                       standard_flow_enabled=True,
                       service_accounts_enabled=True,
                       public_client=False,
                       protocol_mappers=[IdPProtocolMapper(name='client roles')],
                       config=dict())
    idp.create_client(client)
    pass
