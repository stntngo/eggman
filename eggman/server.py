from typing import Any, Callable

from jab import Receive, Send
from starlette.applications import Starlette

from eggman.types import Handler, WebSocketHandler


class Server:
    """
    TODO (niels): Write docstring
    """

    def __init__(self) -> None:
        self._app = Starlette(__name__)

    def add_route(self, fn: Handler, rule: str, **options: Any) -> None:
        self._app.add_route(rule, fn, **options)

    def add_websocket_route(
        self, fn: WebSocketHandler, rule: str, **options: Any
    ) -> None:
        self._app.add_websocket_route(rule, fn, **options)

    async def asgi(self, scope: dict, receive: Receive, send: Send) -> None:
        await self._app(scope, receive, send)

    @property
    def jab(self) -> Callable:
        def constructor() -> Server:
            return self

        return constructor
