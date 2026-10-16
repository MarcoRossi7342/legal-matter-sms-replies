import json

import httpx
from fastapi.testclient import TestClient

from legal_sms.inbound_service import service, sms_client
from legal_sms.infrai_sms import InfraiSMS


def test_signed_document_reply_crosses_request_boundary() -> None:
    captured: dict[str, object] = {}

    def send(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["idempotency_key"] = request.headers["Idempotency-Key"]
        captured["body"] = request.read().decode()
        return httpx.Response(
            200,
            json={
                "ok": True,
                "data": {"message_id": "sms-90210"},
                "error": None,
                "metadata": {"vendor": "auto"},
            },
        )

    client = InfraiSMS(api_key="test-key", transport=httpx.MockTransport(send))
    service.dependency_overrides[sms_client] = lambda: client
    try:
        response = TestClient(service).post(
            "/inbound-sms",
            json={
                "event_id": "evt-signed-7",
                "from_number": "+14155550142",
                "body": "SEND COPY",
                "matter_reference": "MAT-204",
                "stage": "signed",
                "signed_document_url": "https://documents.example/MAT-204/signed",
            },
        )
    finally:
        service.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "event_id": "evt-signed-7",
        "action": "signed_document_delivery",
        "outbound_message_id": "sms-90210",
    }
    assert captured["method"] == "POST"
    assert captured["idempotency_key"] == "inbound-reply:evt-signed-7"
    assert json.loads(str(captured["body"])) == {
        "to": "+14155550142",
        "body": "Matter MAT-204: your signed document is ready: https://documents.example/MAT-204/signed",
    }
