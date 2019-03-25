from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from typing_extensions import Protocol

from eggman.types import Handler, HandlerPkg, UnboundMethodConstructor, WebSocketHandler


class Router(Protocol):
    def add_route(self, fn: Handler, rule: str, **options: Any) -> None:
        pass

    def add_websocket_route(
        self, fn: WebSocketHandler, rule: str, **options: Any
    ) -> None:
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
        """
        `Blueprint` is an object that records handler functions that will be registered to
        and served by a Server object later.
        """

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
        """
        TODO (niels): Write docstirng
        """

        def wrapper(fn: Handler) -> Handler:
            pkg = HandlerPkg(fn, rule, options)
            self.deferred_routes.append(pkg)
            return fn

        return wrapper

    def websocket(self, rule: str, **options: Any) -> Callable:
        """
        TODO (niels): Write docstring
        """

        def wrapper(fn: WebSocketHandler) -> WebSocketHandler:
            pkg = HandlerPkg(fn, rule, options)
            self.deferred_websocket.append(pkg)
            return fn

        return wrapper

    @property
    def jab(self) -> Callable:
        """
        `jab` provides the blueprint to the jab harness by creating a constructor function
        that depends on the dependencies of the uninstantiated classes whose methods have been
        wrapped in `route` and `websocket` decorators, hoisting the dependencies of the classes
        to the level of the jab harness itself.

        `jab` accomplishes this by first breaking down all wrapped handlers into either unbound methods
        or regular functions[1]. As the wrapped methods are from uninstantiated classes with their own
        dependencies, `jab` creates a mapping of a class's dependencies to a shadowed list of dependencies
        used to define the constructor function. When the constructor function is called from inside the jab
        harness and all the shadowed dependencies are provided to it, the constructor maps the shadowed
        dependency names back to each class's dependency and creates an instance of that class using the
        dependencies satisfied by the jab harness.

        As the classes are instantiated and their unbound methods turned into bound methods with their
        dependencies satisfied, the handlers are added to a `Router`. In practice this `Router` is an
        `eggman.Server` instance.

        Notes
        -----
        [1] The formal distinction between these two has been eroded in recent versions of Python so we're forced
            to do some hacky name string parsing in order to figure out which is which. Ideally we can find
            a solution that does not involve name string parsing.
        """
        unbound_routes = UnboundMethodConstructor()
        unbound_ws = UnboundMethodConstructor()
        func_routes: List[HandlerPkg] = []
        func_ws: List[HandlerPkg] = []

        def constructor(app: Router, **kwargs) -> Blueprint:  # type: ignore
            """
            `constructor` creates a functional jab provider with the dependencies of the wrapped
            uninstantiated classes of the blueprint.
            """
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

        unbound_ws.update_offset(len(unbound_routes.deps))
        for fn, rule, options in self.deferred_websocket:

            try:
                unbound_ws.add(fn, rule, **options)
            except ValueError:
                func_ws.append(HandlerPkg(fn, rule, options))

        for arg, type_ in unbound_routes.deps.items():
            constructor.__annotations__[arg] = type_

        for arg, type_ in unbound_ws.deps.items():
            constructor.__annotations__[arg] = type_

        return constructor
