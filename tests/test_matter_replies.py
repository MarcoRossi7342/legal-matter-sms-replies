from datetime import date

from legal_sms.matter_replies import InboundSMS, ReplyAction, decide_reply


def test_confirmed_deadline_moves_to_confirmed_reply() -> None:
    inbound = InboundSMS(
        event_id="evt-1042",
        from_number="+14155550142",
        body="  confirm  ",
        matter_reference="MAT-204",
        stage="deadline_pending",
        deadline=date(2026, 9, 18),
    )

    decision = decide_reply(inbound)

    assert decision.action is ReplyAction.DEADLINE_CONFIRMED
    assert decision.text == "Matter MAT-204: deadline confirmed for 2026-09-18."

