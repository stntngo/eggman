import uvicorn
import os
from typing import Any, Callable, Optional

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

    def __init__(self, host: Optional[str] = None, port: Optional[int] = None) -> None:
        self._app = Starlette(__name__)
        self._host = host
        self._port = port

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

    async def run(self) -> None:
        """
        Runs the app inside of uvicorn inside of the jab harness.

        NOTE
        ----
        Despite the async definition this function immediately blocks. It's an ugly
        vestige of when jab did not support an ASGI interface itself and the jab ASGI interface should
        always be used instead of it.
        """
        uvicorn.run(self._app, host=self._host or "0.0.0.0", port=self._port or 8000)

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
