import starlette.requests as starlette_requests
import starlette.responses as starlette_responses
import starlette.websockets as starlette_websockets

Request = starlette_requests.Request
Response = starlette_responses.Response
WebSocket = starlette_websockets.WebSocket

HTMLResponse = starlette_responses.HTMLResponse
PlainTextResponse = starlette_responses.Response
JSONResponse = starlette_responses.JSONResponse
UJSONResponse = starlette_responses.UJSONResponse
RedirectResponse = starlette_responses.RedirectResponse
StreamingResponse = starlette_responses.StreamingResponse
FileResponse = starlette_responses.FileResponse
