import sanic

bp = sanic.Blueprint("user", url_prefix="/user")
print(bp.url_prefix)


class Test:
    def __init__(self, name: str) -> None:
        self.n = name

    def name(self, request: sanic.request.Request) -> sanic.response.HTTPResponse:
        return sanic.response.json({"name": self.n})

    def on_start(self, bp):
        bp.add_route(self.name, "/name")


Test("niels").on_start(bp)


@bp.route("/test")
def name(request):
    return sanic.response.json({"name": "test"})


app = sanic.Sanic()
app.blueprint(bp)

app.run()
