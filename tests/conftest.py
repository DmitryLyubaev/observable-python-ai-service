import pytest

from p19.jobs import JobStore


@pytest.fixture
def store():
    value = JobStore()
    value.reset()
    return value


def record(n=0):
    return dict(
        export_id=f"export_{n}",
        sale_id=f"sale_{n}",
        failure_code="timeout",
        occurred_at="2026-10-30T00:00:00Z",
        diagnostic_text="synthetic timeout",
    )
