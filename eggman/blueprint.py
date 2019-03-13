from __future__ import annotations

import asyncio
import inspect
from collections import namedtuple
from typing import Any, Callable, Dict, List, Tuple, Type, get_type_hints

from sanic import Sanic
from sanic.request import Request
from sanic.response import HTTPResponse, text

Handler = Callable[[Request], HTTPResponse]
HandlerPkg = namedtuple("HandlerPkg", ["fn", "rule", "options"])


class Blueprint:
    def __init__(self, url_prefix: str) -> None:
        self._prefix = url_prefix
        self._deferred: List[HandlerPkg] = []

    def route(self, rule: str, **options: Any) -> Callable:
        def wrapper(fn: Handler) -> Handler:
            pkg = HandlerPkg(fn, rule, options)
            self._deferred.append(pkg)

            return fn

        return wrapper

    @property
    def jab(self) -> Callable:

        constructor_deps: Dict[str, Type] = {}
        constructors: Dict[str, Type] = {}
        class_deps: Dict[str, Dict[str, str]] = {}
        class_routes: Dict[str, List[Tuple]] = {}

        def constructor(sanic: Sanic, **kwargs) -> Blueprint:  # type: ignore
            for name, cls_ in constructors.items():
                dep_map = class_deps[name]
                deps = {k: kwargs[v] for k, v in dep_map.items()}
                instance = cls_(**deps)

                for fn_name, rule, options in class_routes[name]:
                    fn = getattr(instance, fn_name)
                    sanic.add_route(fn, self._prefix + rule, **options)

            return self

        for fn, rule, options in self._deferred:
            mod = inspect.getmodule(fn)
            cls_name, fn_name = tuple(
                fn.__qualname__.split("<locals>", 1)[0].rsplit(".", 1)
            )
            class_ = getattr(mod, cls_name)

            if not constructors.get(class_.__name__):
                constructors[class_.__name__] = class_

            if not class_routes.get(class_.__name__):
                class_routes[class_.__name__] = []

            if not class_deps.get(class_.__name__):
                class_deps[class_.__name__] = {}

            class_routes[class_.__name__].append((fn_name, rule, options))

            for arg, type_ in get_type_hints(class_.__init__).items():
                if arg == "return":
                    continue

                existing = next(
                    (k for k, v in constructor_deps.items() if v == type_), None
                )

                if existing:
                    class_deps[class_.__name__][arg] = existing
                    continue

                pseudo_arg = "arg_{}".format(len(constructor_deps))

                constructor_deps[pseudo_arg] = type_
                class_deps[class_.__name__][arg] = pseudo_arg
                constructor.__annotations__[pseudo_arg] = type_

        return constructor


test = Blueprint("/home")


class Test:
    def __init__(self, name: str, age: int) -> None:
        self.name = name
        self.age = age

    @test.route("/name", methods=["GET"])
    async def get_name(self, req: Request) -> HTTPResponse:
        await asyncio.sleep(0.5)
        return text(self.name)

    @test.route("/other", methods=["POST"])
    def put_other(self, req: Request) -> HTTPResponse:
        return text("other")

    @test.route("/age", methods=["GET"])
    def get_age(self, req: Request) -> HTTPResponse:
        return text(self.age)


app = Sanic(__name__)
test.jab(app, arg_0="niels", arg_1=27)
app.run()
