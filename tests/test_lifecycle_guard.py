import os

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
