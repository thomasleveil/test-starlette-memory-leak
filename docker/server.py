import json
from pathlib import Path
import resource
import sys
import objgraph
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.routing import Route
from starlette.middleware.base import (
    BaseHTTPMiddleware,
    RequestResponseEndpoint,
)
from starlette.requests import Request
from starlette.responses import PlainTextResponse, JSONResponse, FileResponse

stats_dir = Path("/stats")
stats_dir.mkdir(parents=True, exist_ok=True)
stats_file = stats_dir / "stats.csv"


def on_startup():
    with stats_file.open("w") as f:
        f.write("Query count,Max RSS\n")
        f.write(f"0,{resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}\n")
    stats_file.chmod(0o777)


# Default value for middleware count
MIDDLEWARE_COUNT = 1

ping_count = 0


# Check if an argument is provided
if len(sys.argv) > 1:
    try:
        MIDDLEWARE_COUNT = int(sys.argv[1])
    except ValueError:
        print("Please provide a valid integer for middleware count")
        sys.exit(1)

print("Middlewares to setup: " + str(MIDDLEWARE_COUNT))


class TestMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, req: Request, call_next: RequestResponseEndpoint):
        a_tuple = tuple("a" * 1000 for _ in range(1000))
        return await call_next(req)


async def ping(request):
    global ping_count
    ping_count += 1
    if ping_count % 500 == 0:
        with stats_file.open("a") as f:
            f.write(
                f"{ping_count},{resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}\n"
            )

    a_list = ["a" * 1000 for _ in range(1000)]
    return PlainTextResponse("pong")


def garbage_collect(request):
    import gc

    gc.collect()
    return PlainTextResponse(str(gc.garbage))


async def objgraph_stats(request):
    most_common_types = objgraph.most_common_types()
    data = {"objgraph_stats": most_common_types}
    objgraph_file = stats_dir / "objgraph.json"
    objgraph_file.write_text(json.dumps(data))
    objgraph_file.chmod(0o777)
    return JSONResponse(data)


app = Starlette(
    routes=[
        Route("/_ping", endpoint=ping),
        Route("/garbage_collect", endpoint=garbage_collect),
        Route("/objgraph-stats", endpoint=objgraph_stats),
    ],
    middleware=[Middleware(TestMiddleware)] * MIDDLEWARE_COUNT,
    on_startup=[on_startup],
)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=14000)
