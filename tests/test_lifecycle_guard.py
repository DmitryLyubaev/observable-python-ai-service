import os
from copy import deepcopy

import docker
import pytest


def test_recovery_requires_exact_stopped_owned_worker(store):
    from p19.lifecycle import restart_worker

    project = os.environ["P19_PROJECT"]
    worker = docker.from_env().containers.get(f"{project}-worker-1")
    with pytest.raises(RuntimeError, match="running"):
        restart_worker(worker.id, store, project)
    with pytest.raises(RuntimeError, match="foreign"):
        restart_worker(worker.id, store, "another-project")
    assert store.all() == []


def test_live_recovery_preserves_only_exact_readonly_secret_mount():
    from p19.lifecycle import validated_volumes

    attrs = {
        "Config": {"Env": ["P19_PROVIDER=live", "P19_LIVE_STUDY=p19-real-20261030"]},
        "Mounts": [
            {"Type": "bind", "Source": "/repo/.local", "Destination": "/app/.local", "RW": True},
            {
                "Type": "bind",
                "Source": "/repo/.secrets/claude-api-key",
                "Destination": "/run/secrets/claude_api_key",
                "RW": False,
            },
        ],
    }
    assert validated_volumes(attrs)["/repo/.secrets/claude-api-key"]["mode"] == "ro"
    for change in ("writable", "foreign_source", "controlled"):
        unsafe = deepcopy(attrs)
        if change == "writable":
            unsafe["Mounts"][1]["RW"] = True
        elif change == "foreign_source":
            unsafe["Mounts"][1]["Source"] = "/elsewhere/secret"
        else:
            unsafe["Config"]["Env"] = ["P19_PROVIDER=controlled"]
        with pytest.raises(RuntimeError):
            validated_volumes(unsafe)
