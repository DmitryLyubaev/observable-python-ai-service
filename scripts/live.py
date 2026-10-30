"""Administer the approved three-case study. No inference retries or budget reset."""

import argparse
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path

from p19.acceptance import RunJournal, write_once
from p19.claude import MODEL, bounded_request, canonical
from p19.evidence import seed
from p19.jobs import JobStore
from p19.live import PROPOSAL_SHA, STUDY, LiveGuard, LiveStudy, digest, fixture_cases, make_manifest


def validate_secret_configuration(config):
    services = config.get("services", {})
    for required in ("worker", "live-admin"):
        if required not in services:
            raise LiveGuard("live_service_missing")
    for name, service in services.items():
        references = service.get("secrets", [])
        sources = {item if isinstance(item, str) else item["source"] for item in references}
        if ("claude_api_key" in sources) != (name in {"worker", "live-admin"}):
            raise LiveGuard("provider_secret_service_exposure")
        environment = service.get("environment", {})
        if isinstance(environment, list):
            environment = dict(item.split("=", 1) for item in environment)
        if {"ANTHROPIC_API_KEY", "P19_CLAUDE_API_KEY"} & environment.keys():
            raise LiveGuard("provider_secret_in_environment")
        for mount in service.get("volumes", []):
            if ".secrets" in str(mount) or "/run/secrets" in str(mount):
                raise LiveGuard("provider_secret_in_shared_volume")
    worker_env = services["worker"].get("environment", {})
    if worker_env.get("P19_PROVIDER") != "live" or worker_env.get("P19_LIVE_STUDY") != STUDY:
        raise LiveGuard("live_worker_mode_missing")
    source = Path(config["secrets"]["claude_api_key"]["file"])
    if source.name != "claude-api-key" or source.parent.name != ".secrets":
        raise LiveGuard("provider_secret_source_invalid")


def checked_model(body):
    try:
        capabilities = body["capabilities"]
        valid = (
            body["id"] == MODEL
            and body["lifecycle"] == "active"
            and type(body["max_input_tokens"]) is int
            and 4096 <= body["max_input_tokens"] <= 1_000_000
            and type(body["max_tokens"]) is int
            and body["max_tokens"] >= 1024
            and capabilities["structured_outputs"]["supported"] is True
            and capabilities["effort"]["low"]["supported"] is True
            and capabilities["thinking"]["types"]["adaptive"]["supported"] is True
        )
    except (KeyError, TypeError):
        valid = False
    if not valid:
        raise LiveGuard("live_model_capabilities_unverified")


def prepare(store, key_path, output, approval, *, transport=None):
    value = LiveStudy(store)
    if value.status()["state"] != "uninitialized":
        raise LiveGuard("live_study_already_initialized")
    if any(job["state"] in {"queued", "preparing", "calling"} for job in store.all()):
        raise LiveGuard("live_requires_idle_job_store")
    seed(store)
    draft = make_manifest(store, approval, [0, 0, 0])
    output.parent.mkdir(parents=True, exist_ok=True)
    receipt = output.parent / f"preflight-{uuid.uuid4().hex}.json"
    counts = []
    with RunJournal(receipt, draft) as journal:

        def request(method, path, payload=None):
            def send():
                status, request_id, raw = bounded_request(
                    method, path, key_path, payload, transport=transport
                )
                try:
                    body = json.loads(raw)
                except (ValueError, UnicodeError):
                    body = {"unparseable": raw.decode(errors="replace")}
                return {
                    "status": status,
                    "request_id": request_id,
                    "path": path,
                    "payload_hash": digest(payload) if payload else None,
                    "body": body,
                }

            result = journal.capture_response(len(journal.responses), send)
            if result["status"] != 200:
                raise LiveGuard("live_preflight_http_rejected")
            return result["body"]

        checked_model(request("GET", f"/v1/models/{MODEL}"))
        for case in draft["cases"]:
            full = json.loads(case["payload"])
            count_payload = {
                key: full[key]
                for key in ("model", "messages", "system", "thinking", "output_config")
            }
            result = request("POST", "/v1/messages/count_tokens", canonical(count_payload))
            count = result.get("input_tokens") if isinstance(result, dict) else None
            if type(count) is not int or not 0 < count <= 4096:
                raise LiveGuard("live_input_estimate_invalid")
            counts.append(count)
        journal.succeed({"model": MODEL, "counts": counts, "source_digest": draft["source_digest"]})
    manifest = make_manifest(
        store,
        {
            **approval,
            "preflight_receipt": str(receipt),
            "preflight_sha256": digest(receipt.read_bytes()),
        },
        counts,
    )
    write_once(output, manifest)
    value.initialize(manifest)
    return {
        "prepared": True,
        "model": MODEL,
        "source_digest": manifest["source_digest"],
        "count_estimates": counts,
        "manifest": str(output),
    }


def cli(url, *arguments, timeout=15):
    result = subprocess.run(
        [sys.executable, "-m", "p19.cli", "--url", url, *arguments],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result.returncode:
        raise LiveGuard("live_cli_operation_failed")
    return result.stdout


def run_next(store, url, root):
    study = LiveStudy(store)
    study.require_preflight()
    status = study.status()
    if status["state"] != "active":
        raise LiveGuard("live_study_not_active")
    calls = status["calls"]
    if calls and calls[-1]["assessment"] is None:
        last = calls[-1]
        job = store.get(last["job_id"])
        if job["state"] == "succeeded" and last["state"] == "settled":
            return {"state": "awaiting_assessment", "case_id": last["case_id"], "job_id": job["id"]}
        raise LiveGuard("live_previous_case_not_assessed")
    index = len(calls)
    if index >= 3:
        raise LiveGuard("live_all_slots_consumed")
    record = fixture_cases()[index]
    case_id = record["export_id"]
    root.mkdir(parents=True, exist_ok=True)
    intent = root / f"{case_id}.intent.json"
    if intent.exists():
        raise LiveGuard("live_submission_already_recorded")
    # This global study/case key never changes with output directories or invocations.
    key = f"live-{STUDY}-{case_id}"
    write_once(
        intent,
        {
            "case_id": case_id,
            "idempotency_key": key,
            "source_digest": status["manifest"]["source_digest"],
        },
    )
    receipt = {"case_id": case_id, "state": "failed", "job_id": None}
    try:
        path = root / f"{case_id}.request.json"
        write_once(path, record)
        admitted = json.loads(cli(url, "submit", "--file", str(path), "--idempotency-key", key))
        receipt["job_id"] = admitted["id"]
        write_once(root / f"{case_id}.admitted.json", admitted)
        progress = cli(url, "follow", admitted["id"], timeout=95)
        (root / f"{case_id}.progress.jsonl").write_text(progress)
        saved = json.loads(cli(url, "get", admitted["id"]))
        write_once(root / f"{case_id}.result.json", saved)
        receipt["job_state"] = saved["state"]
        expected = ["rejected", "received", "unresolved"][index]
        expected_ids = [["ev_reject"], ["ev_receipt"], []][index]
        result = saved.get("result") or {}
        if (
            saved["state"] == "succeeded"
            and result.get("receiver_outcome") == expected
            and sorted(result.get("evidence_ids", [])) == expected_ids
        ):
            receipt["state"] = "awaiting_assessment"
        else:
            receipt["error"] = "live_case_automated_check_failed"
            study.stop(receipt["error"])
    except Exception as exc:
        receipt["error"] = type(exc).__name__
        study.stop("live_driver_failure")
    receipt["budget"] = study.status()
    write_once(root / f"{case_id}.receipt.json", receipt)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    preparation = commands.add_parser("prepare")
    preparation.add_argument(
        "--output", type=Path, default=Path(f".local/live/{STUDY}/manifest.json")
    )
    preparation.add_argument("--approval", type=Path, default=Path(".local/live-approval.json"))
    commands.add_parser("status")
    run = commands.add_parser("run")
    run.add_argument("--next", action="store_true", required=True)
    assess = commands.add_parser("assess")
    assess.add_argument("--case", required=True)
    assess.add_argument("--decision", choices=["pass", "fail"], required=True)
    assess.add_argument("--notes-file", type=Path, required=True)
    commands.add_parser("check-config")
    args = parser.parse_args()
    try:
        if args.command == "check-config":
            validate_secret_configuration(json.load(sys.stdin))
            print(json.dumps({"provider_secret_isolated": True}))
            return 0
        if os.environ.get("P19_PROJECT") != "p19-demo" or os.environ.get("P19_TEST"):
            raise LiveGuard("live_cli_requires_demo_namespace")
        store = JobStore()
        if args.command == "prepare":
            approval = json.loads(args.approval.read_text(encoding="utf-8-sig"))
            if (
                approval.get("approved_proposal_sha256") != PROPOSAL_SHA
                or approval.get("owner_personal_account_and_alert_confirmed") is not True
                or approval.get("plan_approved") is not True
                or approval.get("allowance_usd") != "2"
                or approval.get("max_inference_calls") != 3
                or approval.get("automatic_retries") != 0
                or approval.get("model") != MODEL
            ):
                raise LiveGuard("live_owner_approval_missing")
            output = prepare(
                store,
                Path(os.environ.get("P19_CLAUDE_KEY_FILE", "/run/secrets/claude_api_key")),
                args.output,
                {**approval, "owner_confirmed": True},
            )
        elif args.command == "run":
            output = run_next(
                store,
                os.environ.get("P19_URL", "http://api:8000"),
                Path(f".local/live/{STUDY}/run"),
            )
        elif args.command == "assess":
            LiveStudy(store).assess(args.case, args.decision, args.notes_file.read_text())
            output = {"case_id": args.case, "assistant_assessment": args.decision}
        else:
            output = LiveStudy(store).status()
        print(json.dumps(output, default=str))
        return 1 if output.get("state") == "failed" else 0
    except Exception as exc:
        print(
            json.dumps({"error": str(exc) if isinstance(exc, LiveGuard) else type(exc).__name__}),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
