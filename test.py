from __future__ import annotations

import asyncio

import jab
from jab import Logger
from starlette.responses import PlainTextResponse
from typing_extensions import Protocol

from eggman import Blueprint, Request, Response, Server, WebSocket


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
    def __init__(self, db: GetIncr, log: Logger, _db: GetDecr) -> None:
        self.log = log
        self.db = db
        self._db = _db
        self.name = "niels"
        self.age = 27

    @bp_one.route("/name", methods=["GET"])
    async def get_name(self, req: Request) -> Response:
        await asyncio.sleep(0.5)
        self.db.incr()
        return PlainTextResponse("{} - {}".format(self.name, self.db.get()))

    @bp_one.route("/other", methods=["POST"])
    def put_other(self, req: Request) -> Response:
        return PlainTextResponse("other")

    @bp_one.route("/age", methods=["GET"])
    def get_age(self, req: Request) -> Response:
        return PlainTextResponse(str(self.age))

    @bp_one.websocket("/backward")
    async def go_backward(self, ws: WebSocket) -> None:
        await ws.accept()
        for _ in range(1000):
            self._db.decr()
            msg = f"{self.name[::-1]} - {self.db.get()}"
            await ws.send_text(msg)
            await asyncio.sleep(0.5)
        await ws.close()


class Backward:
    def __init__(self, db: GetDecr, log: Logger) -> None:
        self.log = log
        self.db = db
        self.name = "niels"

    @bp_two.websocket("/backward")
    async def go_backward(self, ws: WebSocket) -> None:
        await ws.accept()
        for _ in range(100):
            self.db.decr()
            msg = f"{self.name[::-1]} - {self.db.get()}"
            await ws.send_text(msg)
        await ws.close()


@bp_two.route("/whatever")
def whatever(req: Request) -> Response:
    return PlainTextResponse("whatever")


app = Server()

harness = jab.Harness().provide(app.jab, bp_one.jab, bp_two.jab, Database)
