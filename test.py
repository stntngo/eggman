import asyncio
from typing import Any, Callable

from sanic import Sanic
from sanic.request import Request
from sanic.response import HTTPResponse, text

import vendor as jab
from eggman import Blueprint
from typing_extensions import Protocol


class SanicWrapper:
    def __init__(self) -> None:
        self._app = Sanic(__name__)

    def add_route(self, fn: Callable, rule: str, **kwargs: Any) -> None:
        self._app.add_route(fn, rule, **kwargs)

    async def run(self) -> None:
        server = await self._app.create_server()
        await server.wait_closed()


class GetIncr(Protocol):
    def get(self) -> int:
        pass

    def incr(self) -> None:
        pass


class Database:
    def __init__(self) -> None:
        self._internal = 0

    def get(self) -> int:
        return self._internal

    def incr(self) -> None:
        self._internal += 1


test = Blueprint("/home")


class Test:
    def __init__(self, db: GetIncr) -> None:
        self.db = db
        self.name = "niels"
        self.age = 27

    @test.route("/name", methods=["GET"])
    async def get_name(self, req: Request) -> HTTPResponse:
        await asyncio.sleep(0.5)
        self.db.incr()
        return text("{} - {}".format(self.name, self.db.get()))

    @test.route("/other", methods=["POST"])
    def put_other(self, req: Request) -> HTTPResponse:
        return text("other")

    @test.route("/age", methods=["GET"])
    def get_age(self, req: Request) -> HTTPResponse:
        return text(self.age)


class Backward:
    def __init__(self) -> None:
        self.name = "niels"

    @test.route("/backward")
    async def backward(self, req: Request) -> HTTPResponse:
        return text(str(self.name[::-1]))


jab.Harness().provide(SanicWrapper, test.jab, Database).run()
