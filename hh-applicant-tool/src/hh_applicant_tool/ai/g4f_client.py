import io
import logging
import time
from dataclasses import KW_ONLY, dataclass, field
from threading import Lock

from .base import AIError

logger = logging.getLogger(__package__)


class G4FError(AIError):
    pass


@dataclass
class ChatG4F:
    api_key: str = ""

    _: KW_ONLY

    base_url: str = "g4f"
    model: str = "gpt-4o-mini"
    system_prompt: str | None = None
    timeout: float = 60.0
    max_retries: int = 5
    temperature: float = 0.0
    max_completion_tokens: int = 1000
    rate_limit: int = 40
    session: object = None

    _previous_request_time: float = field(default=0.0, init=False)
    _lock: Lock = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._lock = Lock()
        try:
            from g4f.client import Client  # noqa: F401
        except ImportError:
            raise G4FError(
                "Библиотека g4f не установлена. Установите: pip install -U g4f"
            )

    _PROVIDER_CACHE = None

    @classmethod
    def _get_provider(cls):
        if cls._PROVIDER_CACHE is None:
            from g4f.Provider.Perplexity import Perplexity
            cls._PROVIDER_CACHE = Perplexity
        return cls._PROVIDER_CACHE

    @property
    def _min_request_interval(self) -> float:
        return 60.0 / self.rate_limit if self.rate_limit > 0 else 0.0

    def _throttle(self) -> None:
        with self._lock:
            if self._previous_request_time > 0:
                delay = (
                    self._min_request_interval
                    - time.monotonic()
                    + self._previous_request_time
                )
                if delay > 0:
                    logger.debug("G4F throttle: wait %.2fs", delay)
                    time.sleep(delay)
            self._previous_request_time = time.monotonic()

    def _call(self, messages: list, image_data: bytes | None = None) -> str:
        from g4f.client import Client

        provider = self._get_provider()
        fallback_model = getattr(provider, "default_model", "auto")

        for attempt in range(self.max_retries + 1):
            self._throttle()
            if attempt == 0:
                models_to_try = [self.model]
            else:
                models_to_try = [self.model, fallback_model]

            for model_name in models_to_try:
                kwargs = {
                    "model": model_name,
                    "messages": messages,
                    "temperature": self.temperature,
                    "max_tokens": self.max_completion_tokens,
                    "web_search": False,
                }
                if image_data is not None:
                    kwargs["image"] = io.BytesIO(image_data)
                    kwargs["temperature"] = 0.0
                    kwargs["max_tokens"] = 20
                try:
                    resp = Client(provider=provider).chat.completions.create(**kwargs)
                    content = resp.choices[0].message.content
                    if content and content.strip():
                        return content.strip()
                except Exception as ex:
                    logger.debug("G4F model %s failed: %s", model_name, ex)

            delay = min(2 ** attempt, 15)
            logger.warning(
                "G4F attempt %d/%d failed, retry in %ds",
                attempt + 1,
                self.max_retries,
                delay,
            )
            if attempt < self.max_retries:
                time.sleep(delay)

        raise G4FError("G4F request failed after retries")

    def complete(self, message: str) -> str:
        messages = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        messages.append({"role": "user", "content": message})

        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("G4F запрос: %s", message)

        return self._call(messages)

    def solve_captcha(self, image_data: bytes) -> str:
        messages = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        messages.append(
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Распознай текст на изображении. Верни только результат распознавания.",
                    },
                ],
            }
        )

        logger.debug("G4F капча: %d bytes", len(image_data))

        return self._call(messages, image_data=image_data)
