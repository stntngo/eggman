from __future__ import annotations

import inspect
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, get_type_hints

from typing_extensions import Protocol

from eggman.types import Handler, HandlerPkg, UnboundMethodConstructor, WebSocketHandler


class Router(Protocol):
    def add_route(self, fn: Handler, rule: str, **options: Any) -> None:
        pass
    
    def add_websocket_route(self, fn: WebSocketHandler, rule: str, **options: Any) -> None:
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
        self.url_prefix = url_prefix or f"/{name}"
        self.version = version
        self.host = host
        self.strict_slashes = strict_slashes

        self._jab = f"eggman.Blueprint.{name}"
        self.deferred_routes: List[HandlerPkg] = []
        self.deferred_websocket: List[HandlerPkg] = []
        self._instances: Dict[str, Any] = {}

    def route(self, rule: str, **options: Any) -> Callable:
        def wrapper(fn: Handler) -> Handler:
            pkg = HandlerPkg(fn, rule, options)
            self.deferred_routes.append(pkg)
            return fn

        return wrapper
    
    def websocket(self, rule: str, **options: Any) -> Callable:
        def wrapper(fn: WebSocketHandler) -> WebSocketHandler:
            pkg = HandlerPkg(fn, rule, options)
            self.deferred_websocket.append(pkg)
            return fn
        
        return wrapper

    @property
    def jab(self) -> Callable:
        unbound_routes = UnboundMethodConstructor()
        unbound_ws = UnboundMethodConstructor()
        func_routes: List[HandlerPkg] = []
        func_ws: List[HandlerPkg] = []

        def constructor(app: Router, **kwargs) -> Blueprint:  # type: ignore
            # handle unbound routes
            for name, cls_ in unbound_routes.constructors.items():
                dep_map = unbound_routes.constructor_deps[name]
                deps = {k: kwargs[v] for k, v in dep_map.items()}
                instance = cls_(**deps)

                self._instances[name] = instance

                # handle routes
                for fn_name, rule, options in unbound_routes.constructor_routes[name]:
                    fn = getattr(instance, fn_name)

                    uri = self.url_prefix + rule if self.url_prefix else rule

                    app.add_route(fn, uri, **options)

            # handle function routes
            for fn, rule, options in func_routes:
                uri = self.url_prefix + rule if self.url_prefix else rule

                app.add_route(fn, uri, **options)

            # handle websockets
            for name, cls_ in unbound_ws.constructors.items():
                instance = self._instances.get(name)
                if not isinstance(instance, cls_):
                    dep_map = unbound_ws.constructor_deps[name]
                    deps = {k: kwargs[v] for k, v in dep_map.items()}
                    instance = cls_(**deps)
                    self._instances[name] = instance

                for fn_name, rule, options in unbound_ws.constructor_routes[name]:
                    fn = getattr(instance, fn_name)
                    
                    uri = self.url_prefix + rule if self.url_prefix else rule

                    app.add_websocket_route(fn, uri, **options)

            for fn, rule, options in func_ws:
                uri = self.url_prefix + rule if self.url_prefix else rule

                app.add_websocket_route(fn, uri, **options)

            # handle middleware

            return self

        for fn, rule, options in self.deferred_routes:
            # HACK: Right now when parsing a deferred function handler we try to split its
            # qualified name into a class name and a method name. If we're unable to do so
            # then we assume that this function does not belong to a class and we append it
            # to the list of raw functions with the understanding that it does not need to
            # have a class instance in order for the function to be called.
            try:
                unbound_routes.add(fn, rule, **options)
            except ValueError:
                func_routes.append(HandlerPkg(fn, rule, options))

        for fn, rule, options in self.deferred_websocket:
            unbound_ws.update_offset(len(unbound_routes.deps))

            try:
                unbound_ws.add(fn, rule, **options)
            except ValueError:
                func_ws.append(HandlerPkg(fn, rule, options))

        for arg, type_ in unbound_routes.deps.items():
            constructor.__annotations__[arg] = type_

        for arg, type_ in unbound_ws.deps.items():
            constructor.__annotations__[arg] = type_

        return constructor
