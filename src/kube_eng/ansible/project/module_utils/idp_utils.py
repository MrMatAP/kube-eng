"""IdP-related tooling"""

import typing
from typing import Annotated, Any

import keycloak.exceptions
import pydantic
from keycloak import KeycloakAdmin

from .base import InfraException, InfraResult


class IdPException(InfraException):
    pass


class IdPResult(InfraResult):
    pass


class IdPValidationResult(IdPResult):
    validated: typing.Annotated[bool, pydantic.Field()]


class IdPClientCreateResult(IdPResult):
    client_id: typing.Annotated[str, pydantic.Field()]
    client_secret: typing.Annotated[str | None, pydantic.Field(default=None)]


class IdPPayload(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(
        extra='ignore',
        serialize_by_alias=True,
        validate_by_name=True,
        validate_by_alias=True,
    )

    def model_dump(self, **kwargs):
        kwargs.setdefault('exclude_none', True)
        return super().model_dump(**kwargs)

    def model_dump_json(self, **kwargs):
        kwargs.setdefault('exclude_none', True)
        return super().model_dump_json(**kwargs)


class IdPProtocolMapper(IdPPayload):
    id: str | None = None
    name: str = 'client-roles'
    protocol: str = 'openid-connect'
    protocol_mapper: Annotated[
        str,
        pydantic.Field(
            alias='protocolMapper', default='oidc-usermodel-client-role-mapper'
        ),
    ]
    config: dict[str, Any] | None = None


class IdPClientScope(IdPPayload):
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


class IdPClient(IdPPayload):
    id: str | None = None
    client_id: Annotated[str, pydantic.Field(alias='clientId')]
    name: str
    description: str | None = None
    root_url: Annotated[
        pydantic.AnyHttpUrl | None, pydantic.Field(alias='rootUrl', default=None)
    ]
    admin_url: Annotated[
        pydantic.AnyHttpUrl | None, pydantic.Field(alias='adminUrl', default=None)
    ]
    base_url: Annotated[
        pydantic.AnyHttpUrl | None, pydantic.Field(alias='baseUrl', default=None)
    ]
    redirect_uris: Annotated[
        list[pydantic.AnyHttpUrl] | None,
        pydantic.Field(alias='redirectUris', default=None),
    ]
    web_origins: Annotated[
        list[pydantic.AnyHttpUrl] | None,
        pydantic.Field(alias='webOrigins', default=None),
    ]
    enabled: bool = True
    always_display_in_console: Annotated[
        bool, pydantic.Field(alias='alwaysDisplayInConsole', default=True)
    ]
    secret: pydantic.SecretStr | None = None
    standard_flow_enabled: Annotated[
        bool, pydantic.Field(alias='standardFlowEnabled', default=True)
    ]
    implicit_flow_enabled: Annotated[
        bool, pydantic.Field(alias='implicitFlowEnabled', default=True)
    ]
    direct_access_grants_enabled: Annotated[
        bool, pydantic.Field(alias='directAccessGrantsEnabled', default=False)
    ]
    service_accounts_enabled: Annotated[
        bool, pydantic.Field(alias='serviceAccountsEnabled', default=True)
    ]
    public_client: Annotated[bool, pydantic.Field(alias='publicClient', default=False)]
    protocol: Annotated[str, pydantic.Field(default='openid-connect')]
    attributes: dict[str, Any] | None = None
    protocol_mappers: Annotated[
        list[IdPProtocolMapper], pydantic.Field(alias='protocolMappers')
    ]
    default_client_scopes: Annotated[
        list[str], pydantic.Field(alias='defaultClientScopes', default_factory=list)
    ]
    optional_client_scopes: Annotated[
        list[str], pydantic.Field(alias='optionalClientScopes', default_factory=list)
    ]


class IdPClientRole(IdPPayload):
    id: str | None = None
    name: str
    description: str


class IdPAdmin:
    def __init__(
        self,
        idp_url: str,
        idp_admin_user: str,
        idp_admin_password: str,
        idp_realm: str,
        idp_ca_path: str,
    ):
        self._idp_admin = KeycloakAdmin(
            server_url=idp_url,
            username=idp_admin_user,
            password=idp_admin_password,
            realm_name=idp_realm,
            verify=idp_ca_path,
        )

    def validate(self, admin_user: str) -> IdPValidationResult:
        try:
            user_id = self._idp_admin.get_user_id(admin_user)
            if user_id is None:
                raise IdPException(
                    code=400, msg='Admin user id cannot be found in the realm'
                )
            roles = self._idp_admin.get_realm_roles_of_user(user_id)
            if any(filter(lambda r: r['name'] == 'admin', roles)):
                return IdPValidationResult(
                    changed=False,
                    msg='Connectivity and entitlements are validated',
                    validated=True,
                )
            raise IdPException(code=400, msg='Admin user lacks sufficient permissions')
        except keycloak.exceptions.KeycloakError as ke:
            raise IdPException(code=400, msg='Unable to connect to IdP') from ke

    @staticmethod
    def client_template(
        client_id: str,
        name: str,
        description: str,
        root_url: str,
        callback_url: str | None = None,
    ) -> IdPClient:
        return IdPClient(
            client_id=client_id,
            name=name,
            description=description,
            root_url=pydantic.AnyHttpUrl(root_url),
            redirect_uris=[pydantic.AnyHttpUrl(callback_url)] if callback_url else None,
            attributes={
                'login_theme': 'keycloak.v2',
                'pkce.code.challenge.method': 'S256',
            },
            protocol_mappers=[
                IdPProtocolMapper(
                    name='client roles',
                    config={
                        'introspection.token.claim': False,
                        'multivalued': True,
                        'userinfo.token.claim': True,
                        'id.token.claim': True,
                        'access.token.claim': True,
                        'claim.name': 'roles',
                        'jsonType.label': 'String',
                        'usermodel.clientRoleMapping.clientId': client_id,
                    },
                )
            ],
            default_client_scopes=[
                'profile',
                'basic',
                'email',
            ],
            optional_client_scopes=[
                'organization',
                'offline_access',
                'acr',
                'web-origins',
                'service_account',
                'roles',
            ],
        )

    def client_exists(self, client_id: str) -> bool:
        """
        Check whether a client already exists, so callers can report an
        accurate Ansible 'changed' status instead of always claiming a
        client was created.
        Args:
            client_id (str): The client_id to check
        Returns:
            True if a client with this client_id already exists
        Throws:
            IdPException, when the check itself fails
        """
        try:
            return self._idp_admin.get_client_id(client_id) is not None
        except keycloak.exceptions.KeycloakError as ke:
            raise IdPException from ke

    def client_get(self, client_id: str) -> IdPClient:
        """
        Get a client by client_id
        Args:
            client_id (str): The client_id to get

        Returns:
            The IdPClient representation
        Throws:
            IdPException, when the client_id doesn't exist or its representation cannot be parsed
        """
        try:
            raw_client_id = self._idp_admin.get_client_id(client_id)
            if raw_client_id is None:
                raise IdPException(
                    code=404, msg=f'{client_id} is not a known client_id'
                )
            raw_client = self._idp_admin.get_client(raw_client_id)
            return IdPClient.model_validate(raw_client)
        except pydantic.ValidationError as ve:
            raise IdPException from ve

    def client_create(self, client: IdPClient) -> IdPClient:
        """
        Create an IdP client. Every client gets a default client scope that
        surfaces its own client-roles as a top-level 'roles' claim on issued
        tokens, so callers can rely on that claim without every playbook
        having to wire it up itself. Clients are confidential (non-public),
        so the returned client also carries its credential secret -- fetched
        rather than regenerated, so this is safe to call idempotently
        against an already-existing client.
        Args:
            client (IdPClient): The client to create

        Returns:
            The populated IdPClient, including its secret
        Throws:
            IdPException, when creation fails
        """
        try:
            self._idp_admin.create_client(
                client.model_dump(mode='json'), skip_exists=True
            )
            created = self.client_get(client.client_id)
            created.secret = self.client_secret_get(created)
            return created
        except keycloak.exceptions.KeycloakError as ke:
            raise IdPException from ke

    def client_secret_get(self, client: IdPClient) -> pydantic.SecretStr:
        """
        Fetch a confidential client's current credential secret. Keycloak
        generates this once, at client creation, and keeps it stable across
        re-runs -- this only ever reads it, so calling it repeatedly for the
        same client is idempotent and never rotates the secret.
        Args:
            client (IdPClient): The client to fetch the secret for

        Returns:
            The client's credential secret
        Throws:
            IdPException, when the client lacks an object id or the fetch fails
        """
        try:
            if client.id is None:
                raise IdPException(
                    code=400,
                    msg='Fetching a client secret requires the object id of the client',
                )
            secret = self._idp_admin.get_client_secrets(client_id=client.id)
            return pydantic.SecretStr(secret['value'])
        except keycloak.exceptions.KeycloakError as ke:
            raise IdPException from ke

    def client_remove(self, client_id: str) -> None:
        """
        Remove an IdP client. Idempotent: delete_client takes Keycloak's
        internal object id, not the OAuth client_id, so this resolves it
        first; if no client with this client_id exists, this is a no-op
        rather than an error.
        Args:
            client_id (str): The client_id to remove

        Throws:
            IdPException, when removal fails
        """
        try:
            object_id = self._idp_admin.get_client_id(client_id)
            if object_id is None:
                return
            self._idp_admin.delete_client(object_id)
        except keycloak.exceptions.KeycloakError as ke:
            raise IdPException from ke

    def client_role_create(self, client: IdPClient, role: str, description: str):
        try:
            object_id = client.id
            if object_id is None:
                raise IdPException(
                    code=400, msg='Adding a role requires the object id of the client'
                )
            self._idp_admin.create_client_role(
                client_role_id=object_id,
                payload={'name': role, 'description': description},
                skip_exists=True,
            )
        except keycloak.exceptions.KeycloakError as ke:
            raise IdPException from ke

    def client_scope_create(self, scope: IdPClientScope) -> IdPClientScope:
        """
        Create a client scope
        Args:
            scope (IdPClientScope): The client scope to create

        Returns:
            The populated IdPClientScope
        Throws:
            IdPException, when creation fails
        """
        try:
            scope_id = self._idp_admin.create_client_scope(
                scope.model_dump(mode='json'), skip_exists=True
            )
            return scope.model_copy(update={'id': scope_id})
        except keycloak.exceptions.KeycloakError as ke:
            raise IdPException from ke

    def client_default_scope_add(
        self, client: IdPClient, scope: IdPClientScope
    ) -> None:
        """
        Attach a client scope as a default scope of a client, so its claims
        are always included in tokens issued for that client instead of the
        client having to request the scope explicitly.
        Args:
            client (IdPClient): The client to attach the scope to
            scope (IdPClientScope): The client scope to attach

        Throws:
            IdPException, when either object lacks an object id, or the
            attachment fails
        """
        try:
            if client.id is None or scope.id is None:
                raise IdPException(
                    code=400,
                    msg='Attaching a default client scope requires object ids for both the client and the scope',
                )
            self._idp_admin.add_client_default_client_scope(
                client_id=client.id, client_scope_id=scope.id, payload={}
            )
        except keycloak.exceptions.KeycloakError as ke:
            raise IdPException from ke
