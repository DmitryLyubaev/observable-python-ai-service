import json
import os
import socket
import subprocess
import sys
import uuid
from pathlib import Path

import docker

from p19.acceptance import manifest, write_once


def run_check(command, log_path, timeout=240):
    with log_path.open("w") as output:
        try:
            result = subprocess.run(
                command, stdout=output, stderr=subprocess.STDOUT, text=True, timeout=timeout
            )
        except subprocess.TimeoutExpired:
            output.write("\ncheck_timeout\n")
            return 124
    return result.returncode


def main():
    project = os.environ["P19_PROJECT"]
    if project != "p19-check":
        raise SystemExit("checks_require_p19_check_namespace")
    client = docker.from_env()
    run = Path(".local/runs") / f"verify-{uuid.uuid4().hex}"
    run.mkdir(parents=True)
    write_once(run / "manifest.json", manifest())
    outcomes = []
    try:
        for command in [
            ["uv", "lock", "--check"],
            ["ruff", "check", "src", "tests", "scripts"],
            ["ruff", "format", "--check", "src", "tests", "scripts"],
            ["pytest", "-q", f"--junitxml={run / 'junit.xml'}"],
        ]:
            name = command[0] + ("-format" if "format" in command else "")
            log = run / (name + ".log")
            status = run_check(command, log)
            print(log.read_text()[-2500:], flush=True)
            outcomes.append({"command": command, "exit": status})
            if status:
                break
        success = all(row["exit"] == 0 for row in outcomes) and len(outcomes) == 4
        write_once(
            run / "receipt.json",
            {"success": success, "commands": outcomes, "source": manifest()["source_digest"]},
        )
        print(json.dumps({"success": success, "receipt": str(run / "receipt.json")}))
        return 0 if success else 1
    finally:
        # Only exact-owned containers, retaining all volumes and this current checks process.
        for container in client.containers.list(
            filters={"label": f"com.docker.compose.project={project}"}
        ):
            if container.id.startswith(socket.gethostname()):
                continue
            container.stop(timeout=3)


if __name__ == "__main__":
    sys.exit(main())
