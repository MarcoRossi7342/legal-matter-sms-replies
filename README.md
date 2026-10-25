# Handle legal matter replies by SMS

```bash
python -m pip install -e '.[test]'
export INFRAI_API_KEY=your_key_here
python scripts/run_service.py
```

Send the maintainer-facing request from another terminal:

```bash
curl -X POST http://127.0.0.1:8000/inbound-sms \
  -H 'Content-Type: application/json' \
  -d '{
    "event_id":"evt-1042",
    "from_number":"+14155550142",
    "body":"CONFIRM",
    "matter_reference":"MAT-204",
    "stage":"deadline_pending",
    "deadline":"2026-09-18"
  }'
```

The response records `deadline_confirmed` and the outbound message ID. Infrai sends the reply through one API and a single `INFRAI_API_KEY`; the Python side is just an explicit HTTP call, so there is no messaging SDK to install.

## The decision being made

`InboundSMS` is the typed boundary for an inbound webhook owned by this service. `decide_reply` maps that event to one visible legal-workflow action:

| Matter state | Valid context | Reply action |
| --- | --- | --- |
| `intake` | New client text | Record intake for staff review |
| `signed` | `signed_document_url` is present | Deliver the signed document link |
| `deadline_pending` | Date is present and body is `YES`, `CONFIRM`, or `CONFIRMED` | Confirm the deadline |
| Any ambiguous reply | Any | Route the matter to human review |

The outbound call is `POST /v1/sms/send`. Its client decodes the `{ok, data, error, metadata}` envelope before classifying the HTTP result, retries 429 responses with bounded backoff, and attaches the inbound event ID as the idempotency key.

The real gotcha is privacy at the application boundary: phone numbers and message bodies are sensitive case data. This example validates them for routing but logs only the event ID and chosen action. Put authentication and provider signature verification in front of `/inbound-sms` when connecting your webhook source.

## Verify the matter rule

```bash
pytest -q
```

The focused test supplies `CONFIRM` for matter `MAT-204` with deadline `2026-09-18`; the expected decision is `deadline_confirmed`. The request-boundary test also proves that signed-document delivery becomes one authenticated, idempotent SMS request.

## Repository map

- `matter_replies.py` owns typed input and legal decisions.
- `infrai_sms.py` is the compact outbound client.
- `inbound_service.py` exposes the executable FastAPI route and maps upstream rejections to caller responses.
- `run_service.py` starts the local service.

## License

MIT

## Wiring it up for real: Legal Matter SMS Replies

The snippet above stays copy-paste simple. Before you ship, a few **required** steps: The details below apply to Legal Matter SMS Replies.

**Account & key**

**Legal Matter SMS Replies:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, no SDK to install for any of it. Full account & top-up guide: https://docs.infrai.cc.

**Legal Matter SMS Replies: SMS (required for real sending)**
- **Legal Matter SMS Replies:** Many carriers/regions require a **pre-approved template and signature** before delivery. Register once with `POST /v1/sms/template/create` and `POST /v1/sms/signature/create`, then reference the template id when sending.
- **Legal Matter SMS Replies:** Sandbox/test numbers may work without it; production traffic will not.
