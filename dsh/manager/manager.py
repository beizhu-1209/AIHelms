import asyncio
import os
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass

import httpx
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import Response, StreamingResponse
from jose import JWTError, jwt
from websockets.asyncio.client import connect as websocket_connect

JWT_ALGORITHM = "HS256"
DOCKER_API_VERSION = "v1.43"
CONTAINER_PORT = 3080


@dataclass(frozen=True)
class ManagerSettings:
    enabled: bool
    secret_key: str
    runtime_image: str
    user_network: str
    idle_timeout_seconds: int
    reclaim_grace_seconds: int
    start_timeout_seconds: int
    max_count: int
    nginx_server_name: str = "localhost"

    @classmethod
    def from_env(cls) -> "ManagerSettings":
        return cls(
            enabled=os.getenv("DSH_ENABLED", "false").lower() == "true",
            secret_key=os.environ["SECRET_KEY"],
            runtime_image=os.environ["DSH_RUNTIME_IMAGE"],
            user_network=os.getenv("DSH_USER_NETWORK", "external"),
            idle_timeout_seconds=int(os.getenv("DSH_CONTAINER_IDLE_TIMEOUT_SECONDS", "1800")),
            reclaim_grace_seconds=int(os.getenv("DSH_CONTAINER_RECLAIM_GRACE_SECONDS", "60")),
            start_timeout_seconds=int(os.getenv("DSH_CONTAINER_START_TIMEOUT_SECONDS", "30")),
            max_count=int(os.getenv("DSH_CONTAINER_MAX_COUNT", "20")),
            nginx_server_name=os.getenv("NGINX_SERVER_NAME", "localhost"),
        )


class DockerEngine:
    def __init__(self) -> None:
        transport = httpx.AsyncHTTPTransport(uds="/var/run/docker.sock")
        self.client = httpx.AsyncClient(transport=transport, base_url="http://docker")

    async def close(self) -> None:
        await self.client.aclose()

    async def request(self, method: str, path: str, **kwargs: object) -> httpx.Response:
        response = await self.client.request(method, f"/{DOCKER_API_VERSION}{path}", **kwargs)
        response.raise_for_status()
        return response


class InstanceManager:
    def __init__(self, settings: ManagerSettings, docker: DockerEngine) -> None:
        self.settings = settings
        self.docker = docker
        self.locks: dict[str, asyncio.Lock] = {}
        self.last_activity: dict[str, float] = {}
        self.active_requests: dict[str, int] = {}

    def _lock_for(self, user_id: str) -> asyncio.Lock:
        if user_id not in self.locks:
            self.locks[user_id] = asyncio.Lock()
        return self.locks[user_id]

    @staticmethod
    def _name(user_id: str) -> str:
        return f"dsh-user-{user_id}"

    @staticmethod
    def _volume(user_id: str) -> str:
        return f"dsh-data-user-{user_id}"

    def touch(self, user_id: str) -> None:
        self.last_activity[user_id] = time.monotonic()

    async def _find_container(self, user_id: str) -> dict | None:
        response = await self.docker.request(
            "GET",
            "/containers/json",
            params={"all": "true", "filters": f'{{"label":["aihelms.dsh.user_id={user_id}"]}}'},
        )
        containers = response.json()
        return containers[0] if containers else None

    async def _running_count(self) -> int:
        response = await self.docker.request(
            "GET",
            "/containers/json",
            params={"all": "false", "filters": '{"label":["aihelms.dsh.user_id"]}'},
        )
        return len(response.json())

    async def _create_container(self, user_id: str) -> str:
        if await self._running_count() >= self.settings.max_count:
            raise RuntimeError("DSH 容器数量已达到上限")
        volume = self._volume(user_id)
        await self.docker.request(
            "POST",
            "/volumes/create",
            json={"Name": volume, "Labels": {"aihelms.dsh.user_id": user_id}},
        )
        response = await self.docker.request(
            "POST",
            "/containers/create",
            params={"name": self._name(user_id)},
            json={
                "Image": self.settings.runtime_image,
                "Labels": {
                    "aihelms.dsh.user_id": user_id,
                    "aihelms.dsh.volume": volume,
                },
                "Env": [
                    "DSH_SANDBOX_MODE=workspace-write",
                    f"NGINX_SERVER_NAME={self.settings.nginx_server_name}",
                ],
                "ExposedPorts": {f"{CONTAINER_PORT}/tcp": {}},
                "HostConfig": {
                    "Binds": [f"{volume}:/workspace"],
                    "NetworkMode": self.settings.user_network,
                    "User": "1000:1000",
                    "AutoRemove": False,
                    "CapDrop": ["ALL"],
                    "ReadonlyRootfs": False,
                    "Memory": 1073741824,
                    "NanoCpus": 1000000000,
                    "PidsLimit": 256,
                },
            },
        )
        container_id = response.json()["Id"]
        try:
            await self.docker.request("POST", f"/containers/{container_id}/start")
        except Exception:
            await self.docker.request("DELETE", f"/containers/{container_id}", params={"force": "true"})
            raise
        return container_id

    async def ensure(self, user_id: str) -> str:
        async with self._lock_for(user_id):
            container = await self._find_container(user_id)
            container_id = container["Id"] if container else await self._create_container(user_id)
            if container and container["State"] != "running":
                await self.docker.request("POST", f"/containers/{container_id}/start")
            await self._wait_ready(container_id, user_id)
            self.touch(user_id)
            return container_id

    async def _wait_ready(self, container_id: str, user_id: str) -> None:
        deadline = time.monotonic() + self.settings.start_timeout_seconds
        async with httpx.AsyncClient(timeout=1.0) as client:
            while time.monotonic() < deadline:
                response = await self.docker.request("GET", f"/containers/{container_id}/json")
                state = response.json().get("State", {})
                if state.get("Running"):
                    try:
                        ready = await client.get(f"http://{self._name(user_id)}:{CONTAINER_PORT}/")
                    except httpx.HTTPError:
                        ready = None
                    if ready is not None and 200 <= ready.status_code < 400:
                        return
                await asyncio.sleep(0.25)
        raise TimeoutError("DSH 容器启动超时")

    async def reclaim_idle(self) -> None:
        now = time.monotonic()
        for user_id, last_activity in list(self.last_activity.items()):
            if self.active_requests.get(user_id, 0) or now - last_activity < self.settings.idle_timeout_seconds:
                continue
            async with self._lock_for(user_id):
                if self.active_requests.get(user_id, 0):
                    continue
                container = await self._find_container(user_id)
                if container:
                    await self.docker.request("POST", f"/containers/{container['Id']}/stop", params={"t": self.settings.reclaim_grace_seconds})
                    await self.docker.request("DELETE", f"/containers/{container['Id']}")
                self.last_activity.pop(user_id, None)


def _user_id_from_cookie(cookie: str | None, settings: ManagerSettings) -> str:
    if not cookie:
        raise PermissionError("缺少 DS Harness 会话")
    try:
        payload = jwt.decode(cookie, settings.secret_key, algorithms=[JWT_ALGORITHM])
    except JWTError as exc:
        raise PermissionError("DS Harness 会话无效") from exc
    user_id = payload.get("sub")
    if not payload.get("dsh_session") or not user_id:
        raise PermissionError("当前用户没有 DS Harness 访问权限")
    return str(user_id)


async def _proxy_request(
    request: Request,
    target: str,
    on_close: Callable[[], Awaitable[None]],
) -> Response | StreamingResponse:
    client = httpx.AsyncClient(timeout=None)
    headers = dict(request.headers)
    upstream_host = request.headers.get("x-forwarded-host") or request.headers.get("host")
    headers.pop("host", None)
    if upstream_host:
        headers["host"] = upstream_host
    body = await request.body()
    upstream_request = client.build_request(request.method, target, headers=headers, content=body)
    upstream = await client.send(upstream_request, stream=True)

    async def content() -> AsyncIterator[bytes]:
        try:
            async for chunk in upstream.aiter_bytes():
                yield chunk
        finally:
            await upstream.aclose()
            await client.aclose()
            await on_close()

    response_headers = {key: value for key, value in upstream.headers.items() if key.lower() not in {"content-length", "transfer-encoding", "connection"}}
    return StreamingResponse(content(), status_code=upstream.status_code, headers=response_headers)


def create_app() -> FastAPI:
    settings = ManagerSettings.from_env()
    docker = DockerEngine()
    manager = InstanceManager(settings, docker)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        async def reaper() -> None:
            while True:
                await asyncio.sleep(30)
                if settings.enabled:
                    await manager.reclaim_idle()

        task = asyncio.create_task(reaper())
        yield
        task.cancel()
        await docker.close()

    app = FastAPI(title="DSH Instance Manager", lifespan=lifespan)

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
    async def proxy(path: str, request: Request) -> Response:
        if not settings.enabled:
            return Response(status_code=404)
        try:
            user_id = _user_id_from_cookie(request.cookies.get("dsh_session"), settings)
            await manager.ensure(user_id)
        except PermissionError as exc:
            return Response(str(exc), status_code=403)
        except Exception as exc:
            return Response(str(exc), status_code=503)
        manager.active_requests[user_id] = manager.active_requests.get(user_id, 0) + 1
        manager.touch(user_id)
        try:
            return await _proxy_request(
                request,
                f"http://{manager._name(user_id)}:{CONTAINER_PORT}/{path}",
                lambda: _release_request(manager, user_id),
            )
        except Exception:
            await _release_request(manager, user_id)
            raise

    @app.websocket("/{path:path}")
    async def websocket_proxy(websocket: WebSocket, path: str) -> None:
        if not settings.enabled:
            await websocket.close(code=1013)
            return
        try:
            user_id = _user_id_from_cookie(websocket.cookies.get("dsh_session"), settings)
            await manager.ensure(user_id)
            manager.active_requests[user_id] = manager.active_requests.get(user_id, 0) + 1
            manager.touch(user_id)
            await websocket.accept()
            upstream_authority = websocket.headers.get("x-forwarded-host") or websocket.headers.get("host")
            if not upstream_authority:
                raise PermissionError("缺少 DSH Web authority")
            upstream_origin = websocket.headers.get("origin")
            upstream_scheme = "wss" if websocket.url.scheme == "https" else "ws"
            upstream_uri = f"{upstream_scheme}://{manager._name(user_id)}:{CONTAINER_PORT}/{path}"
            upstream_kwargs = {"additional_headers": {"Host": upstream_authority}}
            if upstream_origin:
                upstream_kwargs["additional_headers"]["Origin"] = upstream_origin
            async with websocket_connect(
                upstream_uri,
                **upstream_kwargs,
            ) as upstream:
                async def client_to_upstream() -> None:
                    while True:
                        message = await websocket.receive()
                        if message.get("text") is not None:
                            await upstream.send(message["text"])
                        elif message.get("bytes") is not None:
                            await upstream.send(message["bytes"])

                async def upstream_to_client() -> None:
                    while True:
                        message = await upstream.recv()
                        if isinstance(message, bytes):
                            await websocket.send_bytes(message)
                        else:
                            await websocket.send_text(message)

                await asyncio.gather(client_to_upstream(), upstream_to_client())
        except PermissionError:
            await websocket.close(code=1008)
        except WebSocketDisconnect:
            pass
        except Exception:
            if websocket.client_state.name != 'DISCONNECTED':
                await websocket.close(code=1011)
        finally:
            if "user_id" in locals():
                manager.active_requests[user_id] = max(0, manager.active_requests.get(user_id, 1) - 1)

    return app


async def _release_request(manager: InstanceManager, user_id: str) -> None:
    manager.active_requests[user_id] = max(0, manager.active_requests.get(user_id, 1) - 1)


app = create_app()
