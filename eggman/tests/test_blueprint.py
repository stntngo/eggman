from __future__ import annotations

import asyncio

import jab
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.testclient import TestClient
from typing_extensions import Protocol

from eggman import Blueprint, Request, Response, Server


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


app = Server()
api = Blueprint("api", url_prefix="/api")


class ApiHandlers:
    def __init__(self) -> None:
        pass

    @api.route("/hello")
    async def hello_world(self, request: Request) -> Response:
        return PlainTextResponse("Hello, world!")


home = Blueprint("home", url_prefix="/home")
away = Blueprint("other", url_prefix="/away")


class Home:
    def __init__(self, db: GetIncr, log: jab.Logger) -> None:
        self.log = log
        self.db = db
        self.name = "eggman"

    @home.route("/go-up")
    async def increment(self, req: Request) -> Response:
        self.db.incr()
        return PlainTextResponse(str(self.db.get()))


class Other:
    def __init__(self, db: GetDecr) -> None:
        self.db = db

    @away.route("/go-down")
    async def decrement(self, req: Request) -> Response:
        self.db.decr()
        return PlainTextResponse(str(self.db.get()))


harness = jab.Harness().provide(app.jab, api.jab, home.jab, away.jab, Database)
asyncio.get_event_loop().run_until_complete(harness._on_start())


def test_jab():
    assert isinstance(harness.inspect(Server).obj.starlette, Starlette)


client = TestClient(harness.inspect(Server).obj.starlette)


def test_free_route():
    response = client.get("/api/hello")
    assert response.status_code == 200
    assert response.text == "Hello, world!"


def test_blueprint_wiring():
    response = client.get("/home/go-up")
    assert response.status_code == 200
    assert response.text == "1"

    response = client.get("/away/go-down")
    assert response.status_code == 200
    assert response.text == "0"

    response = client.get("/away/go-down")
    assert response.status_code == 200
    assert response.text == "-1"
