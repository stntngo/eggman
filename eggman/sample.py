import inspect
from typing import Callable

import jab


class SampleClass:
    def __init__(self) -> None:
        self.thing = {}

    def decorator(self, name: str) -> Callable:
        def outer(f: Callable) -> Callable:
            print(inspect.getmodule(f))

            self.thing[f.__name__] = {"func": f, "name": name}

            return f

        return outer

    def on_start(self, harness: jab.Harness) -> None:
        for fn in self.thing.values():
            func = fn["func"]
            mod = inspect.getmodule(func)
            cls_name, fn_name = tuple(
                func.__qualname__.split(".<locals>", 1)[0].rsplit(".", 1)
            )
            class_ = getattr(mod, cls_name)
            instance = class_(fn["name"])
            print(class_, fn_name)
            print(instance, getattr(instance, fn_name), getattr(instance, fn_name)())


s = SampleClass()


class Cls:
    def __init__(self, name):
        self.name = name

    @s.decorator("other")
    def get_name(self):
        return self.name


s.on_start(None)
