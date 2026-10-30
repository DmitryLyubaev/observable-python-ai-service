import time

from conftest import record
from test_api import serve


def test_disconnect_does_not_cancel_and_reconnect_has_no_gaps(store):
    from p19.broker import publish

    with serve(store) as client:
        job = client.post(
            "/investigations", json=record(), headers={"Idempotency-Key": "sse"}
        ).json()
        with client.stream("GET", f"/investigations/{job['id']}/events") as response:
            for line in response.iter_lines():
                if line.startswith("id:"):
                    last = int(line.split(":")[1])
                    break
        assert not store.get(job["id"])["cancel_requested"]
        publish(job["id"], {})
        deadline = time.monotonic() + 10
        while store.get(job["id"])["state"] != "succeeded" and time.monotonic() < deadline:
            time.sleep(0.05)
        response = client.get(
            f"/investigations/{job['id']}/events", headers={"Last-Event-ID": str(last)}
        )
        ids = [int(line[3:]) for line in response.text.splitlines() if line.startswith("id:")]
        expected = [ev["sequence"] for ev in store.events_after(job["id"], last)]
        assert ids == expected
        assert client.get(f"/investigations/{job['id']}").json()["result"]


def test_sse_cursor_validation_and_terminal_close(store):
    job = store.admit(record(), "cursor")
    store.cancel(job["id"])
    with serve(store) as client:
        path = f"/investigations/{job['id']}/events"
        for value in ["-1", "bad", "99999"]:
            assert client.get(path, headers={"Last-Event-ID": value}).status_code == 422
        assert (
            client.get(path, headers={"Last-Event-ID": str(store.get(job["id"])["sequence"])}).text
            == ""
        )
