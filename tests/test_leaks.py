from datetime import datetime
from pathlib import Path
import time
import pytest
from python_on_whales import DockerClient
from flaky import flaky
import pandas as pd
import matplotlib.pyplot as plt


####################################################
num_queries = 10_000
num_middleware = [0, 1, 2, 3, 4, 5, 6, 10]
test_matrix = [
    {
        "python": "3.12.1",
        "starlette": "0.34.0",
        "uvicorn": "0.25.0",
    },
    # {
    #     "python": "3.12.1",
    #     "starlette": "0.19.1",
    #     "uvicorn": "0.25.0",
    # },
    # {
    #     "python": "3.12.1",
    #     "starlette": "0.19.1",
    #     "uvicorn": "0.22.0",
    # },
    {
        "python": "3.7.17",
        "starlette": "0.19.1",
        "uvicorn": "0.22.0",
    },
]

####################################################

now = datetime.now()
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


def plot_and_save_csv_data(file_path, output_image_path, graph_title):
    """
    Reads data from a CSV file, creates a plot with the specified title,
    and saves the plot as an image.

    :param file_path: The path to the CSV file.
    :param output_image_path: The path where the plot image will be saved.
    :param graph_title: The title for the graph.
    """
    # Read the data from the CSV file
    data = pd.read_csv(file_path)

    # Create the plot
    plt.figure(figsize=(10, 6))
    plt.plot(data["Query count"], data["Max RSS"], marker="o")
    plt.title(graph_title)
    plt.xlabel("Query Count")
    plt.ylabel("Max RSS")
    plt.grid(True)

    # Save the plot to a file
    plt.savefig(output_image_path)
    plt.close()


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    pytest_html = item.config.pluginmanager.getplugin("html")
    outcome = yield
    report = outcome.get_result()
    extra = getattr(report, "extra", [])
    if report.when == "call":
        image_path = getattr(item, "rss_stats_image_path", None)
        if image_path:
            extra.append(pytest_html.extras.image(image_path))
        report.extra = extra


@flaky(max_runs=2)
@pytest.mark.parametrize(
    "num_middleware", num_middleware, ids=lambda x: f"middlewares-{x:02}"
)
@pytest.mark.parametrize("versions", test_matrix, ids=str)
def test_leak(request, versions, num_middleware):
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

    unique_dir = (
        Path(__file__).parent
        / f"../test_results/{now:%Y-%m-%dT%H%M%S}/s{starlette_version}_p{python_version}_u{uvicorn_version}_middleware-{num_middleware:02}"
    )
    unique_dir.mkdir(parents=True, exist_ok=True)

    container = docker.container.create(
        image=image,
        command=[str(num_middleware), str(num_queries)],
        volumes=[(str(unique_dir), "/stats")],
        labels={
            "num_middlewares": num_middleware,
            "test-leak": "true",
        },
    )
    print(f"starting container {container}, with {num_middleware} middlewares")
    container.start(attach=True)

    time.sleep(2)
    (unique_dir / "docker.log").write_text(container.logs(timestamps=True))

    plot_and_save_csv_data(
        file_path=str(unique_dir / "stats.csv"),
        output_image_path=str(unique_dir / "rss-stats.png"),
        graph_title=f"Starlette {starlette_version}, {num_middleware} middlewares, Python {python_version}, Uvicorn {uvicorn_version}",
    )
    request.node.rss_stats_image_path = str(unique_dir / "rss-stats.png")
