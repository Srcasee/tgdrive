from contextlib import contextmanager

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from config import settings
from database import init_database


pool = ConnectionPool(
    conninfo=settings.DATABASE_URL,
    min_size=settings.DB_POOL_MIN_SIZE,
    max_size=settings.DB_POOL_MAX_SIZE,
    timeout=settings.DB_POOL_TIMEOUT,
    kwargs={"row_factory": dict_row},
    open=False,
)


def open_pool():
    pool.open(wait=True)


def close_pool():
    pool.close()


@contextmanager
def connection():
    with pool.connection() as conn:
        yield conn


@contextmanager
def transaction():
    with pool.connection() as conn:
        with conn.transaction():
            yield conn


def initialize():
    # Schema initialization currently remains in the database module.
    # Repository operations use the shared pool after initialization.
    init_database()
