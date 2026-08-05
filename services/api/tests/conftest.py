"""Session-scoped DB fixtures.

The main `engine` fixture migrates the target database to head once
(idempotent) and is shared by auth/audit/consent/seed tests. Schema tests
create their own throwaway database so they can prove upgrade-from-empty.
"""

from __future__ import annotations

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from tests.db_utils import SKIP_MESSAGE, db_reachable, db_url


def alembic_config(url: str) -> Config:
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


@pytest.fixture(scope="session")
def engine():
    url = db_url()
    if not db_reachable(url):
        pytest.skip(SKIP_MESSAGE)
    command.upgrade(alembic_config(url), "head")
    eng = create_engine(url, pool_pre_ping=True)
    yield eng
    eng.dispose()


@pytest.fixture(scope="session")
def db_session(engine):
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = Session()
    yield session
    session.close()


@pytest.fixture(scope="session")
def seeded_db_session(engine, db_session):
    """Migrated + seeded database (seed is idempotent, safe to rerun)."""
    from app.seed.loader import run_seed

    run_seed(db_session)
    return db_session
