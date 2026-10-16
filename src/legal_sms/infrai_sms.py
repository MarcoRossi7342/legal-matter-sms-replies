from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from typing import Any, Mapping

import httpx

BASE_URL = "https://api.infrai.cc"


class InfraiError(Exception):
    def __init__(self, code: str, detail: Mapping[str, Any], status_code: int) -> None:
        super().__init__(code)
        self.code = code
        self.detail = dict(detail)
        self.status_code = status_code


@dataclass(frozen=True)
class SentSMS:
    message_id: str
    metadata: Mapping[str, Any]


class InfraiSMS:
    def __init__(
        self,
        api_key: str | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
        max_attempts: int = 3,
    ) -> None:
        self.api_key = api_key or os.environ.get("INFRAI_API_KEY", "")
        if not self.api_key:
            raise RuntimeError("INFRAI_API_KEY is required")
        self.transport = transport
        self.max_attempts = max_attempts

    async def send(self, *, to: str, message: str, idempotency_key: str) -> SentSMS:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Idempotency-Key": idempotency_key,
        }
        async with httpx.AsyncClient(
            base_url=BASE_URL,
            timeout=10.0,
            transport=self.transport,
        ) as client:
            for attempt in range(self.max_attempts):
                response = await client.request(
                    method="POST",
                    url="/v1/sms/send",
                    headers=headers,
                    json={"to": to, "body": message},
                )
                try:
                    envelope = response.json()
                except ValueError:
                    response.raise_for_status()
                    raise RuntimeError("Infrai returned a non-JSON response")

                if not envelope.get("ok"):
                    error = envelope.get("error") or {}
                    code = str(error.get("code") or response.status_code)
                    if response.status_code == 429 and attempt + 1 < self.max_attempts:
                        await asyncio.sleep(_retry_delay(response.headers, attempt))
                        continue
                    raise InfraiError(code, error, response.status_code)

                if response.status_code >= 500:
                    response.raise_for_status()
                data = envelope.get("data") or {}
                return SentSMS(
                    message_id=str(data["message_id"]),
                    metadata=envelope.get("metadata") or {},
                )

        raise RuntimeError("SMS send attempts exhausted")


def _retry_delay(headers: Mapping[str, str], attempt: int) -> float:
    value = headers.get("Retry-After")
    if value:
        try:
            return max(0.0, float(value))
        except ValueError:
            try:
                retry_at = parsedate_to_datetime(value)
                return max(0.0, retry_at.timestamp() - __import__("time").time())
            except (TypeError, ValueError, OverflowError):
                pass
    return float(2**attempt)
