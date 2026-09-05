"""PostgreSQL-related tooling"""

import typing

import psycopg2
import pydantic
from psycopg2 import sql

from .base import InfraException, InfraResult


class PGException(InfraException):
    pass


class PGResult(InfraResult):
    pass


class PGValidationResult(PGResult):
    validated: typing.Annotated[bool, pydantic.Field()]


class PGDatabaseResult(PGResult):
    db_name: typing.Annotated[str, pydantic.Field()]
    db_user: typing.Annotated[str, pydantic.Field()]


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

    def role_exists(self, db_user: str) -> bool:
        """
        Check whether a role already exists
        Args:
            db_user (str): The role to check

        Returns:
            True if the role exists
        Throws:
            PGException, when the check fails
        """
        try:
            with psycopg2.connect(dsn=self._admin_dsn) as conn, conn.cursor() as cur:
                cur.execute('SELECT 1 FROM pg_roles WHERE rolname = %s;', (db_user,))
                return cur.fetchone() is not None
        except psycopg2.Error as pe:
            raise PGException(code=400, msg=pe.pgerror or 'Unknown Error') from pe

    def database_exists(self, db_name: str) -> bool:
        """
        Check whether a database already exists
        Args:
            db_name (str): The database to check

        Returns:
            True if the database exists
        Throws:
            PGException, when the check fails
        """
        try:
            with psycopg2.connect(dsn=self._admin_dsn) as conn, conn.cursor() as cur:
                cur.execute('SELECT 1 FROM pg_database WHERE datname = %s;', (db_name,))
                return cur.fetchone() is not None
        except psycopg2.Error as pe:
            raise PGException(code=400, msg=pe.pgerror or 'Unknown Error') from pe

    def database_create(
        self, db_name: str, db_user: str, db_password: str
    ) -> PGDatabaseResult:
        """
        Create a database and its dedicated owning role, if they do not
        already exist. Safe to call idempotently: an existing role's
        password is never rotated, same as client_create() in idp_utils.
        Args:
            db_name (str): The database to create
            db_user (str): The role to own the database
            db_password (str): Password for the role, if it needs creating

        Returns:
            A PGDatabaseResult
        Throws:
            PGException, when creation fails
        """
        try:
            role_created = not self.role_exists(db_user)
            db_created = not self.database_exists(db_name)
            with psycopg2.connect(dsn=self._admin_dsn) as conn:
                # CREATE DATABASE cannot run inside a transaction block.
                conn.autocommit = True
                with conn.cursor() as cur:
                    if role_created:
                        cur.execute(
                            sql.SQL('CREATE ROLE {} WITH LOGIN PASSWORD %s').format(
                                sql.Identifier(db_user)
                            ),
                            (db_password,),
                        )
                    if db_created:
                        cur.execute(
                            sql.SQL('CREATE DATABASE {} OWNER {}').format(
                                sql.Identifier(db_name), sql.Identifier(db_user)
                            )
                        )
            return PGDatabaseResult(
                changed=role_created or db_created,
                msg='Database created' if db_created else 'Database is present',
                db_name=db_name,
                db_user=db_user,
            )
        except psycopg2.Error as pe:
            raise PGException(code=400, msg=pe.pgerror or 'Unknown Error') from pe

    def database_remove(self, db_name: str, db_user: str) -> PGDatabaseResult:
        """
        Remove a database and its dedicated owning role. Idempotent: a
        database or role that is already absent is not an error.
        Args:
            db_name (str): The database to remove
            db_user (str): The role owning the database

        Returns:
            A PGDatabaseResult
        Throws:
            PGException, when removal fails
        """
        try:
            db_removed = self.database_exists(db_name)
            role_removed = self.role_exists(db_user)
            with psycopg2.connect(dsn=self._admin_dsn) as conn:
                # DROP DATABASE cannot run inside a transaction block.
                conn.autocommit = True
                with conn.cursor() as cur:
                    if db_removed:
                        cur.execute(
                            sql.SQL('DROP DATABASE {}').format(sql.Identifier(db_name))
                        )
                    if role_removed:
                        cur.execute(
                            sql.SQL('DROP ROLE {}').format(sql.Identifier(db_user))
                        )
            return PGDatabaseResult(
                changed=db_removed or role_removed,
                msg='Database removed' if db_removed else 'Database is absent',
                db_name=db_name,
                db_user=db_user,
            )
        except psycopg2.Error as pe:
            raise PGException(code=400, msg=pe.pgerror or 'Unknown Error') from pe
