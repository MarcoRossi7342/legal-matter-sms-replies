from __future__ import annotations

import logging
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel

from .infrai_sms import InfraiError, InfraiSMS
from .matter_replies import InboundSMS, ReplyAction, decide_reply

logger = logging.getLogger("legal_sms")
service = FastAPI(title="Legal matter SMS replies")


class ReplyReceipt(BaseModel):
    event_id: str
    action: ReplyAction
    outbound_message_id: str


def sms_client() -> InfraiSMS:
    return InfraiSMS()


@service.post("/inbound-sms", response_model=ReplyReceipt)
async def handle_inbound_sms(
    inbound: InboundSMS,
    client: Annotated[InfraiSMS, Depends(sms_client)],
) -> ReplyReceipt:
    decision = decide_reply(inbound)
    try:
        sent = await client.send(
            to=inbound.from_number,
            message=decision.text,
            idempotency_key=f"inbound-reply:{inbound.event_id}",
        )
    except InfraiError as exc:
        caller_status = exc.status_code if 400 <= exc.status_code < 500 else 502
        raise HTTPException(status_code=caller_status, detail={"code": exc.code}) from exc

    logger.info("reply sent", extra={"event_id": inbound.event_id, "action": decision.action})
    return ReplyReceipt(
        event_id=inbound.event_id,
        action=decision.action,
        outbound_message_id=sent.message_id,
    )

