"""Model names are never hard-coded: every provider path requires the
configured `model_name` and refuses to substitute a default."""
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.routes.llm import _prepare_llm_request


def _cfg(provider, model_name, **kw):
    base = dict(provider=provider, endpoint_url="http://llm.local/v1", api_key="k",
                jwt_token=None, temperature=0.2, max_tokens=100, model_name=model_name)
    base.update(kw)
    return SimpleNamespace(**base)


@pytest.mark.parametrize("provider", ["openai", "anthropic", "ollama", "cloudera", "custom"])
@pytest.mark.parametrize("missing", [None, "", "   "])
def test_missing_model_name_is_a_clear_400(provider, missing):
    with pytest.raises(HTTPException) as exc:
        _prepare_llm_request(_cfg(provider, missing), [{"role": "user", "content": "hi"}])
    assert exc.value.status_code == 400
    assert "Settings" in exc.value.detail


@pytest.mark.parametrize("provider", ["openai", "anthropic", "ollama", "cloudera", "custom"])
def test_configured_model_name_is_sent_verbatim(provider):
    _, _, payload = _prepare_llm_request(_cfg(provider, "foundation-sec-8b"),
                                         [{"role": "user", "content": "hi"}])
    assert payload["model"] == "foundation-sec-8b"
