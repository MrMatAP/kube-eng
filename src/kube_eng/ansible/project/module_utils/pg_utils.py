"""PostgreSQL-related tooling"""

import typing

import psycopg2
import pydantic

from .base import InfraException, InfraResult


class PGException(InfraException):
    pass


class PGResult(InfraResult):
    pass


class PGValidationResult(PGResult):
    validated: typing.Annotated[bool, pydantic.Field()]


class PGAdmin:
    def __init__(self, admin_dsn: str):
        self._admin_dsn = admin_dsn

    def validate(self) -> PGValidationResult:
        """
        Validate connectivity and entitlements against PostgreSQL
        Returns:
            A PGValidationResult
        Throws:
            PGException, when connectivity or entitlements are missing
        """
        try:
            with psycopg2.connect(dsn=self._admin_dsn) as conn, conn.cursor() as cur:
                cur.execute(
                    'SELECT rolcreaterole, rolcreatedb FROM pg_roles '
                    'where rolname = current_user;'
                )
                entitlements = cur.fetchone()
                if entitlements is None or not all(entitlements):
                    raise PGException(
                        code=400, msg='Missing connectivity or entitlements'
                    )
            return PGValidationResult(
                changed=False,
                msg='Connectivity and entitlements are granted',
                validated=True,
            )
        except psycopg2.Error as pe:
            raise PGException(code=400, msg=pe.pgerror or 'Unknown Error') from pe
