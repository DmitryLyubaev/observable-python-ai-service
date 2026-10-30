import time

from p19.provider import ProviderFailure


class ControlledProvider:
    def __init__(self, profile="success"):
        self.profile = profile

    def invoke(self, record, evidence, attempt, timeout_seconds):
        if self.profile in {"rate_exhausted", "long_retry"} or (
            self.profile == "rate_then_success" and attempt == 1
        ):
            raise ProviderFailure("rate_limit", True, 3 if self.profile == "long_retry" else 0.05)
        if self.profile in {"timeout", "ambiguous_5xx"}:
            if self.profile == "timeout":
                time.sleep(min(timeout_seconds, 0.05))
            raise ProviderFailure(self.profile)
        if self.profile == "rejected":
            raise ProviderFailure("provider_rejected", True)
        if self.profile == "load":
            time.sleep(min(0.2, timeout_seconds))
        outcome = evidence["receiver_outcome"]
        summaries = {
            "received": "A matching receiver receipt confirms the sale was recorded despite the timeout.",
            "rejected": "An explicit rejection identifies an invalid fictional account code.",
            "unresolved": "Available evidence does not establish whether the sale was recorded.",
        }
        steps = {
            "received": "Inspect the receipt before considering another export; a resend could duplicate the sale.",
            "rejected": "Check the account mapping before any later operator action.",
            "unresolved": "Perform an independent receiver check before deciding whether to resend.",
        }
        result = dict(
            schema_version=1,
            summary=summaries[outcome],
            receiver_outcome=outcome,
            evidence_ids=[row["id"] for row in evidence["records"]],
            uncertainty="Only the supplied synthetic evidence was inspected.",
            next_diagnostic_step=steps[outcome],
        )
        if self.profile == "contradictory":
            result["receiver_outcome"] = "rejected" if outcome != "rejected" else "received"
        if self.profile == "foreign_citation":
            result["evidence_ids"] = ["not_supplied"]
        if self.profile == "malformed":
            result = {}
        return {
            "result": result,
            "usage": {
                "provenance": "simulated",
                "input_tokens": 100,
                "output_tokens": 50,
                "cost_usd": None,
            },
        }
