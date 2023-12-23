from pathlib import Path
import time
import pytest
from python_on_whales import DockerClient
from flaky import flaky


####################################################
num_queries = 5_000
max_memory_threshold = 35_000
num_middleware = [0, 1, 3, 6, 9]
test_matrix = [
    {
        "python": "3.13.0a2",
        "starlette": "0.34.0",
        "uvicorn": "0.25.0",
    },
    {
        "python": "3.12.1",
        "starlette": "0.34.0",
        "uvicorn": "0.25.0",
    },
    {
        "python": "3.12.1",
        "starlette": "0.19.1",
        "uvicorn": "0.25.0",
    },
    {
        "python": "3.7.17",
        "starlette": "0.19.1",
        "uvicorn": "0.22.0",
    },
]

####################################################


dockerfile = Path(__file__).parent / "../docker/Dockerfile"
docker = DockerClient()


def build_image(context_path, python_version, starlette_version, uvicorn_version):
    return docker.buildx.build(
        context_path=context_path,
        build_args={
            "PYTHON_VERSION": python_version,
            "STARLETTE_VERSION": starlette_version,
            "UVICORN_VERSION": uvicorn_version,
        },
        cache=True,
        progress="plain",
        load=True,
        tags=["test-leak:p" + python_version + "-s" + starlette_version],
    )


def find_memory_from_logs(container) -> tuple[str, str]:
    logs = container.logs(tail=30)

    server_log_line = None
    for line in logs.splitlines():
        if "python server.py" in line:
            print(line)
            server_log_line = line
    return logs, server_log_line


@flaky(max_runs=2)
@pytest.mark.parametrize(
    "num_middleware", num_middleware, ids=lambda x: f"middlewares-{x}"
)
@pytest.mark.parametrize("versions", test_matrix, ids=str)
def test_leak(versions, num_middleware):
    python_version = versions["python"]
    starlette_version = versions["starlette"]
    uvicorn_version = versions["uvicorn"]
    print(
        f"building image for Python {python_version} and Starlette {starlette_version}"
    )
    image = build_image(
        dockerfile.parent,
        python_version=python_version,
        starlette_version=starlette_version,
        uvicorn_version=uvicorn_version,
    )
    assert image is not None, "Failed to build docker image"

    container = docker.container.create(
        image=image,
        command=[str(num_middleware), str(num_queries)],
        labels={
            "num_middlewares": num_middleware,
            "test-leak": "true",
        },
    )
    print(f"starting container {container}, with {num_middleware} middlewares")
    container.start(attach=True)

    logs, server_log_line = find_memory_from_logs(container)
    if not server_log_line:
        time.sleep(2)
        logs, server_log_line = find_memory_from_logs(container)

    print(logs)
    if not server_log_line:
        raise ValueError("`ps aux` output not found in the container log")

    final_memory = int(server_log_line.split()[5])
    assert final_memory <= max_memory_threshold, server_log_line
