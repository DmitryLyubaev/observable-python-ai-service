import os
import socket
import threading
import time
from contextlib import contextmanager

import httpx
import uvicorn
from conftest import record


@contextmanager
def serve(store):
    from p19.api import create_app

    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(create_app(store), log_level="critical"))
    thread = threading.Thread(target=lambda: server.run(sockets=[sock]), daemon=True)
    thread.start()
    deadline = time.monotonic() + 5
    while not server.started and time.monotonic() < deadline:
        time.sleep(0.01)
    assert server.started
    try:
        with httpx.Client(
            base_url=f"http://127.0.0.1:{port}",
            headers={"Authorization": f"Bearer {os.environ['P19_TOKEN']}"},
            timeout=5,
        ) as client:
            yield client
    finally:
        server.should_exit = True
        thread.join(5)
        sock.close()


def test_api_validation_auth_and_idempotency(store):
    with serve(store) as client:
        response = client.post("/investigations", json=record(), headers={"Idempotency-Key": "api"})
        assert response.status_code == 202
        job_id = response.json()["id"]
        for method, path in [
            ("GET", f"/investigations/{job_id}"),
            ("GET", f"/investigations/{job_id}/events"),
            ("POST", f"/investigations/{job_id}/cancel"),
            ("POST", "/investigations"),
        ]:
            assert client.request(method, path, headers={"Authorization": "bad"}).status_code == 401
        assert (
            client.post(
                "/investigations", json=record(9), headers={"Idempotency-Key": "api"}
            ).status_code
            == 409
        )
        assert client.get("/investigations/missing").status_code == 404
        assert client.post("/investigations", json={}).status_code == 422
        assert (
            client.post(
                "/investigations",
                content=iter([b"x" * 4096] * 3),
                headers={"Idempotency-Key": "big"},
            ).status_code
            == 422
        )
        assert client.post(f"/investigations/{job_id}/cancel").status_code == 202
        assert client.post(f"/investigations/{job_id}/cancel").json()["state"] == "cancelled"


def test_admission_capacity_through_http(store):
    with serve(store) as client:
        for n in range(8):
            assert (
                client.post(
                    "/investigations", json=record(n), headers={"Idempotency-Key": str(n)}
                ).status_code
                == 202
            )
        assert (
            client.post(
                "/investigations", json=record(9), headers={"Idempotency-Key": "overflow"}
            ).status_code
            == 429
        )


def test_database_unavailable_has_safe_503(store, monkeypatch):
    with serve(store) as client:

        def failed(*args, **kwargs):
            from sqlalchemy.exc import OperationalError

            raise OperationalError("secret_payload", {}, Exception("secret"))

        monkeypatch.setattr(store, "admit", failed)
        response = client.post(
            "/investigations", json=record(), headers={"Idempotency-Key": "outage"}
        )
        assert response.status_code == 503
        assert "secret" not in response.text
