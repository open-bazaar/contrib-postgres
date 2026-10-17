"""PostgreSQL backend using the public storage contract."""

from __future__ import annotations

from contextlib import AsyncExitStack, asynccontextmanager, contextmanager
from math import ceil
from time import monotonic
lazy import asyncio
lazy from collections.abc import Awaitable, Callable, Iterator
lazy from typing import Any

import bazaar_contrib_storage as storage
import psycopg
from bazaar_core import Context, Contrib
from pydantic import BaseModel, ConfigDict
lazy from jinja2 import Environment
lazy from psycopg.rows import dict_row

from .compiler import Compiler, load_templates, schema_sql


class Config(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    dsn: str


@contextmanager
def errors() -> Iterator[None]:
    try:
        yield
    except psycopg.errors.QueryCanceled as error:
        raise storage.StorageQueryTimeoutError(str(error)) from error
    except psycopg.IntegrityError as error:
        raise storage.StorageIntegrityError(str(error)) from error
    except psycopg.OperationalError as error:
        raise storage.StorageUnavailableError(str(error)) from error
    except psycopg.Error as error:
        raise storage.StorageQueryError(str(error)) from error


class Session:
    def __init__(
        self,
        connection: psycopg.AsyncConnection[dict[str, Any]],
        templates: Environment,
        *,
        query_budget: float | None = None,
    ) -> None:
        self._connection = connection
        self._templates = templates
        self.closed = False
        self._deadline = None if query_budget is None else monotonic() + query_budget

    async def _execute(
        self, statement: str, parameters: tuple[storage.Scalar, ...]
    ) -> storage.Mutation:
        if self.closed:
            raise storage.StorageClosedError("PostgreSQL session has closed")
        with errors():
            async with psycopg.AsyncRawCursor(self._connection) as cursor:
                if self._deadline is not None:
                    remaining = self._deadline - monotonic()
                    if remaining <= 0:
                        raise storage.StorageQueryTimeoutError(
                            "query execution budget exceeded"
                        )
                    compiler = Compiler(self._templates)
                    budget = compiler.render(
                        "query_budget.sql.tpl", milliseconds=ceil(remaining * 1000)
                    )
                    await cursor.execute(
                        budget.encode("utf-8"), tuple(compiler.parameters)
                    )
                await cursor.execute(statement.encode("utf-8"), parameters)
                rows = (
                    tuple(await cursor.fetchall())
                    if cursor.description is not None
                    else ()
                )
                return storage.Mutation(count=max(cursor.rowcount, 0), rows=rows)

    async def select(self, request: storage.Select) -> tuple[storage.Record, ...]:
        compiler = Compiler(self._templates)
        statement = compiler.render("select.sql.tpl", request=request)
        return (await self._execute(statement, tuple(compiler.parameters))).rows

    async def copy(self, request: storage.Copy) -> storage.Mutation:
        compiler = Compiler(self._templates)
        statement = compiler.render("copy.sql.tpl", request=request)
        return await self._execute(statement, tuple(compiler.parameters))

    async def table_exists(self, name: str) -> bool:
        result = await self._execute(
            "SELECT 1 FROM pg_class WHERE oid = to_regclass($1) AND relkind IN ('r', 'p')",
            (name,),
        )
        return bool(result.rows)

    async def insert(self, request: storage.Insert) -> storage.Mutation:
        compiler = Compiler(self._templates)
        statement = compiler.render("insert.sql.tpl", request=request)
        return await self._execute(statement, tuple(compiler.parameters))

    async def update(self, request: storage.Update) -> storage.Mutation:
        compiler = Compiler(self._templates)
        statement = compiler.render("update.sql.tpl", request=request)
        return await self._execute(statement, tuple(compiler.parameters))

    async def delete(self, request: storage.Delete) -> storage.Mutation:
        compiler = Compiler(self._templates)
        statement = compiler.render("delete.sql.tpl", request=request)
        return await self._execute(statement, tuple(compiler.parameters))

    async def apply_schema(
        self, operations: tuple[storage.SchemaOperation, ...]
    ) -> None:
        for operation in operations:
            for statement in schema_sql(operation, self._templates):
                await self._execute(statement, ())


class Database(Session):
    def __init__(
        self,
        connection: psycopg.AsyncConnection[dict[str, Any]],
        templates: Environment,
    ) -> None:
        super().__init__(connection, templates)
        self._lock = asyncio.Lock()

    async def _execute(
        self, statement: str, parameters: tuple[storage.Scalar, ...]
    ) -> storage.Mutation:
        async with self._lock:
            return await super()._execute(statement, parameters)

    async def read[T](
        self,
        operation: Callable[[storage.Session], Awaitable[T]],
        *,
        snapshot: bool = False,
        query_budget: float | None = None,
    ) -> T:
        async with self._lock:
            if self.closed:
                raise storage.StorageClosedError("PostgreSQL backend has closed")
            with errors():
                async with self._connection.transaction():
                    async with psycopg.AsyncRawCursor(self._connection) as cursor:
                        statement = self._templates.get_template("read.sql.tpl").render(
                            snapshot=snapshot
                        )
                        await cursor.execute(statement.encode("utf-8"))
                    session = Session(
                        self._connection, self._templates, query_budget=query_budget
                    )
                    try:
                        return await operation(session)
                    finally:
                        session.closed = True

    async def write[T](
        self,
        operation: Callable[[storage.Session], Awaitable[T]],
        *,
        transactional: bool = False,
    ) -> T:
        async with self._lock:
            if self.closed:
                raise storage.StorageClosedError("PostgreSQL backend has closed")
            with errors():
                async with AsyncExitStack() as stack:
                    if transactional:
                        await stack.enter_async_context(self._connection.transaction())
                    session = Session(self._connection, self._templates)
                    try:
                        return await operation(session)
                    finally:
                        session.closed = True

    async def transaction[T](
        self, operation: Callable[[storage.Session], Awaitable[T]]
    ) -> T:
        return await self.write(operation, transactional=True)

    async def apply_schema(
        self, operations: tuple[storage.SchemaOperation, ...]
    ) -> None:
        await self.transaction(lambda session: session.apply_schema(operations))

    async def close(self) -> None:
        async with self._lock:
            self.closed = True
            await self._connection.close()


@asynccontextmanager
async def lifespan(ctx: Context, config: Config):
    templates = await asyncio.to_thread(load_templates)
    with errors():
        connection = await psycopg.AsyncConnection[dict[str, Any]].connect(
            config.dsn, autocommit=True, row_factory=dict_row
        )
    database = Database(connection, templates)
    try:
        with ctx.accept(storage.STORAGE).register("postgres", database):
            ctx.offer(storage.backend_key("postgres"), database)
            yield
    finally:
        await database.close()


postgres = Contrib(
    config=Config,
    accepts=[storage.STORAGE],
    offers=[storage.backend_key("postgres")],
    lifespan=lifespan,
)
