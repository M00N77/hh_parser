import base64
import logging
import time
from dataclasses import KW_ONLY, dataclass, field
from threading import Lock

import requests

from .base import AIError

logger = logging.getLogger(__package__)


class AnthropicError(AIError):
    pass


@dataclass
class ChatAnthropic:
    api_key: str

    _: KW_ONLY

    base_url: str = "https://api.openmodel.ai/v1/messages"
    model: str = "claude-3-5-haiku-latest"
    system_prompt: str | None = None
    timeout: float = 30.0
    max_retries: int = 5
    temperature: float = 0.0
    max_completion_tokens: int = 1000
    rate_limit: int = 40
    anthropic_version: str = "2023-06-01"
    session: requests.Session | None = None

    _last_request: float = field(default=0.0, init=False)
    _lock: Lock = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if self.session is None:
            self.session = requests.Session()
        self._lock = Lock()

    def _headers(self) -> dict[str, str]:
        return {
            "x-api-key": self.api_key,
            "anthropic-version": self.anthropic_version,
            "content-type": "application/json",
        }

    @property
    def _min_request_interval(self) -> float:
        return 60.0 / self.rate_limit if self.rate_limit > 0 else 0.0

    def _throttled_post(self, payload: dict) -> requests.Response:
        with self._lock:
            if self._last_request > 0:
                delay = (
                    self._min_request_interval
                    - time.monotonic()
                    + self._last_request
                )
                if delay > 0:
                    logger.debug(
                        "Wait %.2fs before Anthropic request (%s)", delay, self.base_url
                    )
                    time.sleep(delay)
            try:
                return self.session.post(
                    self.base_url,
                    json=payload,
                    headers=self._headers(),
                    timeout=self.timeout,
                )
            finally:
                self._last_request = time.monotonic()

    def _post(self, payload: dict) -> dict:
        payload = payload.copy()
        if self.system_prompt:
            payload["system"] = self.system_prompt
        payload["model"] = self.model
        payload["max_tokens"] = self.max_completion_tokens
        payload["temperature"] = self.temperature

        for attempt in range(self.max_retries + 1):
            try:
                resp = self._throttled_post(payload)
            except requests.exceptions.RequestException as ex:
                logger.warning(
                    "Anthropic request failed (attempt %d/%d): %s",
                    attempt + 1,
                    self.max_retries + 1,
                    ex,
                )
                if attempt < self.max_retries:
                    time.sleep(min(2 ** attempt, 15))
                continue

            if resp.status_code == 429:
                if attempt >= self.max_retries:
                    raise AnthropicError(
                        f"Anthropic endpoint ({self.base_url}) rate limit exceeded"
                    )
                retry_after = resp.headers.get("retry-after")
                delay = (
                    float(retry_after)
                    if retry_after
                    else min(2 ** attempt, 15)
                )
                logger.warning(
                    "Anthropic endpoint (%s) returned 429, retry in %.2fs",
                    self.base_url,
                    delay,
                )
                time.sleep(delay)
                continue

            if resp.status_code >= 400:
                if 500 <= resp.status_code < 600:
                    if attempt < self.max_retries:
                        time.sleep(min(2 ** attempt, 15))
                    continue
                raise AnthropicError(resp.text[:300])

            return resp.json()

        raise AnthropicError(
            f"Anthropic endpoint ({self.base_url}) request failed after retries"
        )

    @staticmethod
    def _extract_text(data: dict) -> str:
        parts = []
        for block in data.get("content", []):
            if block.get("type") == "text":
                parts.append(block.get("text", ""))
        return "".join(parts).strip()

    def complete(self, message: str) -> str:
        payload = {
            "messages": [{"role": "user", "content": message}],
        }
        data = self._post(payload)
        text = self._extract_text(data)
        if not text:
            raise AnthropicError("Empty response from Anthropic API")
        return text

    def solve_captcha(self, image_data: bytes) -> str:
        image_base64 = base64.b64encode(image_data).decode("utf-8")

        content = [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": image_base64,
                },
            },
            {
                "type": "text",
                "text": (
                    self.system_prompt
                    or "Что написано на картинке? Ответь только текстом."
                ),
            },
        ]

        payload = {
            "messages": [{"role": "user", "content": content}],
        }

        logger.debug("Anthropic captcha request: %d bytes", len(image_data))

        data = self._post(payload)
        text = self._extract_text(data)
        return text if text else ""
