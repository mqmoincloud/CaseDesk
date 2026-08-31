"""NF-02 - the migrations are the schema, and they run both ways.

conftest.py already proves `upgrade head` builds a database the whole suite
works against. These two check the parts that would otherwise go stale: that
the downgrades are real, and that the migrations and the models still agree.
"""

import os
import sqlite3

import pytest
from alembic import command
from alembic.config import Config as AlembicConfig
from sqlalchemy import create_engine

from src.database import Base
import src.models  # noqa: F401 - registers every model on Base.metadata


def alembic_config_for(url):
    config = AlembicConfig("alembic.ini")
    config.set_main_option("sqlalchemy.url", url)
    return config


def table_names(path):
    connection = sqlite3.connect(path)
    rows = connection.execute(
        "select name from sqlite_master"
        " where type='table' and name not like 'sqlite_%' and name != 'alembic_version'"
    ).fetchall()
    connection.close()
    return {name for (name,) in rows}


def columns_of(path, table):
    connection = sqlite3.connect(path)
    rows = connection.execute(f"PRAGMA table_info({table})").fetchall()
    connection.close()
    # name -> (type, not null, default)
    return {row[1]: (row[2], row[3], row[4]) for row in rows}


@pytest.fixture
def scratch_db(tmp_path):
    """An empty database file that no other test touches."""
    return str(tmp_path / "migration_check.db")


def test_the_migrations_run_forwards_backwards_and_forwards_again(scratch_db):
    # A downgrade nobody runs is a downgrade that quietly stops working. This
    # is the check that keeps them honest as migrations pile up.
    config = alembic_config_for(f"sqlite:///{scratch_db}")

    command.upgrade(config, "head")
    assert table_names(scratch_db)

    command.downgrade(config, "base")
    assert table_names(scratch_db) == set()

    command.upgrade(config, "head")
    assert table_names(scratch_db)


def test_the_migrations_build_the_same_schema_as_the_models(scratch_db, tmp_path):
    # The models and the migrations are two descriptions of one schema. If
    # they drift, the app is written against one and the database is the
    # other, and nothing notices until a query fails in production.
    command.upgrade(alembic_config_for(f"sqlite:///{scratch_db}"), "head")

    from_models = str(tmp_path / "from_models.db")
    Base.metadata.create_all(create_engine(f"sqlite:///{from_models}"))

    assert table_names(scratch_db) == table_names(from_models)

    for table in sorted(table_names(scratch_db)):
        assert columns_of(scratch_db, table) == columns_of(from_models, table), table
