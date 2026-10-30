from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class FailureRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")
    export_id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    sale_id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    failure_code: str = Field(min_length=1, max_length=64)
    occurred_at: datetime
    diagnostic_text: str = Field(max_length=2048)
    supersedes_job_id: UUID | None = None

    @field_validator("occurred_at")
    @classmethod
    def timezone_required(cls, value):
        if value.tzinfo is None:
            raise ValueError("timezone_required")
        return value


class InvestigationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[1] = 1
    summary: str = Field(min_length=1, max_length=2048)
    receiver_outcome: Literal["rejected", "received", "unresolved"]
    evidence_ids: list[str] = Field(max_length=8)
    uncertainty: str = Field(max_length=2048)
    next_diagnostic_step: str = Field(min_length=1, max_length=2048)


TERMINAL = {"succeeded", "failed", "cancelled", "interrupted", "outcome_unknown"}
