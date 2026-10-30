from pydantic import ValidationError

from p19.contracts import InvestigationResult


class InvalidProviderOutput(Exception):
    pass


class ProviderFailure(Exception):
    def __init__(self, kind, definitely_not_processed=False, retry_after_seconds=None):
        super().__init__(kind)
        self.kind = kind
        self.definitely_not_processed = definitely_not_processed
        self.retry_after_seconds = retry_after_seconds


def validate_reply(reply, evidence):
    try:
        result = InvestigationResult.model_validate(reply["result"]).model_dump(mode="json")
        allowed = {row["id"] for row in evidence["records"]}
        if (
            result["receiver_outcome"] != evidence["receiver_outcome"]
            or not set(result["evidence_ids"]) <= allowed
        ):
            raise InvalidProviderOutput("invalid_provider_output")
        return result
    except (ValidationError, KeyError, TypeError) as exc:
        raise InvalidProviderOutput("invalid_provider_output") from exc
