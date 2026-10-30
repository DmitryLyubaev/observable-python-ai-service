"""Generate local-only credentials without displaying them."""

import os
import secrets
from pathlib import Path

path = Path(".env")
if not path.exists():
    with path.open("x") as handle:
        handle.write(
            f"P19_TOKEN={secrets.token_hex(32)}\nP19_DB_PASSWORD={secrets.token_hex(24)}\n"
        )
    os.chmod(path, 0o600)
Path(".local").mkdir(exist_ok=True)
print("Local configuration ready; credentials are in the ignored .env file.")
