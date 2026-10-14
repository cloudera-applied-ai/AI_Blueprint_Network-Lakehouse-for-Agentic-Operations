"""Edge staging: local fallback + S3 (botocore Stubber, no network)."""
import tempfile

from app.edge import staging, synthesizer
from app.models import ClouderaServicesModel


def _make_pcap() -> str:
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pcap")
    tmp.close()
    synthesizer.generate("port_scan", tmp.name, seed=1)
    return tmp.name


def test_backend_local_without_config(pcap_db):
    assert staging.is_s3_configured() is False
    assert staging.backend_name() == "local"


def test_local_roundtrip(pcap_db):
    src = _make_pcap()
    staged = staging.stage_pcap(src, "edge-abc123")
    assert staged.backend == "local"
    assert staged.key.endswith("edge-abc123.pcap")

    assert staged.key in staging.list_incoming()
    assert staging.execution_id_from_key(staged.key) == "edge-abc123"

    with tempfile.NamedTemporaryFile(suffix=".pcap") as dest:
        staging.fetch(staged.key, dest.name)
        with open(dest.name, "rb") as fh:
            assert len(fh.read()) > 0

    staging.mark_processed(staged.key)
    assert staged.key not in staging.list_incoming()


def _configure_s3(pcap_db):
    pcap_db.add(ClouderaServicesModel(
        id=1, config_key="default",
        s3_staging_enabled=True, s3_staging_bucket="pcap-edge",
        s3_staging_region="us-east-1", s3_staging_prefix="edge-captures",
        s3_staging_access_key="AKIA_TEST", s3_staging_secret_key="secret",
    ))
    pcap_db.commit()


def test_backend_switches_to_s3(pcap_db):
    _configure_s3(pcap_db)
    assert staging.is_s3_configured() is True
    assert staging.backend_name() == "s3"


def test_test_s3_head_bucket_ok(pcap_db, monkeypatch):
    from botocore.stub import Stubber

    _configure_s3(pcap_db)
    client, bucket = staging._client()
    stubber = Stubber(client)
    stubber.add_response("head_bucket", {}, {"Bucket": bucket})
    monkeypatch.setattr(staging, "_client", lambda: (client, bucket))
    with stubber:
        result = staging.test_s3()
    assert result["ok"] is True


def test_stage_pcap_uploads_to_s3(pcap_db, monkeypatch):
    _configure_s3(pcap_db)
    client, bucket = staging._client()
    key = "edge-captures/incoming/edge-xyz.pcap"
    monkeypatch.setattr(staging, "_client", lambda: (client, bucket))
    called = {}
    monkeypatch.setattr(client, "upload_file", lambda p, b, k: called.update(bucket=b, key=k))
    with tempfile.NamedTemporaryFile(suffix=".pcap") as tmp:
        tmp.write(b"\xd4\xc3\xb2\xa1")
        tmp.flush()
        staged = staging.stage_pcap(tmp.name, "edge-xyz")
    assert staged.backend == "s3"
    assert staged.uri == f"s3://{bucket}/{key}"
    assert called == {"bucket": bucket, "key": key}
