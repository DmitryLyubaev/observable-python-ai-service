import argparse
import json
import statistics

from p19.jobs import JobStore


def distribution(values):
    values = sorted(values)
    return {
        "n": len(values),
        "min": min(values) if values else None,
        "median": statistics.median(values) if values else None,
        "max": max(values) if values else None,
    }


def build_summary(run_ids, store):
    jobs = [store.get(job_id) for job_id in run_ids]
    attempts = [attempt for job in jobs for attempt in job["attempts"]]
    terminal = {}
    for job in jobs:
        terminal[job["state"]] = terminal.get(job["state"], 0) + 1
    return {
        "jobs": len(jobs),
        "terminal_counts": terminal,
        "attempts": len(attempts),
        "unknown_usage_attempts": sum(attempt["usage"] is None for attempt in attempts),
        "simulated_usage_attempts": sum(
            bool(attempt["usage"] and attempt["usage"].get("provenance") == "simulated")
            for attempt in attempts
        ),
        "provider_provenance": "controlled",
        "known_real_cost_usd": None,
        "queue_seconds": distribution(
            [
                (job["claimed_at"] - job["created_at"]).total_seconds()
                for job in jobs
                if job["claimed_at"]
            ]
        ),
        "completion_seconds": distribution(
            [(job["updated_at"] - job["created_at"]).total_seconds() for job in jobs]
        ),
        "provider_seconds": distribution(
            [
                attempt["duration_seconds"]
                for attempt in attempts
                if attempt["duration_seconds"] is not None
            ]
        ),
        "clock_limits": "Within-process monotonic durations; cross-stage timestamps use local PostgreSQL UTC clock.",
        "limits": "Synthetic controlled-provider local observations; no real-provider cost, quality or capacity claim.",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("job_ids", nargs="*")
    args = parser.parse_args()
    store = JobStore()
    print(
        json.dumps(
            build_summary(args.job_ids or [job["id"] for job in store.all()], store),
            default=str,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
