from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine, text


class Database:
    def __init__(self, url):
        self.engine = create_engine(
            url, pool_size=12, max_overflow=4, connect_args={"connect_timeout": 3}
        )
        with self.write() as conn:
            conn.execute(text(Path(__file__).with_name("schema.sql").read_text()))

    @contextmanager
    def write(self):
        with self.engine.begin() as conn:
            conn.execute(text("SELECT pg_advisory_xact_lock(190019)"))
            yield conn
