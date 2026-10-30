import argparse
import json
import os
import sys
import time
from pathlib import Path

import httpx


def main(argv=None):
    parser = argparse.ArgumentParser(description="Synthetic integration investigation operator")
    parser.add_argument("--url", default=os.environ.get("P19_URL", "http://api:8000"))
    commands = parser.add_subparsers(dest="command", required=True)
    submit = commands.add_parser("submit")
    submit.add_argument("--file", required=True)
    submit.add_argument("--idempotency-key", required=True)
    for command in ["get", "follow", "cancel"]:
        child = commands.add_parser(command)
        child.add_argument("job_id")
        if command == "follow":
            child.add_argument("--after", type=int, default=0)
    args = parser.parse_args(argv)
    if not os.environ.get("P19_TOKEN"):
        print("operator_token_missing", file=sys.stderr)
        return 2
    with httpx.Client(
        base_url=args.url,
        headers={"Authorization": f"Bearer {os.environ['P19_TOKEN']}"},
        timeout=15,
    ) as client:
        try:
            if args.command == "submit":
                response = client.post(
                    "/investigations",
                    json=json.loads(Path(args.file).read_text()),
                    headers={"Idempotency-Key": args.idempotency_key},
                )
            elif args.command == "follow":
                cursor = args.after
                for retry in range(3):
                    try:
                        with client.stream(
                            "GET",
                            f"/investigations/{args.job_id}/events",
                            headers={"Last-Event-ID": str(cursor)},
                        ) as response:
                            response.raise_for_status()
                            pending = None
                            for line in response.iter_lines():
                                if line.startswith("id:"):
                                    pending = int(line[3:])
                                elif line.startswith("data:") and pending is not None:
                                    payload = json.loads(line[5:])
                                    if pending > cursor:
                                        print(json.dumps(payload), flush=True)
                                        cursor = pending
                                    pending = None
                        return 0
                    except httpx.TransportError:
                        if retry == 2:
                            raise
                        print("stream_connection_lost_reconnecting", file=sys.stderr)
                        time.sleep(0.2)
            elif args.command == "cancel":
                response = client.post(f"/investigations/{args.job_id}/cancel")
            else:
                response = client.get(f"/investigations/{args.job_id}")
            response.raise_for_status()
            print(json.dumps(response.json()), flush=True)
            return 0
        except (httpx.HTTPError, OSError, ValueError):
            print("request_failed", file=sys.stderr)
            return 1


if __name__ == "__main__":
    raise SystemExit(main())
