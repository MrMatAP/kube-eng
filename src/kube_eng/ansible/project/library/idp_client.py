from typing import Annotated, Any

import keycloak.exceptions
import pydantic
from ansible.module_utils.basic import AnsibleModule
from keycloak import KeycloakAdmin


class IdPProtocolMapper(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(extra='ignore',
                                       serialize_by_alias=True,
                                       validate_by_name=True)

    id: str | None = None
    name: str = 'client-roles'
    protocol: str = 'openid-connect'
    protocol_mapper: Annotated[str, pydantic.Field(alias='protocolMapper')] = (
        'oidc-usernodel-client-role-mapper'
    )
    consent_required: Annotated[
        bool | None, pydantic.Field(alias='consentRequired')
    ] = None
    consent_text: Annotated[str | None, pydantic.Field(alias='consentText')] = None
    config: dict[str, Any] | None = None

    def model_dump(self, **kwargs):
        kwargs.setdefault('exclude_none', True)
        return super().model_dump(**kwargs)

    def model_dump_json(self, **kwargs):
        kwargs.setdefault('exclude_none', True)
        return super().model_dump_json(**kwargs)



class IdPClientScope(pydantic.BaseModel):
    id: str | None = None
    name: str
    description: str | None = None
    protocol: str = 'openid-connect'
    attributes: dict[str, Any] | None = None
    protocol_mappers: Annotated[
        list[IdPProtocolMapper] | None,
        pydantic.Field(
            serialization_alias='protocolMappers', validation_alias='protocolMappers'
        ),
    ] = None


class IdPClient(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(extra='ignore',
                                       serialize_by_alias=True,
                                       validate_by_name=True)

    id: str | None = None
    client_id: Annotated[str, pydantic.Field(alias='clientId')]
    name: str
    description: str | None = None
    root_url: Annotated[pydantic.AnyHttpUrl | None, pydantic.Field(alias='rootUrl')] = None
    admin_url: Annotated[pydantic.AnyHttpUrl | None, pydantic.Field(alias='adminUrl')] = None
    base_url: Annotated[pydantic.AnyHttpUrl | None, pydantic.Field(alias='baseUrl')] = None
    redirect_uris: Annotated[
        list[pydantic.AnyHttpUrl] | None, pydantic.Field(alias='redirectUris')
    ] = None
    web_origins: Annotated[
        list[pydantic.AnyHttpUrl] | None, pydantic.Field(alias='webOrigins')
    ] = None
    enabled: bool = True
    always_display_in_console: Annotated[
        bool, pydantic.Field(alias='alwaysDisplayInConsole')
    ] = True
    secret: pydantic.SecretStr | None = None
    standard_flow_enabled: Annotated[
        bool, pydantic.Field(alias='standardFlowEnabled')
    ] = True
    implicit_flow_enabled: Annotated[
        bool, pydantic.Field(alias='implicitFlowEnabled')
    ] = False
    direct_access_grants_enabled: Annotated[
        bool, pydantic.Field(alias='directAccessGrantsEnabled')
    ] = False
    service_accounts_enabled: Annotated[
        bool, pydantic.Field(alias='serviceAccountsEnabled')
    ] = True
    public_client: Annotated[bool, pydantic.Field(alias='publicClient')] = False
    front_channel_logout: Annotated[
        bool, pydantic.Field(alias='frontchannelLogout')
    ] = True
    protocol: str = 'openid-connect'
    attributes: dict[str, Any] | None = None
    protocol_mappers: Annotated[
        list[IdPProtocolMapper], pydantic.Field(alias='protocolMappers')
    ]

    def model_dump(self, **kwargs):
        kwargs.setdefault('exclude_none', True)
        return super().model_dump(**kwargs)

    def model_dump_json(self, **kwargs):
        kwargs.setdefault('exclude_none', True)
        return super().model_dump_json(**kwargs)



class IdPException(Exception):

    def __init__(self, code: int = 500, msg: str = 'Unknown'):
        self._code = code
        self._msg = msg

    @property
    def code(self) -> int:
        return self._code

    @property
    def msg(self) -> str:
        return self._msg

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}(code={self.code}, msg={self.msg})'

    def __str__(self) -> str:
        return f'[{self.code}] {self.msg}'

class IdP:
    
    def __init__(self,
                 idp_url: str,
                 idp_admin_user: str,
                 idp_admin_password: str,
                 idp_realm: str,
                 idp_ca_path: str):
        self._idp_admin = KeycloakAdmin(server_url=idp_url,
                                        username=idp_admin_user,
                                        password=idp_admin_password,
                                        realm_name=idp_realm,
                                        verify=idp_ca_path)

    def get_client(self, name: str) -> IdPClient:
        try:
            raw_client_id = self._idp_admin.get_client_id(name)
            if raw_client_id is None:
                raise IdPException(code=400, msg=f'{name} is not a known client_id')
            raw_client = self._idp_admin.get_client(raw_client_id)
            client = IdPClient.model_validate(raw_client)
            return client
        except pydantic.ValidationError as ve:
            raise IdPException from ve

    def create_client(self, client: IdPClient):
        try:
            raw_client = client.model_dump(mode='python')
            self._idp_admin.create_client(raw_client)
        except keycloak.exceptions.KeycloakError as ke:
            raise IdPException from ke


def run_module():
    result = dict(changed=False, msg='')
    module_args = dict(
        idp_url=dict(type='str', required=True),
        idp_admin_user=dict(type='str', required=True),
        idp_admin_password=dict(type='str', required=True, no_log=True),
        idp_realm=dict(type='str', required=True),
        idp_ca_path=dict(type='str', required=True),
        name=dict(type='str', required=True),
        description=dict(type='str', required=True),
        client_id=dict(type='str', required=True)
    )
    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)

    if module.check_mode:
        module.exit_json(**result)
    try:
        idp_clientscope = IdP(idp_url=module.params['idp_url'],
                              idp_admin_user=module.params['idp_admin_uer'],
                              idp_admin_password=module.params['idp_admin_password'],
                              idp_realm=module.params['idp_realm'],
                              idp_ca_path=module.params['idp_ca_path'])
        idp_clientscope.create(name=module.params['name'], description=module.params['description'])
        module.exit_json(**result)
    except Exception as e:
        module.fail_json(msg='An exception occurred', exception=e)


def main():
    run_module()


if __name__ == '__main__':
    main()
