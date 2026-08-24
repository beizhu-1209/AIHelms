import asyncio
import os

os.environ.setdefault("SECRET_KEY", "secret")
os.environ.setdefault(
    "DSH_RUNTIME_IMAGE",
    "registry.cn-zhangjiakou.aliyuncs.com/microbaton/dsh:v0.1.0-rc.8",
)

import manager as manager_module
from manager import InstanceManager, ManagerSettings


class FakeResponse:
    def __init__(self, payload: object, status_code: int = 200) -> None:
        self.payload = payload
        self.status_code = status_code

    def json(self) -> object:
        return self.payload

    def raise_for_status(self) -> None:
        return None


class FakeDocker:
    def __init__(self) -> None:
        self.containers: list[dict[str, object]] = []
        self.create_count = 0
        self.create_payload: dict[str, object] | None = None

    async def request(self, method: str, path: str, **kwargs: object) -> FakeResponse:
        if method == "GET" and path == "/containers/json":
            filters = str(kwargs.get("params", {}).get("filters", ""))
            if "aihelms.dsh.user_id=7" in filters:
                return FakeResponse(self.containers[:1])
            return FakeResponse(self.containers)
        if method == "POST" and path == "/volumes/create":
            return FakeResponse({"Name": "dsh-data-user-7"})
        if method == "POST" and path == "/containers/create":
            self.create_count += 1
            self.create_payload = kwargs["json"]
            self.containers.append({"Id": "container-7", "State": "created"})
            return FakeResponse({"Id": "container-7"})
        if method == "POST" and path == "/containers/container-7/start":
            self.containers[0]["State"] = "running"
            return FakeResponse({})
        if method == "GET" and path == "/containers/container-7/json":
            return FakeResponse({"State": {"Running": True}})
        raise AssertionError(f"unexpected Docker call: {method} {path}")


class FakeHttpClient:
    def __init__(self, **_: object) -> None:
        pass

    async def __aenter__(self) -> "FakeHttpClient":
        return self

    async def __aexit__(self, *_: object) -> None:
        return None

    async def get(self, _: str) -> FakeResponse:
        return FakeResponse({}, status_code=200)


def test_ensure_same_user_creates_one_container(monkeypatch) -> None:
    monkeypatch.setattr(manager_module.httpx, "AsyncClient", FakeHttpClient)
    settings = ManagerSettings(
        enabled=True,
        secret_key="secret",
        runtime_image="registry.cn-zhangjiakou.aliyuncs.com/microbaton/dsh:v0.1.0-rc.8",
        user_network="dsh-user",
        idle_timeout_seconds=1800,
        reclaim_grace_seconds=60,
        start_timeout_seconds=1,
        max_count=20,
    )
    docker = FakeDocker()
    manager = InstanceManager(settings, docker)

    async def run() -> tuple[str, str]:
        return await asyncio.gather(manager.ensure("7"), manager.ensure("7"))

    first, second = asyncio.run(run())

    assert first == second == "container-7"
    assert docker.create_count == 1

    assert docker.create_payload is not None
    assert docker.create_payload["Image"] == (
        "registry.cn-zhangjiakou.aliyuncs.com/microbaton/dsh:v0.1.0-rc.8"
    )
    host_config = docker.create_payload["HostConfig"]
    assert host_config["Binds"] == ["dsh-data-user-7:/workspace"]
    assert host_config["NetworkMode"] == "dsh-user"
    assert host_config["User"] == "1000:1000"
    assert host_config["CapDrop"] == ["ALL"]
    assert host_config["Memory"] == 1073741824
    assert host_config["NanoCpus"] == 1000000000
    assert host_config["PidsLimit"] == 256
    assert host_config.get("Privileged", False) is False
    assert "/var/run/docker.sock" not in str(host_config["Binds"])
