from conftest import record


def test_summary_preserves_unknown_usage(store):
    from p19.reporting import build_summary
    from p19.runner import run_job

    job = store.admit(record(), "unknown-cost")
    run_job(job["id"], "local", store=store, profile="timeout")
    summary = build_summary([job["id"]], store)
    assert summary["jobs"] == 1
    assert summary["unknown_usage_attempts"] == 1
    assert summary["known_real_cost_usd"] is None
    assert summary["provider_provenance"] == "controlled"
