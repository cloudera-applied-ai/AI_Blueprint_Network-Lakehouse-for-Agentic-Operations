"""Two-model routing: analyst (security model) vs writer (generalist)."""
from app.database import SessionLocal
from app.models import LLMConfigModel
from app.pcap import llm_bridge


def _set_config(writer: str | None, analyst_provider: str = "ollama", jwt: str | None = None, **writer_fields):
    with SessionLocal() as db:
        row = db.get(LLMConfigModel, 1)
        if row is None:
            row = LLMConfigModel(id=1, config_key="default")
            db.add(row)
        row.provider = analyst_provider
        row.endpoint_url = "http://llm:11434/v1"
        row.api_key = "analyst-key" if not jwt else None
        row.jwt_token = jwt
        row.model_name = "foundation-sec:8b"
        row.writer_model_name = writer
        row.writer_provider = writer_fields.get("provider")
        row.writer_endpoint_url = writer_fields.get("endpoint")
        row.writer_api_key = writer_fields.get("api_key")
        row.enabled = True
        db.commit()


def _capture(monkeypatch) -> dict:
    """Returns a dict populated (in place) with the submitted request when chat() runs."""
    captured: dict = {}

    def fake_submit(**kwargs):
        captured["payload"] = kwargs["payload"]
        captured["api_url"] = kwargs["api_url"]
        captured["headers"] = kwargs["headers"]
        return "job-1"

    monkeypatch.setattr(llm_bridge.llm_queue, "submit_and_process_parallel", fake_submit)
    monkeypatch.setattr(
        llm_bridge.llm_queue,
        "wait_for_job_outcome",
        lambda job_id, timeout=180.0: ({"choices": [{"message": {"content": "ok"}}]}, None),
    )
    return captured


def test_writer_enabled_reflects_config(pcap_db):
    _set_config(writer=None)
    assert llm_bridge.writer_enabled() is False
    _set_config(writer="qwen2.5")
    assert llm_bridge.writer_enabled() is True


def test_analyst_uses_security_model(pcap_db, monkeypatch):
    _set_config(writer="qwen2.5")
    cap = _capture(monkeypatch)
    llm_bridge.chat("sys", [{"role": "user", "content": "hi"}], role="analyst")
    assert cap["payload"]["model"] == "foundation-sec:8b"
    assert cap["api_url"] == "http://llm:11434/v1/chat/completions"


def test_writer_uses_generalist_model_same_endpoint(pcap_db, monkeypatch):
    _set_config(writer="qwen2.5")  # no writer endpoint => analyst endpoint
    cap = _capture(monkeypatch)
    llm_bridge.chat("sys", [{"role": "user", "content": "hi"}], role="writer")
    assert cap["payload"]["model"] == "qwen2.5"
    assert cap["api_url"] == "http://llm:11434/v1/chat/completions"


def test_writer_uses_separate_endpoint_and_key(pcap_db, monkeypatch):
    _set_config(
        writer="qwen2.5",
        provider="cloudera",
        endpoint="https://qwen-host/v1",
        api_key="writer-key",
    )
    cap = _capture(monkeypatch)
    llm_bridge.chat("sys", [{"role": "user", "content": "hi"}], role="writer")
    assert cap["payload"]["model"] == "qwen2.5"
    assert cap["api_url"] == "https://qwen-host/v1/chat/completions"
    assert cap["headers"].get("Authorization") == "Bearer writer-key"
    # The analyst still uses its own endpoint on the same config.
    cap2 = _capture(monkeypatch)
    llm_bridge.chat("sys", [{"role": "user", "content": "hi"}], role="analyst")
    assert cap2["api_url"] == "http://llm:11434/v1/chat/completions"


def test_writer_falls_back_to_single_model(pcap_db, monkeypatch):
    _set_config(writer=None)
    cap = _capture(monkeypatch)
    llm_bridge.chat("sys", [{"role": "user", "content": "hi"}], role="writer")
    # No writer configured → writer role still uses the single model.
    assert cap["payload"]["model"] == "foundation-sec:8b"


def test_writer_separate_endpoint_no_key_falls_back_to_jwt(pcap_db, monkeypatch):
    """A separate-endpoint writer with no key must not go out unauthenticated:
    it reuses the analyst JWT (valid across CAI endpoints in one environment)."""
    _set_config(
        writer="qwen2.5",
        analyst_provider="cloudera",
        jwt="analyst-jwt",
        provider="cloudera",
        endpoint="https://qwen-host/v1",
    )
    cap = _capture(monkeypatch)
    llm_bridge.chat("sys", [{"role": "user", "content": "hi"}], role="writer")
    assert cap["api_url"] == "https://qwen-host/v1/chat/completions"
    assert cap["headers"].get("Authorization") == "Bearer analyst-jwt"


def test_writer_partial_config_ignored_without_endpoint(pcap_db, monkeypatch):
    """Writer Provider/Key without a Writer Endpoint must not produce a mixed
    config: same-endpoint mode inherits the analyst transport wholesale."""
    _set_config(
        writer="qwen2.5",
        analyst_provider="cloudera",
        jwt="analyst-jwt",
        provider="ollama",  # set, but endpoint is blank → ignored
        api_key="stray-key",  # ignored too
    )
    cap = _capture(monkeypatch)
    llm_bridge.chat("sys", [{"role": "user", "content": "hi"}], role="writer")
    assert cap["payload"]["model"] == "qwen2.5"
    assert cap["api_url"] == "http://llm:11434/v1/chat/completions"
    # Analyst transport (cloudera + JWT) is kept — auth is not dropped.
    assert cap["headers"].get("Authorization") == "Bearer analyst-jwt"


def test_chat_surfaces_real_queue_error(pcap_db, monkeypatch):
    """Failures must carry the queue's real error (HTTP status/body), not the
    generic 'timed out or failed' message."""
    _set_config(writer="qwen2.5")
    monkeypatch.setattr(
        llm_bridge.llm_queue, "submit_and_process_parallel", lambda **kw: "job-1"
    )
    monkeypatch.setattr(
        llm_bridge.llm_queue,
        "wait_for_job_outcome",
        lambda job_id, timeout=180.0: (None, "HTTP 401: invalid token"),
    )
    try:
        llm_bridge.chat("sys", [{"role": "user", "content": "hi"}], role="writer")
        assert False, "expected LLMError"
    except llm_bridge.LLMError as exc:
        assert "HTTP 401" in str(exc)


def test_config_save_preserves_stored_jwt(pcap_client):
    """Saving the settings form (which never round-trips jwt_token) must not
    wipe a JWT stored server-side — this used to break the analyst the moment
    a writer model was added and saved."""
    with SessionLocal() as db:
        row = db.get(LLMConfigModel, 1)
        if row is None:
            row = LLMConfigModel(id=1, config_key="default")
            db.add(row)
        row.provider = "cloudera"
        row.endpoint_url = "https://analyst-host/v1"
        row.jwt_token = "stored-jwt"
        row.model_name = "foundation-sec-8b"
        row.enabled = True
        db.commit()

    # The UI save: full form payload, jwt_token absent, writer model added.
    resp = pcap_client.post(
        "/api/v1/llm/config",
        json={
            "provider": "cloudera",
            "endpoint_url": "https://analyst-host/v1",
            "api_key": None,
            "model_name": "foundation-sec-8b",
            "writer_model_name": "qwen2.5",
            "writer_provider": None,
            "writer_endpoint_url": "http://qwen-host:11434/v1",
            "writer_api_key": None,
            "temperature": 0.7,
            "max_tokens": 2000,
            "enabled": True,
        },
    )
    assert resp.status_code == 200

    with SessionLocal() as db:
        row = db.get(LLMConfigModel, 1)
        assert row.jwt_token == "stored-jwt"  # not wiped
        assert row.writer_model_name == "qwen2.5"

    # Clearing the writer model with an explicit null does clear it.
    resp = pcap_client.post(
        "/api/v1/llm/config",
        json={"provider": "cloudera", "writer_model_name": None},
    )
    assert resp.status_code == 200
    with SessionLocal() as db:
        row = db.get(LLMConfigModel, 1)
        assert row.writer_model_name is None
        assert row.jwt_token == "stored-jwt"
