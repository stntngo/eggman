from collections import namedtuple
from typing import Callable

from sanic.request import Request
from sanic.response import HTTPResponse

Handler = Callable[[Request], HTTPResponse]

HandlerPkg = namedtuple("HandlerPkg", ["fn", "rule", "options"])
