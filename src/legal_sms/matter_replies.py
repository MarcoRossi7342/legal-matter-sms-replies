from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from pydantic import BaseModel, Field, HttpUrl


class MatterStage(StrEnum):
    INTAKE = "intake"
    AWAITING_SIGNATURE = "awaiting_signature"
    SIGNED = "signed"
    DEADLINE_PENDING = "deadline_pending"


class InboundSMS(BaseModel):
    event_id: str = Field(min_length=1, max_length=120)
    from_number: str = Field(pattern=r"^\+[1-9]\d{7,14}$")
    body: str = Field(min_length=1, max_length=1600)
    matter_reference: str = Field(min_length=1, max_length=80)
    stage: MatterStage
    signed_document_url: HttpUrl | None = None
    deadline: date | None = None


class ReplyAction(StrEnum):
    INTAKE_RECORDED = "intake_recorded"
    SIGNED_DOCUMENT_DELIVERY = "signed_document_delivery"
    DEADLINE_CONFIRMED = "deadline_confirmed"
    HUMAN_REVIEW = "human_review"


@dataclass(frozen=True)
class ReplyDecision:
    action: ReplyAction
    text: str


def decide_reply(inbound: InboundSMS) -> ReplyDecision:
    normalized = " ".join(inbound.body.upper().split())

    if inbound.stage is MatterStage.SIGNED and inbound.signed_document_url:
        return ReplyDecision(
            ReplyAction.SIGNED_DOCUMENT_DELIVERY,
            f"Matter {inbound.matter_reference}: your signed document is ready: "
            f"{inbound.signed_document_url}",
        )

    if inbound.stage is MatterStage.DEADLINE_PENDING and inbound.deadline:
        if normalized in {"YES", "CONFIRM", "CONFIRMED"}:
            return ReplyDecision(
                ReplyAction.DEADLINE_CONFIRMED,
                f"Matter {inbound.matter_reference}: deadline confirmed for "
                f"{inbound.deadline.isoformat()}.",
            )
        return ReplyDecision(
            ReplyAction.HUMAN_REVIEW,
            f"Matter {inbound.matter_reference}: your reply was recorded for staff review.",
        )

    if inbound.stage is MatterStage.INTAKE:
        return ReplyDecision(
            ReplyAction.INTAKE_RECORDED,
            f"Matter {inbound.matter_reference}: intake reply recorded. A team member will review it.",
        )

    return ReplyDecision(
        ReplyAction.HUMAN_REVIEW,
        f"Matter {inbound.matter_reference}: your reply was recorded for staff review.",
    )

