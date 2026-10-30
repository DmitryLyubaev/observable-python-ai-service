import copy

import pytest


def test_acceptance_manifest_requires_all_groups_and_original_dispositions(tmp_path):
    from p19.acceptance import manifest, validate_manifest, write_once

    value = manifest()
    assert set(value["groups"]) == {f"A{n}" for n in range(1, 13)}
    assert value["source_digest"] and value["fixture_digests"]
    broken = copy.deepcopy(value)
    broken["groups"].pop("A9")
    with pytest.raises(ValueError):
        validate_manifest(broken)
    target = tmp_path / "receipt.json"
    write_once(target, {"original": "failed"})
    with pytest.raises(FileExistsError):
        write_once(target, {"replacement": "passed"})
    assert '"failed"' in target.read_text()
