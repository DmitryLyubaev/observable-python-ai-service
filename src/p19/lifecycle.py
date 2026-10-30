import argparse
import json
import os
from pathlib import Path

import docker
from sqlalchemy import text

from p19.jobs import JobStore
from p19.recovery import recover_worker


def restart_worker(container_id, store, project, *, barrier=None, profile="success"):
    client = docker.from_env(timeout=10)
    with store.db.engine.connect() as conn:
        if not conn.execute(text("SELECT pg_try_advisory_lock(190021)")).scalar_one():
            raise RuntimeError("lifecycle_busy")
        try:
            old = client.containers.get(container_id)
            attrs = old.attrs
            labels = attrs["Config"].get("Labels", {})
            if (
                labels.get("com.docker.compose.project") != project
                or labels.get("com.docker.compose.service") != "worker"
            ):
                raise RuntimeError("foreign_worker")
            if attrs["State"]["Running"]:
                raise RuntimeError("worker_still_running")
            others = client.containers.list(
                filters={
                    "label": [
                        f"com.docker.compose.project={project}",
                        "com.docker.compose.service=worker",
                    ]
                }
            )
            if others:
                raise RuntimeError("replacement_already_running")
            if not attrs["Config"]["Cmd"][:3] == ["celery", "-A", "p19.worker:app"]:
                raise RuntimeError("unexpected_worker_configuration")
            networks = list(attrs["NetworkSettings"]["Networks"])
            if networks != [f"{project}_default"]:
                raise RuntimeError("unexpected_worker_network")
            volumes = {}
            for mount in attrs["Mounts"]:
                if mount["Destination"] != "/app/.local" or mount["Type"] != "bind":
                    raise RuntimeError("unexpected_worker_mount")
                volumes[mount["Source"]] = {"bind": mount["Destination"], "mode": "rw"}
            owner = attrs["Config"]["Hostname"]
            if owner != old.id[:12]:
                raise RuntimeError("worker_identity_mismatch")
            proof = {
                "container_id": old.id,
                "instance_id": owner,
                "project": project,
                "image_id": attrs["Image"],
                "stopped_at": attrs["State"]["FinishedAt"],
            }
            Path(".local").mkdir(exist_ok=True)
            Path(f".local/recovery-{old.id}.json").write_text(json.dumps(proof))
            recover_worker(store, owner)
            environment = dict(entry.split("=", 1) for entry in attrs["Config"]["Env"])
            environment.pop("P19_BARRIER", None)
            environment["P19_PROFILE"] = profile
            if barrier:
                environment["P19_BARRIER"] = barrier
            image, command, name = attrs["Image"], attrs["Config"]["Cmd"], old.name
            user = attrs["Config"]["User"]
            old.remove(v=False)
            return client.containers.run(
                image,
                command,
                name=name,
                environment=environment,
                labels=labels,
                volumes=volumes,
                network=networks[0],
                user=user,
                detach=True,
            )
        finally:
            conn.execute(text("SELECT pg_advisory_unlock(190021)"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["restart-worker"])
    parser.add_argument("--container", required=True)
    parser.add_argument("--project", default=os.environ.get("P19_PROJECT", "p19-demo"))
    args = parser.parse_args()
    worker = restart_worker(args.container, JobStore(), args.project)
    print(json.dumps({"worker_container": worker.id}))


if __name__ == "__main__":
    main()
