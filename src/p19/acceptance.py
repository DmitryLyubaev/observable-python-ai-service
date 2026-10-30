import hashlib
import json
import threading
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


class RunJournal:
    """Reserve an immutable run name before work and retain failed/partial observations."""

    def __init__(self, path, metadata):
        self.path = Path(path)
        self.metadata = metadata
        self.responses = []
        self.terminals = []
        self.payload = None
        self.job_reader = None
        self.lock = threading.Lock()
        if self.path.exists():
            raise FileExistsError("run_receipt_already_exists")
        write_once(
            Path(str(self.path) + ".intent.json"), {"status": "started", "manifest": metadata}
        )
        self.observation_path = Path(str(self.path) + ".observations.jsonl")
        with self.observation_path.open("x", encoding="utf-8"):
            pass

    def __enter__(self):
        return self

    def response(self, value):
        with self.lock:
            self.responses.append(value)
            with self.observation_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps({"kind": "response", **value}, default=str) + "\n")
                handle.flush()

    def capture_response(self, index, send):
        try:
            value = send()
        except Exception as exc:
            self.response({"index": index, "status": None, "error_type": type(exc).__name__})
            raise
        self.response(value)
        return value

    def terminal(self, job):
        value = {"job_id": job["id"], "state": job["state"], "attempts": len(job["attempts"])}
        self.terminals.append(value)
        with self.observation_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({"kind": "terminal", **value}) + "\n")

    def succeed(self, payload):
        self.payload = payload

    def __exit__(self, exc_type, exc, traceback):
        if self.job_reader:
            captured = {row["job_id"] for row in self.terminals}
            for row in self.responses:
                job_id = row.get("job_id")
                if job_id and job_id not in captured:
                    try:
                        self.terminal(self.job_reader(job_id))
                    except Exception as read_error:
                        self.terminals.append(
                            {
                                "job_id": job_id,
                                "state": "unavailable",
                                "error_type": type(read_error).__name__,
                            }
                        )
                    captured.add(job_id)
        status = "passed" if exc_type is None and self.payload is not None else "failed"
        value = {
            "manifest": self.metadata,
            "responses": self.responses,
            "terminal_observations": self.terminals,
            **(self.payload or {}),
            "status": status,
        }
        if status == "failed":
            value["error_type"] = exc_type.__name__ if exc_type else "IncompleteRun"
        write_once(self.path, value)
        return False
