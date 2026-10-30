import time
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine, text


class ExecutionDeadline(Exception):
    pass


class Database:
    def __init__(self, url):
        self.engine = create_engine(
            url, pool_size=12, max_overflow=4, pool_timeout=2, connect_args={"connect_timeout": 3}
        )
        with self.write() as conn:
            conn.execute(text(Path(__file__).with_name("schema.sql").read_text()))

    @contextmanager
    def write(self, deadline=None):
        if deadline is not None and time.monotonic() >= deadline:
            raise ExecutionDeadline("execution_deadline")
        with self.engine.begin() as conn:
            remaining = 2 if deadline is None else min(2, deadline - time.monotonic())
            if remaining <= 0:
                raise ExecutionDeadline("execution_deadline")
            timeout = str(max(1, int(remaining * 1000)))
            conn.execute(
                text(
                    "SELECT set_config('lock_timeout',:timeout,true),set_config('statement_timeout',:timeout,true)"
                ),
                {"timeout": timeout},
            )
            conn.execute(text("SELECT pg_advisory_xact_lock(190019)"))
            if deadline is not None and time.monotonic() >= deadline:
                raise ExecutionDeadline("execution_deadline")
            yield conn
