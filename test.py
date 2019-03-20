from __future__ import annotations

import asyncio
from typing import Callable

from sanic.request import Request
from sanic.response import HTTPResponse, text
from typing_extensions import Protocol

import vendor as jab
from eggman import Blueprint, Server


class GetIncr(Protocol):
    def get(self) -> int:
        pass

    def incr(self) -> None:
        pass


class GetDecr(Protocol):
    def get(self) -> int:
        pass

    def decr(self) -> None:
        pass


class Database:
    def __init__(self) -> None:
        self._internal = 0

    def get(self) -> int:
        return self._internal

    def incr(self) -> None:
        self._internal += 1

    def decr(self) -> None:
        self._internal -= 1


bp_one = Blueprint("home", url_prefix="/home")
bp_two = Blueprint("other", url_prefix="/other")


class Test:
    def __init__(self, db: GetIncr) -> None:
        self.db = db
        self.name = "niels"
        self.age = 27

    @bp_one.route("/name", methods=["GET"])
    async def get_name(self, req: Request) -> HTTPResponse:
        await asyncio.sleep(0.5)
        self.db.incr()
        return text("{} - {}".format(self.name, self.db.get()))

    @bp_one.route("/other", methods=["POST"])
    def put_other(self, req: Request) -> HTTPResponse:
        return text("other")

    @bp_one.route("/age", methods=["GET"])
    def get_age(self, req: Request) -> HTTPResponse:
        return text(self.age)


class Backward:
    def __init__(self, db: GetDecr) -> None:
        self.db = db
        self.name = "niels"

    @bp_two.route("/backward")
    async def go_backward(self, req: Request) -> HTTPResponse:
        self.db.decr()
        return text("{} - {}".format(str(self.name[::-1]), self.db.get()))


@bp_two.route("/whatever")
def whatever(req: Request) -> HTTPResponse:
    return text("whatever")


app = Server()

jab.Harness().provide(app.jab, bp_one.jab, bp_two.jab, Database).run()
