import importlib.util
import subprocess
import sys
from pathlib import Path


def test_check_runner_retains_success_failure_and_timeout_output(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("verification_script", Path("scripts/verify.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for code in (0, 7):
        log = tmp_path / f"exit-{code}.log"
        status = module.run_check(
            [sys.executable, "-c", f"print('recorded'); raise SystemExit({code})"], log, timeout=2
        )
        assert status == code and "recorded" in log.read_text()
    log = tmp_path / "timeout.log"
    status = module.run_check(
        [sys.executable, "-c", "import time; print('checkpoint',flush=True); time.sleep(5)"],
        log,
        timeout=0.5,
    )
    assert status == 124
    assert "check_timeout" in log.read_text()

    # Fault injection pins partial-output retention without assuming interpreter
    # startup can finish before a short timeout on a busy host.
    def expired(command, *, stdout, timeout, **kwargs):
        stdout.write("checkpoint\n")
        raise subprocess.TimeoutExpired(command, timeout)

    monkeypatch.setattr(module.subprocess, "run", expired)
    partial = tmp_path / "partial.log"
    assert module.run_check(["fault-injected-child"], partial) == 124
    assert "checkpoint" in partial.read_text()
    assert "check_timeout" in partial.read_text()
