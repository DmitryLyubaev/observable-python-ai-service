import importlib.util
import sys
from pathlib import Path


def test_check_runner_retains_success_failure_and_timeout_output(tmp_path):
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
    assert "checkpoint" in log.read_text()
    assert "check_timeout" in log.read_text()
