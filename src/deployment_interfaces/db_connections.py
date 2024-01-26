"""Database connection classes.

This module is designed to be reusable and project-agnostic.

Todos:
    Make class attributes lower_case.
"""

import dataclasses
import os
from contextlib import contextmanager
from typing import Union

import pandas as pd
import psycopg2
import psycopg2.pool
import sqlalchemy


@dataclasses.dataclass
class DbServerConnection:
    """Parameters for connecting to an arbitrary database server."""

    HOSTNAME: str
    PORT: Union[int, None] = None

    USERNAME: str = os.getenv("DB_SERVERS_USERNAME")
    PASSWORD: str = os.getenv("DB_SERVERS_PASSWORD")

    @property
    def connection_uri(self) -> str:
        connection_uri = f"postgresql://{self.USERNAME}:{self.PASSWORD}@{self.HOSTNAME}"
        if self.PORT is not None:
            connection_uri += f":{self.PORT}"
        return connection_uri


@dataclasses.dataclass
class DbConnection:
    """Connection to a database of a given name on a given database server."""

    DB_SERVER: DbServerConnection = dataclasses.field(init=False)
    DB_NAME: str = dataclasses.field(init=False)

    CONNECTION_POOL_MINCONN: int = 1
    CONNECTION_POOL_MAXCONN: int = 10

    _connection_pool: psycopg2.pool.SimpleConnectionPool = dataclasses.field(init=False)

    def __post_init__(self):
        # Are the corresponding environment variables set?
        assert self.DB_SERVER.HOSTNAME is not None
        assert self.DB_SERVER.USERNAME is not None
        assert self.DB_SERVER.PASSWORD is not None

        self._connect()

    def _connect(self) -> None:
        """Connect to the database using its server's hostname, its database name, and credentials
        (username and password) that have appropriate permissions.
        """

        print(f"Connecting to '{self.DB_NAME}' database...")

        # If running locally and you get OperationalError "FATAL:  no pg_hba.conf entry for host..."
        #     then check that you are connected to the BluWave office VPN or your GCP instance's
        #     public IP is whitelisted on the BluWave database servers.
        self._connection_pool = psycopg2.pool.SimpleConnectionPool(
            minconn=self.CONNECTION_POOL_MINCONN,
            maxconn=self.CONNECTION_POOL_MAXCONN,
            dbname=self.DB_NAME,
            user=self.DB_SERVER.USERNAME,
            password=self.DB_SERVER.PASSWORD,
            host=self.DB_SERVER.HOSTNAME,
            port=self.DB_SERVER.PORT,
        )  # Instead of `psycopg2.connect(...)`.

    @contextmanager
    def _get_cursor(self):
        """Yield a database cursor from the simple connection pool."""

        conn = self._connection_pool.getconn()

        # Automatically commit changes; automatically make the changes to the database persistent:
        conn.autocommit = True

        print(f"'{self.DB_NAME}' database connection status: {conn.status}")

        try:
            with conn.cursor() as cursor:
                yield cursor
        finally:
            self._connection_pool.putconn(conn)

    def query(self, query, vars=None, output: bool = True) -> Union[pd.DataFrame, None]:
        """Execute an operation (query or command) on the database.

        Args:
            query: The query or command.
            output (bool): Whether the query is, in fact, a command and thus there is no output to
                fetch; no DataFrame of records will be returned.

        Returns:
            Union[pd.DataFrame, None]: The DataFrame of records resulting from the query.
                There is no return value (the return value is None) if the query itself fails or if
                called with ``output=False``.
        """

        with self._get_cursor() as cur:
            cur.execute(query, vars)
            if not output:
                return None
            output = cur.fetchall()
            header = [[desc[0] for desc in cur.description]]
            df = pd.DataFrame(data=output, columns=header[0], dtype=object)
            # ^ `dtype=object` avoids pandas typecasting `dt.datetime`s to `pd.Timestamp`s and
            #     `None`s to `np.nan` (in a column with `float`s) or `pd.NaT` (in a column with
            #     `pd.Timestamp`s), which would be inconsistent and would not match type hints of
            #     modeling object dataclasses.
            return df

    @property
    def connection_uri(self) -> str:
        return self.DB_SERVER.connection_uri + "/" + self.DB_NAME

    def create_sqlalchemy_engine(self) -> sqlalchemy.Engine:
        """Create an SQLAlchemy ``Engine`` which is useful, e.g., in
        ``df.to_sql(..., con=<sqlalchemy-engine>)``.

        NOTE: Not created for production-grade deployments (does not use ``self._get_cursor``).
        """

        return sqlalchemy.create_engine(self.connection_uri)


# ==================================================================================================
# High- and low-volume database server connections


# Connection to a server with high-volume database:
high_vol_db_server = DbServerConnection(
    HOSTNAME=os.getenv("HIGH_VOL_DB_SERVER_HOSTNAME")
)

# Connection to a server with low-volume database:
low_vol_db_server = DbServerConnection(HOSTNAME=os.getenv("LOW_VOL_DB_SERVER_HOSTNAME"))

# --------------------------------------------------------------------------------------------------
# Connection to servers with high- and low-volume databases, but for access from a development
#     machine that has been configured with port forwarding to BluWave's proxy gateway
#     according to https://bluwave-ai.atlassian.net/wiki/spaces/ENG/pages/2863890433
# Not for deployments.
# Only works with the real databases (not locally mocked ones).

high_vol_db_server_local_access = DbServerConnection(HOSTNAME="localhost", PORT=45432)
# ^ Port forwarding should resolve this to hostname
#     "dev-shared-hv-postgresql.postgres.database.azure.com" with port 5432.
low_vol_db_server_local_access = DbServerConnection(HOSTNAME="localhost", PORT=35432)
# ^ Port forwarding should resolve this to hostname
#     "dev-shared-lv-postgresql.postgres.database.azure.com" with port 5432.


# ==================================================================================================
# Connections to databases on the high- and low-volume database servers
# Add as necessary.


class HighVolDb(DbConnection):
    """Connection to high-volume database on a high-volume database server."""

    DB_SERVER = high_vol_db_server
    DB_NAME = "dev"


class LowVolDb(DbConnection):
    """Connection to low-volume database on a low-volume database server."""

    DB_SERVER = low_vol_db_server
    DB_NAME = "dev_low_volume"


# --------------------------------------------------------------------------------------------------
# Connection to high- and low-volume databases on respective servers, but for access from a
#     development machine that has been configured with port forwarding to BluWave's proxy gateway
#     according to https://bluwave-ai.atlassian.net/wiki/spaces/ENG/pages/2863890433
# Not for deployments.
# Only works with the real databases (not locally mocked ones).


class HighVolDbLocalAccess(DbConnection):
    """Connection to high-volume database on a high-volume database server."""

    DB_SERVER = high_vol_db_server_local_access
    DB_NAME = "dev"


class LowVolDbLocalAccess(DbConnection):
    """Connection to low-volume database on a low-volume database server."""

    DB_SERVER = low_vol_db_server_local_access
    DB_NAME = "dev_low_volume"


# ==================================================================================================


if __name__ == "__main__":
    high_vol_db = HighVolDb()
    low_vol_db = LowVolDb()
