from collections import namedtuple
from inspect import getmodule
from typing import Any, Callable, Dict, List, Type, get_type_hints

from sanic.request import Request
from sanic.response import HTTPResponse
from sanic.websocket import WebSocketProtocol

Handler = Callable[[Request], HTTPResponse]

HandlerPkg = namedtuple("HandlerPkg", ["fn", "rule", "options"])

WebSocketHandler = Callable[[Request, WebSocketProtocol], None]


# TODO (niels): Rename this
class UnboundMethodConstructor:
    def __init__(self) -> None:
        self._offset = 0
        self.deps: Dict[str, Type] = {}
        self.constructors: Dict[str, Type] = {}
        self.constructor_deps: Dict[str, Dict[str, str]] = {}
        self.constructor_routes: Dict[str, List[HandlerPkg]] = {}

    def update_offset(self, n: int) -> None:
        self._offset = n

    def add(self, fn: Callable, rule: str, **options: Any) -> None:
        mod = getmodule(fn)

        cls_name, fn_name = tuple(
            fn.__qualname__.split("<locals>", 1)[0].rsplit(".", 1)
        )

        class_ = getattr(mod, cls_name)

        if not self.constructors.get(cls_name):
            self.constructors[cls_name] = class_

        if not self.constructor_routes.get(cls_name):
            self.constructor_routes[cls_name] = []

        if not self.constructor_deps.get(cls_name):
            self.constructor_deps[cls_name] = {}

        self.constructor_routes[cls_name].append(HandlerPkg(fn_name, rule, options))

        for arg, type_ in get_type_hints(class_.__init__).items():
            if arg == "return":
                continue

            existing = next((k for k, v in self.deps.items() if v == type_), None)

            if existing:
                self.constructor_deps[cls_name][arg] = existing
                continue

            shadow_arg = f"arg{len(self.deps) + self._offset}"
            self.deps[shadow_arg] = type_
            self.constructor_deps[cls_name][arg] = shadow_arg
