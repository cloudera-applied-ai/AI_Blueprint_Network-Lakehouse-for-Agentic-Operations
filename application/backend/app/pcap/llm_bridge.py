"""Bridge the ported agents/chat/report onto this repo's LLM queue.

The standalone app called an SDK-based `chat(system, messages, ...)`. Here we
route the same signature through the datalakehouse `llm_queue` +
`routes.llm._prepare_llm_request` (single shared `LLMConfigModel`), so the pcap
agents use the exact provider handling and rate-limited queue as the rest of
the NOC app.
"""
from __future__ import annotations

import logging
from typing import Iterable, Literal

from ..database import SessionLocal
from ..llm_queue import llm_queue
from ..routes.llm import _get_llm_config, _prepare_llm_request

log = logging.getLogger(__name__)

Role = Literal["analyst", "writer"]


class LLMError(RuntimeError):
    pass


class _EffectiveConfig:
    """A config view for the writer role, shaped like LLMConfigModel so it can
    be handed straight to `_prepare_llm_request`.

    Two coherent modes (all-or-nothing, no per-field mixing):

    - Writer Endpoint blank => same-endpoint mode: the analyst's transport
      (provider/endpoint/api_key/jwt) is inherited wholesale; only the model
      name differs. Writer Provider / Writer API Key are ignored so a partial
      writer block can't produce an unauthenticated or misrouted request.
    - Writer Endpoint set => separate-endpoint mode: the writer block is used.
      If no Writer API Key was given, fall back to the analyst's JWT rather
      than sending an unauthenticated request — CDP JWTs are valid across
      Cloudera AI Inference endpoints in the same environment. (For ollama no
      auth is needed and `_prepare_llm_request` sends none.)
    """

    def __init__(self, c):
        self.writer_model_name = getattr(c, "writer_model_name", None)
        self.model_name = self.writer_model_name or c.model_name
        self.temperature = c.temperature
        self.max_tokens = c.max_tokens

        writer_endpoint = getattr(c, "writer_endpoint_url", None)
        if not writer_endpoint:
            # Same-endpoint mode: inherit the analyst's transport wholesale.
            self.provider = c.provider
            self.endpoint_url = c.endpoint_url
            self.api_key = c.api_key
            self.jwt_token = getattr(c, "jwt_token", None)
        else:
            self.provider = getattr(c, "writer_provider", None) or c.provider
            self.endpoint_url = writer_endpoint
            self.api_key = getattr(c, "writer_api_key", None)
            self.jwt_token = None if self.api_key else getattr(c, "jwt_token", None)


def writer_enabled() -> bool:
    """True when a separate generalist writer model is configured.

    Two-model mode pairs a security analyst model (e.g. Cisco Foundation-Sec-8B,
    which extracts structured findings) with a generalist writer (e.g. Qwen,
    which produces the analysis prose, reports, and chat). Both are served from
    the same provider/endpoint; only the model name differs. Blank writer model
    => single-model mode (the analyst produces prose too).
    """
    try:
        with SessionLocal() as db:
            config = _get_llm_config(db)
            return bool(config and getattr(config, "writer_model_name", None))
    except Exception:  # noqa: BLE001
        return False


def _extract_content(result: dict) -> str:
    if not isinstance(result, dict):
        return ""
    choices = result.get("choices")
    if isinstance(choices, list) and choices:
        choice = choices[0]
        if isinstance(choice, dict):
            msg = choice.get("message")
            if isinstance(msg, dict) and msg.get("content"):
                return msg["content"]
            if choice.get("text"):
                return choice["text"]
    content = result.get("content")
    if isinstance(content, list):  # Anthropic
        return "".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")
    if isinstance(content, str):
        return content
    return ""


def chat(
    system: str,
    messages: Iterable[dict[str, str]],
    *,
    max_tokens: int = 2000,
    temperature: float = 0.3,
    json_mode: bool = False,
    role: Role = "analyst",  # "writer" routes to the writer model when one is configured
    priority: int = 0,
    label: str = "",
) -> str:
    """Send a chat completion through the shared queue. Raises LLMError on failure."""
    msgs = list(messages)
    sys_text = system
    if json_mode:
        sys_text = (
            system
            + "\n\nYou MUST respond with a single JSON object and nothing else. "
            "Do not wrap it in code fences. Do not write any prose outside the JSON."
        )

    with SessionLocal() as db:
        config = _get_llm_config(db)
        if not config or not config.endpoint_url or not getattr(config, "enabled", True):
            raise LLMError("LLM is not configured or not enabled. Set it up in Settings.")
        full_messages = [{"role": "system", "content": sys_text}] + [
            {"role": m["role"], "content": m["content"]} for m in msgs if m.get("role") != "system"
        ]
        # Two-model routing: the writer role uses the generalist model — on its
        # own provider/endpoint/key when configured, else the analyst's. The
        # analyst always uses the security model on the primary endpoint.
        effective = (
            _EffectiveConfig(config)
            if role == "writer" and getattr(config, "writer_model_name", None)
            else config
        )
        try:
            api_url, headers, payload = _prepare_llm_request(effective, full_messages)
        except Exception as exc:  # noqa: BLE001 — HTTPException etc. outside a request
            raise LLMError(str(getattr(exc, "detail", exc))) from exc
        provider = effective.provider.lower()

    # Per-call decoding overrides
    payload["max_tokens"] = max_tokens
    payload["temperature"] = temperature

    job_id = llm_queue.submit_and_process_parallel(
        messages=full_messages,
        provider=provider,
        api_url=api_url,
        headers=headers,
        payload=payload,
        priority=priority or 5,
    )
    # Wait budget must cover queue depth, not just one request: in two-model
    # mode a full analysis is 2 calls per agent through a small worker pool,
    # so a job can sit queued behind several full-length requests before its
    # own starts.
    wait_budget = llm_queue.request_timeout * 4 + 60
    result, error = llm_queue.wait_for_job_outcome(job_id, timeout=wait_budget)
    if error:
        raise LLMError(f"LLM request failed ({label or role}): {error}")
    if result is None:
        raise LLMError(f"LLM request returned no result ({label or role}).")
    if isinstance(result, dict) and result.get("error"):
        raise LLMError(str(result["error"]))
    return _extract_content(result)


def test_connection(role: Role = "analyst") -> dict:
    """Probe the configured LLM. role="writer" exercises the writer model's
    provider/endpoint/auth so a broken writer config is caught in Settings
    instead of mid-analysis."""
    if role == "writer" and not writer_enabled():
        return {
            "ok": False,
            "message": "No writer model configured — the writer role would use the analyst model.",
        }
    try:
        reply = chat(
            system="You are a connectivity probe. Respond with the single word: ok.",
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=16,
            temperature=0.0,
            role=role,
            label=f"test:{role}",
        )
        return {"ok": True, "message": (reply or "").strip() or "(empty response)"}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "message": str(exc)}
