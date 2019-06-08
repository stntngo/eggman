from __future__ import annotations

import asyncio

import jab
from starlette.applications import Starlette
from starlette.testclient import TestClient
from typing_extensions import Protocol

from eggman import Blueprint, Request, Response, Server, WebSocket, PlainTextResponse


class GetIncr(Protocol):
    def get(self) -> int:
        pass  # pragma: no cover

    def incr(self) -> None:
        pass  # pragma: no cover


class GetDecr(Protocol):
    def get(self) -> int:
        pass  # pragma: no cover

    def decr(self) -> None:
        pass  # pragma: no cover


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


@api.route("/hello")
def hello_world(request: Request) -> Response:
    return PlainTextResponse("Hello, world!")


mounted = Blueprint("mounted", url_prefix="/mounted")
api.mount(mounted)


@mounted.route("/hello")
def hello_mount(request: Request) -> Response:
    return PlainTextResponse("Hello, world!")


home = Blueprint("home", url_prefix="/home")
away = Blueprint("other", url_prefix="/away")
mounted_away = Blueprint("mounted_away")

api.mount(mounted_away)


class Home:
    def __init__(self, db: GetIncr, log: jab.Logger) -> None:
        self.log = log
        self.db = db
        self.name = "eggman"

    @home.route("/go-up")
    async def increment(self, req: Request) -> Response:
        self.db.incr()
        return PlainTextResponse(str(self.db.get()))

    @home.route("/name")
    async def get_name(self, req: Request) -> Response:
        return PlainTextResponse(self.name)

    @home.websocket("/go-up-again")
    async def ws_increment(self, ws: WebSocket) -> None:
        await ws.accept()

        for _ in range(int(ws.query_params.get("n", 0))):
            self.db.incr()
            await ws.send_text(str(self.db.get()))

        await ws.close()


class Other:
    def __init__(self, db: GetDecr) -> None:
        self.db = db

    @away.route("/go-down")
    async def decrement(self, req: Request) -> Response:
        self.db.decr()
        return PlainTextResponse(str(self.db.get()))


class MountedOther:
    def __init__(self, db: GetDecr) -> None:
        self.db = db

    @mounted_away.route("/go-down")
    async def decrement(self, req: Request) -> Response:
        self.db.decr()
        return PlainTextResponse(str(self.db.get()))


@away.websocket("/countdown")
async def countdown(ws: WebSocket) -> Response:
    await ws.accept()
    start = int(ws.query_params.get("n", 10))

    for i in range(start, 0, -1):
        await ws.send_text(str(i))

    await ws.close()


class WsOther:
    def __init__(self) -> None:
        pass

    @away.websocket("/countup")
    async def countup(self, ws: WebSocket) -> Response:
        await ws.accept()
        end = int(ws.query_params.get("n", 10))

        for i in range(end):
            await ws.send_text(str(i))

        await ws.close()


harness = jab.Harness().provide(app.jab, api.jab, home.jab, away.jab, Database)
asyncio.get_event_loop().run_until_complete(harness._on_start())


def test_jab():
    assert isinstance(harness.inspect(Server).obj.starlette, Starlette)


client = TestClient(harness.inspect(Server).obj.starlette)


def test_free_route():
    response = client.get("/api/hello")
    assert response.status_code == 200
    assert response.text == "Hello, world!"


def test_mounted_blueprint():
    response = client.get("/api/mounted/hello")
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

    response = client.get("/api/mounted_away/go-down")
    assert response.status_code == 200
    assert response.text == "-2"

    response = client.get("/home/go-up")
    assert response.status_code == 200
    assert response.text == "-1"

    response = client.get("/home/name")
    assert response.status_code == 200
    assert response.text == "eggman"


def test_websocket():
    n = 10
    path = f"/home/go-up-again?n={n}"
    with client.websocket_connect(path) as websocket:
        for i in range(n):
            data = websocket.receive_text()
            assert data == str(i)

    with client.websocket_connect(f"/away/countdown?n={n}") as websocket:
        for i in range(n, 0, -1):
            data = websocket.receive_text()
            assert data == str(i)

    with client.websocket_connect(f"/away/countup?n={n}") as websocket:
        for i in range(n):
            data = websocket.receive_text()
            assert data == str(i)
