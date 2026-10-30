import hashlib
import json
from pathlib import Path


def source_digest():
    paths = []
    for directory in ["src", "tests", "scripts", "fixtures"]:
        paths.extend(
            p
            for p in Path(directory).rglob("*")
            if p.suffix in {".py", ".sql", ".json"} and "__pycache__" not in p.parts
        )
    paths += [Path(p) for p in ["pyproject.toml", "uv.lock", "Dockerfile", "compose.yaml"]]
    digest = hashlib.sha256()
    for path in sorted(paths):
        digest.update(path.as_posix().encode() + b"\0" + path.read_bytes() + b"\0")
    return digest.hexdigest()


def manifest():
    return {
        "source_digest": source_digest(),
        "fixture_digests": {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(Path("fixtures").glob("*.json"))
        },
        "groups": {f"A{n}": "required" for n in range(1, 13)},
        "load": {"submissions": 24, "concurrency": 4, "delay_ms": 200},
        "expected_outcomes": ["rejected", "received", "unresolved"],
        "provider": "controlled",
    }


def validate_manifest(value):
    if (
        set(value["groups"]) != {f"A{n}" for n in range(1, 13)}
        or not value["source_digest"]
        or not value["fixture_digests"]
    ):
        raise ValueError("invalid_acceptance_manifest")


def write_once(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, default=str, indent=2)
        handle.write("\n")
