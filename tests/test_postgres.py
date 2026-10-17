"""Exercise backend selection through the public contribs with an isolated PG."""

from __future__ import annotations

from contextlib import asynccontextmanager
lazy import asyncio
lazy import os
lazy from pathlib import Path

import pytest
from bazaar_contrib_schema import SCHEMA, Migration, ModuleSchema, schema
from bazaar_contrib_sqlite import sqlite
from bazaar_contrib_storage import (
    DB,
    STORAGE,
    BackendRegistry,
    ColumnDefinition,
    CreateTable,
    Database,
    Insert,
    Select,
    Table,
    backend_key,
    database,
    storage,
)
from bazaar_contrib_storage import models as s
from bazaar_core import Composition, Context, Contrib, ContribEntry, ContribHub

from bazaar_contrib_postgres import postgres

pytestmark = pytest.mark.e2e


async def test_two_real_backends_keep_the_consumer_and_schema_unchanged(tmp_path: Path):

    dsn = os.environ.get("BCN_TEST_POSTGRES_DSN")
    if not dsn:
        pytest.skip("supply an owned isolated PostgreSQL database")
    services: list[Database] = []
    registries: list[BackendRegistry] = []
    module = ModuleSchema(
        package="example-switching-consumer",
        tables=("switching_notes",),
        migrations=(
            Migration(
                version=1,
                name="notes",
                operations=(
                    CreateTable(
                        table=Table(
                            name="switching_notes",
                            columns=(ColumnDefinition(name="body", type="text"),),
                        )
                    ),
                ),
            ),
        ),
    )

    @asynccontextmanager
    async def consumer(ctx: Context):
        db = ctx.accept(DB)
        services.append(db)
        async with ctx.accept(SCHEMA).register(module):
            await db.write(
                lambda session: session.insert(
                    Insert(table="switching_notes", rows=({"body": "same consumer"},))
                )
            )
            yield

    @asynccontextmanager
    async def observer(ctx: Context):
        registries.append(ctx.accept(STORAGE))
        yield

    composition = Composition(
        entries=(
            ContribEntry(name="storage", definition=storage),
            ContribEntry(
                name="sqlite",
                definition=sqlite,
                config={"path": str(tmp_path / "switching.sqlite3")},
            ),
            ContribEntry(
                name="postgres",
                definition=postgres,
                config={"dsn": dsn},
            ),
            ContribEntry(
                name="database", definition=database, config={"backend": "sqlite"}
            ),
            ContribEntry(name="schema", definition=schema),
            ContribEntry(
                name="consumer",
                definition=Contrib(accepts=[DB, SCHEMA], lifespan=consumer),
            ),
            ContribEntry(
                name="observer",
                definition=Contrib(
                    accepts=[
                        STORAGE,
                        backend_key("sqlite"),
                        backend_key("postgres"),
                    ],
                    lifespan=observer,
                ),
            ),
        ),
        roots=("consumer", "observer"),
    )
    query = Select(
        table="ranked",
        ctes={
            "ranked": Select(
                table="switching_notes",
                columns={
                    "body": s.Case(
                        when=s.Contains(
                            expression=s.Column(name="body"), text="consumer"
                        ),
                        then=s.Column(name="body"),
                        otherwise=s.Value(value=None),
                    ),
                    "position": s.RowNumber(
                        partition_by=(s.Column(name="body"),),
                        order_by=(s.Sort(expression=s.RowId()),),
                    ),
                    "total": s.Subquery(
                        query=Select(
                            table="switching_notes",
                            columns={"count": s.Call(name="count")},
                        )
                    ),
                },
            )
        },
        where=s.Compare(
            left=s.Column(name="position"), operator="=", right=s.Value(value=1)
        ),
    )
    async with (
        asyncio.timeout(15),
        ContribHub() as hub,
        hub.enable(composition) as enabled,
    ):
        registry = registries[-1]
        assert set(registry.names) == {"sqlite", "postgres"}
        assert services[-1] is registry.get("sqlite")
        assert (
            await services[-1].read(
                lambda session: session.select(query), snapshot=True, query_budget=5.0
            )
        )[0]["body"] == "same consumer"
        composition = composition.model_copy(
            update={
                "entries": tuple(
                    entry.model_copy(update={"config": {"backend": "postgres"}})
                    if entry.name == "database"
                    else entry
                    for entry in composition.entries
                )
            }
        )
        await enabled.update(composition)
        assert services[-1] is registry.get("postgres")
        assert (
            await services[-1].read(
                lambda session: session.select(query), snapshot=True, query_budget=5.0
            )
        )[0]["body"] == "same consumer"
