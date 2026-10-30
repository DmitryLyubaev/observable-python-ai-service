import os
import subprocess
import sys

from conftest import record
from test_api import serve


def test_cli_get_uses_header_without_leaking_token(store):
    job = store.admit(record(), "cli")
    with serve(store) as client:
        result = subprocess.run(
            [sys.executable, "-m", "p19.cli", "--url", str(client.base_url), "get", job["id"]],
            capture_output=True,
            text=True,
            timeout=10,
        )
    assert result.returncode == 0
    assert job["id"] in result.stdout
    assert os.environ["P19_TOKEN"] not in result.stdout + result.stderr
