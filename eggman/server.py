from typing import Any, Callable

from jab import Receive, Send
from starlette.applications import Starlette

from eggman.types import Handler, WebSocketHandler


class Server:
    """
    `Server` is a thin wrapper around a Starlette application. Rather than have the Server inherit
    the Starlette application class we choose to forward specific methods. This gives us greater control
    over the sufrace area of the application when used with the jab harness as well as leaves open
    the option to break away from using the Starlette application itself and instead begin to use the
    starlette toolkit.
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
        """
        Exposes the ASGI interface of the Starlette application to be used with your favorite ASGI server.
        """
        await self._app(scope, receive, send)  # pragma: no cover

    @property
    def starlette(self) -> Starlette:
        """
        Provides access to the underlying Starlette application.
        Useful in conjunction with `starlette.TestClient`.
        """
        return self._app

    @property
    def jab(self) -> Callable:
        """
        Provides a jab constructor to incorporate an already instantiated Server object.
        """

        def constructor() -> Server:
            return self

        return constructor
