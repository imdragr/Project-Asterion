from collections.abc import Iterator

import pytest
from sqlalchemy import Engine, create_engine
from testcontainers.postgres import PostgresContainer


@pytest.fixture(scope="session")
def alembic_engine() -> Iterator[Engine]:
    with PostgresContainer("postgres:17") as pg:
        # sync driver here on purpose — see the gotcha below
        yield create_engine(pg.get_connection_url())
