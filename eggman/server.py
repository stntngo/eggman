from typing import Any, Callable

from sanic import Sanic
from sanic.websocket import WebSocketProtocol

from eggman.types import Handler, WebSocketHandler


class Server:
    """
    TODO (niels): Write docstring
    """

    def __init__(self) -> None:
        self._app = Sanic(__name__)

    def route(self, rule: str, **options: Any) -> Callable:
        def wrapper(fn: Handler) -> Handler:
            self.add_route(fn, rule, **options)
            return fn

        return wrapper

    def add_route(self, fn: Handler, rule: str, **options: Any) -> None:
        self._app.add_route(fn, rule, **options)

    def add_websocket_route(
        self, fn: WebSocketHandler, rule: str, **options: Any
    ) -> None:
        self._app.add_websocket_route(fn, rule, **options)

    async def run(self) -> None:
        server = await self._app.create_server(protocol=WebSocketProtocol)
        await server.wait_closed()

    @property
    def jab(self) -> Callable:
        def constructor() -> Server:
            return self

        return constructor
