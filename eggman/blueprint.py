from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from typing_extensions import Protocol

from eggman.types import (
    BlueprintAlreadyInvoked,
    Handler,
    HandlerPkg,
    UnboundMethodConstructor,
    WebSocketHandler,
)


class Router(Protocol):
    def add_route(self, fn: Handler, rule: str, **options: Any) -> None:
        pass  # pragma: no cover

    def add_websocket_route(self, fn: WebSocketHandler, rule: str, **options: Any) -> None:
        pass  # pragma: no cover


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
        self.tombstone: bool = False
        self.caller: Optional[str] = None
        self.deferred_routes: List[HandlerPkg] = []
        self.deferred_websocket: List[HandlerPkg] = []
        self._instances: Dict[str, Any] = {}
        self._mounted_blueprints: List[Blueprint] = []

    def mount(self, bp: Blueprint) -> None:
        self._mounted_blueprints.append(bp)

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

    def move_routes(self, caller: str) -> List[HandlerPkg]:
        """
        `move_routes` transfers ownership of all of this Blueprint's routes
        as well as ownership of all of the routes inside of mounted Blueprints
        to the caller of the method.

        `move_routes` is invoked during the `jab` provide phase to gather all
        the nested routes under a particular blueprint when the root blueprint
        is provided to a jab harness.

        Once a caller has invoked `move_routes` the blueprint on which `move_routes`
        was invoked cannot be used again. It cannot have `move_routes` called on it
        by some second caller and it cannot be directly provided to a jab harness.
        """
        if self.tombstone:
            self_caller = self.caller or "UNKNOWN"
            raise BlueprintAlreadyInvoked(caller, self.name, self_caller)

        routes = self.deferred_routes

        for bp in self._mounted_blueprints:
            if bp.tombstone:
                mount_caller = bp.caller or "UNKNOWN"
                raise BlueprintAlreadyInvoked(f"{caller} => {self.name}", bp.name, mount_caller)

            prefix = bp.url_prefix
            for route in bp.move_routes(f"{caller} => {self.name}"):
                rule = prefix + route.rule
                routes.append(HandlerPkg(route.fn, rule, route.options))

        self.tombstone = True
        self.caller = caller

        return routes

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
        [1] The formal distinction between these two has been eroded in recent versions of Python so we're
            forced to do some hacky name string parsing in order to figure out which is which. Ideally we
            can find a solution that does not involve name string parsing.
        """

        for bp in self._mounted_blueprints:
            prefix = bp.url_prefix
            for pkg in bp.move_routes(self.name):
                rule = prefix + pkg.rule
                self.deferred_routes.append(HandlerPkg(pkg.fn, rule, pkg.options))

        unbound_routes = UnboundMethodConstructor()
        unbound_ws = UnboundMethodConstructor()
        func_routes: List[HandlerPkg] = []
        func_ws: List[HandlerPkg] = []

        def constructor(app: Router, **kwargs) -> Blueprint:
            """
            `constructor` is a functional jab provider with the dependencies of the wrapped
            uninstantiated classes of the blueprint raised to the level of the blueprint.
            """
            if self.tombstone:
                caller = self.caller or "UNKNOWN"
                raise BlueprintAlreadyInvoked("jab", self.name, caller)

            for name, cls_ in unbound_routes.constructors.items():
                dep_map = unbound_routes.constructor_deps[name]
                deps = {k: kwargs[v] for k, v in dep_map.items()}
                instance = cls_(**deps)

                self._instances[name] = instance

                for fn_name, rule, options in unbound_routes.constructor_routes[name]:
                    fn = getattr(instance, fn_name)

                    uri = self.url_prefix + rule if self.url_prefix else rule

                    app.add_route(fn, uri, **options)

            for fn, rule, options in func_routes:
                uri = self.url_prefix + rule if self.url_prefix else rule

                app.add_route(fn, uri, **options)

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

            self.tombstone = True
            self.caller = "jab"

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
