# eggman

eggman exposes a `sanic` server in such a way that makes it easy to use within the [jab](https://github.com/stntngo/jab) framework.

## Examples

```python
import jab
import eggman

from sanic.request import Request
from sanic.response import HTTPResponse, text


app = eggman.Server()


@app.route("/hello")
def hello_world(req: Request) -> HTTPResponse:
    return text("Hello, world!")


jab.Harness().provide(app.jab).run()
```

```python
import jab
import eggman

import asyncpg
from sanic.request import Request
from sanic.response import HTTPResponse, json
from typing_extensions import Protocol
from dataclasses import dataclass


app = eggman.Server()


class UserGetter(Protocol):
    async def get_user(self, user_name: str) -> dict:


class UserHandler:

    def __init__(self, db: UserGetter) -> None:
        self.db = db

    @app.route("/<name>")
    async def get_user(self, req: Request, name: str) -> HTTPResponse:
        data = await self.db.get_user(name)
        return json(data)


class Database:
    def __init__(self, config: Config) -> None:
        self.config = config
        self.connection = None

    async def on_start(self) -> None:
        self.connection = await asyncpg.create_pool(config.dsn)

    async def get_user(self, name: str) -> dict:
        data = await self.connection.fetch("SELECT * FROM users WHERE user_name = $1", name)
        return dict(data)


@dataclass
class Config:
    dsn: str

    @property
    def jab(self) -> Callable:
        def inner() -> Config:
            return self
        return inner


cfg = Config(dsn="localhost")

jab.Harness().provide(app.jab, Database, cfg.jab).run()
```