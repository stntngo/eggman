from __future__ import annotations

import inspect
from collections import namedtuple
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, get_type_hints

from typing_extensions import Protocol

from eggman.types import Handler

HandlerPkg = namedtuple("HandlerPkg", ["fn", "rule", "options"])


class Router(Protocol):
    def add_route(self, fn: Handler, rule: str, **kwargs: Any) -> None:
        pass


class Blueprint:
    def __init__(
        self,
        name: str,
        url_prefix: Optional[str] = None,
        host: Optional[str] = None,
        version: Optional[str] = None,
        strict_slashes: bool = False,
    ) -> None:
        self.name = name
        self.url_prefix = url_prefix or "/{}".format(name)
        self.version = version
        self.host = host
        self.strict_slashes = strict_slashes

        self._jab = "eggman.Blueprint.{}".format(name)
        self._deferred: List[HandlerPkg] = []
        self._instances: Dict[str, Any] = {}

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

        def constructor(app: Router, **kwargs) -> Blueprint:  # type: ignore
            for name, cls_ in constructors.items():
                dep_map = class_deps[name]
                deps = {k: kwargs[v] for k, v in dep_map.items()}
                instance = cls_(**deps)

                self._instances[name] = instance

                # handle routes
                for fn_name, rule, options in class_routes[name]:
                    fn = getattr(instance, fn_name)

                    uri = self.url_prefix + rule if self.url_prefix else rule

                    app.add_route(fn, uri, **options)

                # handle middleware

            return self

        for fn, rule, options in self._deferred:
            mod = inspect.getmodule(fn)
            cls_name, fn_name = tuple(
                fn.__qualname__.split("<locals>", 1)[0].rsplit(".", 1)
            )
            class_ = getattr(mod, cls_name)

            if not constructors.get(cls_name):
                constructors[cls_name] = class_

            if not class_routes.get(cls_name):
                class_routes[cls_name] = []

            if not class_deps.get(cls_name):
                class_deps[cls_name] = {}

            class_routes[cls_name].append((fn_name, rule, options))

            for arg, type_ in get_type_hints(class_.__init__).items():
                if arg == "return":
                    continue

                existing = next(
                    (k for k, v in constructor_deps.items() if v == type_), None
                )

                if existing:
                    class_deps[cls_name][arg] = existing
                    continue

                pseudo_arg = "arg_{}".format(len(constructor_deps))

                constructor_deps[pseudo_arg] = type_
                class_deps[cls_name][arg] = pseudo_arg
                constructor.__annotations__[pseudo_arg] = type_

        return constructor
