"""S3-related tooling"""

import json
import typing
import xml.etree.ElementTree

import boto3
import botocore.auth
import botocore.awsrequest
import botocore.client
import botocore.credentials
import botocore.exceptions
import pydantic
import requests

from .base import InfraException, InfraResult

S3AccountRole = typing.Literal['admin', 'contributor', 'viewer']

# RustFS's admin API is modelled on MinIO's built-in (canned) policies. These
# are the only three kube-eng grants; custom policy authoring would need the
# policy-create endpoint, which isn't needed for the roles we support.
_ROLE_CANNED_POLICY: dict[S3AccountRole, str] = {
    'admin': 'consoleAdmin',
    'contributor': 'readwrite',
    'viewer': 'readonly',
}


class S3Exception(InfraException):
    pass


class S3Result(InfraResult):
    pass


class S3ValidationResult(S3Result):
    validated: typing.Annotated[bool, pydantic.Field()]


class S3BucketResult(S3Result):
    bucket_name: typing.Annotated[str, pydantic.Field()]


class S3AccountResult(S3Result):
    access_key: typing.Annotated[str, pydantic.Field()]
    role: typing.Annotated[str | None, pydantic.Field(default=None)]


class S3Admin:
    def __init__(
        self,
        s3_endpoint: str,
        s3_access_key: str,
        s3_secret_key: str,
        s3_region: str,
        s3_ca_path: str,
    ):
        self._s3 = boto3.client(
            's3',
            endpoint_url=s3_endpoint,
            use_ssl=True,
            verify=s3_ca_path,
            aws_access_key_id=s3_access_key,
            aws_secret_access_key=s3_secret_key,
            config=botocore.client.Config(signature_version='s3v4'),
            region_name=s3_region,
        )
        # The admin (account/policy) API is separate from the S3 data-plane
        # API boto3 speaks, so it's called directly below rather than
        # through boto3/botocore's client machinery.
        self._admin_endpoint = s3_endpoint.rstrip('/')
        self._admin_region = s3_region
        self._admin_ca_path = s3_ca_path
        self._admin_credentials = botocore.credentials.Credentials(
            s3_access_key, s3_secret_key
        )

    def validate(self) -> S3ValidationResult:
        """
        Validate connectivity and entitlements against S3
        Returns:
            An S3ValidationResult
        Throws:
            S3Exception, when connectivity or entitlements are missing
        """
        try:
            self._s3.list_buckets()
            return S3ValidationResult(
                changed=False,
                msg='Connectivity and entitlements are validated',
                validated=True,
            )
        except botocore.exceptions.EndpointConnectionError as ee:
            raise S3Exception(code=400, msg='Unable to connect to S3') from ee
        except botocore.exceptions.ClientError as ce:
            raise S3Exception(
                code=400, msg='Missing connectivity or entitlements'
            ) from ce

    def bucket_exists(self, bucket_name: str) -> bool:
        """
        Check whether a bucket exists
        Args:
            bucket_name (str): The bucket to check

        Returns:
            True if the bucket exists, False otherwise
        Throws:
            S3Exception, when the check fails for a reason other than the bucket being absent
        """
        try:
            self._s3.head_bucket(Bucket=bucket_name)
            return True
        except botocore.exceptions.ClientError as ce:
            status_code = ce.response.get('ResponseMetadata', {}).get('HTTPStatusCode')
            if status_code == 404:
                return False
            raise S3Exception(code=status_code or 400, msg=str(ce)) from ce

    def bucket_create(self, bucket_name: str) -> S3BucketResult:
        """
        Create a bucket, if it does not already exist
        Args:
            bucket_name (str): The bucket to create

        Returns:
            An S3BucketResult
        Throws:
            S3Exception, when creation fails
        """
        if self.bucket_exists(bucket_name):
            return S3BucketResult(
                changed=False, msg='Bucket is present', bucket_name=bucket_name
            )
        try:
            self._s3.create_bucket(Bucket=bucket_name)
            return S3BucketResult(
                changed=True, msg='Bucket created', bucket_name=bucket_name
            )
        except botocore.exceptions.ClientError as ce:
            raise S3Exception(code=400, msg=str(ce)) from ce

    def bucket_remove(self, bucket_name: str) -> S3BucketResult:
        """
        Remove a bucket, if it exists
        Args:
            bucket_name (str): The bucket to remove

        Returns:
            An S3BucketResult
        Throws:
            S3Exception, when removal fails
        """
        if not self.bucket_exists(bucket_name):
            return S3BucketResult(
                changed=False, msg='Bucket is absent', bucket_name=bucket_name
            )
        try:
            self._s3.delete_bucket(Bucket=bucket_name)
            return S3BucketResult(
                changed=True, msg='Bucket deleted', bucket_name=bucket_name
            )
        except botocore.exceptions.ClientError as ce:
            raise S3Exception(code=400, msg=str(ce)) from ce

    # -- Accounts and permissions --------------------------------------
    #
    # RustFS exposes a MinIO-style admin API under /rustfs/admin/v3/ for
    # managing IAM-like "accounts" (access key/secret key pairs) and
    # attaching canned policies to them. There's no SDK and no published
    # wire-format spec for it -- the calls below were verified empirically
    # against a live RustFS instance rather than from documentation. If a
    # future RustFS release changes this, _admin_request is the one place
    # to fix.

    def _admin_request(
        self,
        method: str,
        path: str,
        params: dict | None = None,
        json_body: dict | None = None,
    ) -> dict:
        """
        Make a SigV4-signed call to the RustFS admin API.
        Args:
            method (str): HTTP method
            path (str): Path under /rustfs/admin/v3/, e.g. 'add-user'
            params (dict | None): Query parameters
            json_body (dict | None): JSON request body

        Returns:
            The decoded JSON response body, or {} for an empty response
        Throws:
            S3Exception, when the request fails
        """
        url = f'{self._admin_endpoint}/rustfs/admin/v3/{path}'
        data = json.dumps(json_body) if json_body is not None else None
        request = botocore.awsrequest.AWSRequest(
            method=method, url=url, params=params, data=data
        )
        botocore.auth.S3SigV4Auth(
            self._admin_credentials, 's3', self._admin_region
        ).add_auth(request)
        prepared = request.prepare()
        try:
            response = requests.request(
                method,
                prepared.url,
                headers=dict(prepared.headers),
                data=data,
                verify=self._admin_ca_path,
                timeout=10,
            )
        except requests.RequestException as re:
            raise S3Exception(
                code=400, msg=f'Unable to reach the S3 admin API: {re}'
            ) from re

        if not response.ok:
            raise S3Exception(
                code=response.status_code, msg=self._admin_error_message(response)
            )
        if not response.text:
            return {}
        try:
            return response.json()
        except ValueError as ve:
            raise S3Exception(
                code=502, msg=f'Unexpected admin API response: {response.text[:200]}'
            ) from ve

    @staticmethod
    def _admin_error_message(response: requests.Response) -> str:
        """Admin API errors come back as S3-style XML, not JSON."""
        try:
            root = xml.etree.ElementTree.fromstring(response.text)
            message = root.findtext('Message')
            code = root.findtext('Code')
            if message:
                return f'{code}: {message}' if code else message
        except xml.etree.ElementTree.ParseError:
            pass
        return response.text or f'HTTP {response.status_code}'

    def account_exists(self, access_key: str) -> bool:
        """
        Check whether a dedicated S3 account already exists.
        Args:
            access_key (str): The account's access key

        Returns:
            True if an account with this access key exists
        Throws:
            S3Exception, when the check fails for a reason other than the account being absent
        """
        try:
            self._admin_request('GET', 'user-info', params={'accessKey': access_key})
            return True
        except S3Exception as se:
            if se.code == 404:
                return False
            raise

    def account_policy_get(self, access_key: str) -> set[str]:
        """
        Get the set of policy names currently attached to an account.
        Args:
            access_key (str): The account's access key

        Returns:
            The set of attached policy names (empty if none)
        Throws:
            S3Exception, when the account doesn't exist or the fetch fails
        """
        info = self._admin_request('GET', 'user-info', params={'accessKey': access_key})
        policy_name = info.get('policyName', '')
        return {p for p in policy_name.split(',') if p}

    def account_create(self, access_key: str, secret_key: str) -> bool:
        """
        Create a dedicated S3 account (an access key/secret key pair), or
        set its secret key if it already exists. Accounts can't have their
        secret key read back once set, so callers are expected to supply a
        stable, persisted secret_key -- calling this repeatedly with the
        same value is then idempotent in effect, even though the admin API
        itself doesn't report whether the secret actually changed.
        Args:
            access_key (str): The account's access key
            secret_key (str): The account's secret key

        Returns:
            True if the account did not already exist (i.e. was created)
        Throws:
            S3Exception, when creation fails
        """
        already_existed = self.account_exists(access_key)
        self._admin_request(
            'PUT',
            'add-user',
            params={'accessKey': access_key},
            json_body={'secretKey': secret_key, 'status': 'enabled'},
        )
        return not already_existed

    def account_role_set(self, access_key: str, role: S3AccountRole) -> bool:
        """
        Ensure exactly the canned policy for the given role is attached to
        an account, detaching any others. RustFS's policy/attach endpoint is
        additive -- it accumulates policies rather than replacing them -- so
        this diffs against the account's current policies to converge on
        exactly one.
        Args:
            access_key (str): The account's access key
            role (S3AccountRole): The role to grant

        Returns:
            True if the account's attached policies changed
        Throws:
            S3Exception, when the change fails
        """
        target_policy = _ROLE_CANNED_POLICY[role]
        current_policies = self.account_policy_get(access_key)
        if current_policies == {target_policy}:
            return False
        extra_policies = current_policies - {target_policy}
        if extra_policies:
            self._admin_request(
                'POST',
                'idp/builtin/policy/detach',
                json_body={'policies': sorted(extra_policies), 'user': access_key},
            )
        if target_policy not in current_policies:
            self._admin_request(
                'POST',
                'idp/builtin/policy/attach',
                json_body={'policies': [target_policy], 'user': access_key},
            )
        return True

    def account_ensure(
        self, access_key: str, secret_key: str, role: S3AccountRole
    ) -> S3AccountResult:
        """
        Ensure a dedicated S3 account exists with exactly the given role.
        Args:
            access_key (str): The account's access key -- conventionally the
                identity of the client it's dedicated to
            secret_key (str): The account's secret key
            role (S3AccountRole): The role to grant: 'admin', 'contributor'
                or 'viewer'

        Returns:
            An S3AccountResult
        Throws:
            S3Exception, when creation or role assignment fails
        """
        created = self.account_create(access_key, secret_key)
        role_changed = self.account_role_set(access_key, role)
        if created:
            msg = 'Account created'
        elif role_changed:
            msg = 'Account role updated'
        else:
            msg = 'Account is present'
        return S3AccountResult(
            changed=created or role_changed, msg=msg, access_key=access_key, role=role
        )

    def account_remove(self, access_key: str) -> S3AccountResult:
        """
        Remove a dedicated S3 account, if it exists.
        Args:
            access_key (str): The account's access key

        Returns:
            An S3AccountResult
        Throws:
            S3Exception, when removal fails
        """
        if not self.account_exists(access_key):
            return S3AccountResult(
                changed=False, msg='Account is absent', access_key=access_key
            )
        self._admin_request('DELETE', 'remove-user', params={'accessKey': access_key})
        return S3AccountResult(
            changed=True, msg='Account removed', access_key=access_key
        )
