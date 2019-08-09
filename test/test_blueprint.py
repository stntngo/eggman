from __future__ import annotations

import asyncio
from typing import Any, List

import jab
import pytest
from starlette.applications import Starlette
from starlette.testclient import TestClient
from typing_extensions import Protocol

from eggman import Blueprint, BlueprintAlreadyInvoked, PlainTextResponse, Request, Response, Server, WebSocket
from eggman.types import Handler, WebSocketHandler


class MockServer:
    def __init__(self) -> None:
        self._routes: List[str] = []
        self._websockets: List[str] = []

    def add_route(self, fn: Handler, rule: str, **options: Any) -> None:
        self._routes.append(rule)

    def add_websocket_route(self, fn: WebSocketHandler, rule: str, **options: Any) -> None:
        self._websockets.append(rule)


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
harness.build()
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


def test_chained_invoke():
    server = Server()
    api = Blueprint("root")
    v = Blueprint("v")
    a = Blueprint("a")
    b = Blueprint("b")
    c = Blueprint("c")
    a.mount(b)
    v.mount(a)
    api.mount(v)
    api.mount(b)

    with pytest.raises(BlueprintAlreadyInvoked):
        jab.Harness().provide(server.jab, api.jab)

    api = Blueprint("root")
    v = Blueprint("v")

    a = Blueprint("a")
    b = Blueprint("b")
    c = Blueprint("c")

    x = Blueprint("x")
    y = Blueprint("y")
    z = Blueprint("z")

    b.mount(c)
    a.mount(b)
    v.mount(a)
    api.mount(v)

    y.mount(z)
    x.mount(y)
    c.mount(z)

    api.mount(x)

    with pytest.raises(BlueprintAlreadyInvoked):
        jab.Harness().provide(MockServer, api.jab)


root = Blueprint("api")

x = Blueprint("x")
y = Blueprint("y")
z = Blueprint("z")


@z.route("/alpha")
def alpha(req: Request) -> Response:
    return PlainTextResponse("alpha")


@y.route("/beta")
def beta(req: Request) -> Response:
    return PlainTextResponse("beta")


@x.route("/gamma")
def gamma(req: Request) -> Response:
    return PlainTextResponse("gamma")


y.mount(z)
x.mount(y)

root.mount(x)


def test_blueprint_mounting():

    harness = jab.Harness().provide(MockServer, root.jab)
    harness.build()
    server = harness.inspect(MockServer)
    expected_routes = ["/api/x/gamma", "/api/x/y/beta", "/api/x/y/z/alpha"]
    observed_routes = server.obj._routes
    assert sorted(expected_routes) == sorted(observed_routes)


def test_multi_invoke():
    away.mount(home)

    with pytest.raises(BlueprintAlreadyInvoked):
        jab.Harness().provide(app.jab, api.jab, away.jab, Database)
