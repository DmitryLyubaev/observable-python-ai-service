import time

from sqlalchemy import text

from p19.broker import publish
from p19.jobs import JobStore


class Dispatcher:
    def __init__(self, store, publisher=publish):
        self.store, self.publisher = store, publisher

    def tick(self, now=None):
        published = 0
        for job in self.store.all():
            if job["state"] == "queued":
                reserved = self.store.reserve_publication(job["id"], now)
                if reserved:
                    try:
                        self.publisher(job["id"], reserved["trace_context"])
                        published += 1
                    except Exception:
                        self.store.observe(job["id"], "publication_failure")
        return published


def main():
    store = JobStore()
    with store.db.engine.connect() as conn:
        if not conn.execute(text("SELECT pg_try_advisory_lock(190020)")).scalar_one():
            raise SystemExit("dispatcher_already_running")
        dispatcher = Dispatcher(store)
        while True:
            try:
                dispatcher.tick()
            except Exception:
                print("dispatcher_tick_failed", flush=True)
            time.sleep(1)


if __name__ == "__main__":
    main()
