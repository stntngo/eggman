from typing import Any, Callable

from sanic import Sanic

from eggman.types import Handler


class Server:
    def __init__(self) -> None:
        self._app = Sanic(__name__)

    def add_route(self, fn: Handler, rule: str, **kwargs: Any) -> None:
        self._app.add_route(fn, rule, **kwargs)

    async def run(self) -> None:
        server = await self._app.create_server()
        await server.wait_closed()

    @property
    def jab(self) -> Callable:
        def constructor() -> Server:
            return self

        return constructor
