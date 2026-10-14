"""PCAP staging — S3-compatible object storage with local-disk fallback.

S3 config is read from the `cloudera_services` row (the same panel that holds
the Iceberg warehouse), so the edge flow stages to whatever object store the
lakehouse uses. When no bucket is configured, captures stage on local disk so
the demo always runs. The poller lists `<prefix>/incoming/`, fetches, analyzes,
then moves objects to `<prefix>/processed/`.
"""
from __future__ import annotations

import logging
import os
import shutil
from dataclasses import dataclass
from pathlib import Path

from ..database import SessionLocal
from ..models import ClouderaServicesModel

log = logging.getLogger(__name__)

# Local fallback root (overridable in tests via EDGE_STAGING_DIR).
_LOCAL_ROOT = Path(
    os.environ.get("EDGE_STAGING_DIR")
    or (Path(__file__).resolve().parent.parent.parent / "data" / "edge_staging")
)


@dataclass
class Staged:
    backend: str  # "s3" | "local"
    uri: str
    key: str


def _s3_config() -> dict:
    """Read S3 staging config from the cloudera_services row."""
    try:
        with SessionLocal() as db:
            row = db.get(ClouderaServicesModel, 1)
            if row is None:
                row = (
                    db.query(ClouderaServicesModel)
                    .filter(ClouderaServicesModel.config_key == "default")
                    .first()
                )
            if row is None:
                return {}
            return {
                "endpoint_url": row.s3_staging_endpoint_url or "",
                "access_key": row.s3_staging_access_key or "",
                "secret_key": row.s3_staging_secret_key or "",
                "bucket": row.s3_staging_bucket or "",
                "region": row.s3_staging_region or "",
                "prefix": (row.s3_staging_prefix or "edge-captures").strip("/") or "edge-captures",
            }
    except Exception:  # noqa: BLE001 — DB unreachable => local fallback
        return {}


def is_s3_configured() -> bool:
    return bool(_s3_config().get("bucket"))


def backend_name() -> str:
    return "s3" if is_s3_configured() else "local"


def _prefix() -> str:
    return _s3_config().get("prefix", "edge-captures") or "edge-captures"


def _incoming_key(execution_id: str) -> str:
    return f"{_prefix()}/incoming/{execution_id}.pcap"


def _processed_key(key: str) -> str:
    return key.replace("/incoming/", "/processed/", 1)


def _client():
    import boto3
    from botocore.config import Config

    cfg = _s3_config()
    kwargs: dict = {}
    if cfg.get("endpoint_url"):
        kwargs["endpoint_url"] = cfg["endpoint_url"]
        kwargs["config"] = Config(s3={"addressing_style": "path"})  # MinIO/Ozone
    if cfg.get("access_key") and cfg.get("secret_key"):
        kwargs["aws_access_key_id"] = cfg["access_key"]
        kwargs["aws_secret_access_key"] = cfg["secret_key"]
    if cfg.get("region"):
        kwargs["region_name"] = cfg["region"]
    return boto3.client("s3", **kwargs), cfg["bucket"]


def test_s3() -> dict:
    if not is_s3_configured():
        return {"ok": False, "message": "No S3 bucket configured (using local-disk staging)."}
    try:
        client, bucket = _client()
        client.head_bucket(Bucket=bucket)
        return {"ok": True, "message": f"Reached bucket '{bucket}'."}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "message": str(exc)}


def stage_pcap(local_path: str, execution_id: str) -> Staged:
    key = _incoming_key(execution_id)
    if is_s3_configured():
        client, bucket = _client()
        client.upload_file(local_path, bucket, key)
        return Staged(backend="s3", uri=f"s3://{bucket}/{key}", key=key)
    dest = _LOCAL_ROOT / key
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(local_path, dest)
    return Staged(backend="local", uri=str(dest), key=key)


def list_incoming() -> list[str]:
    prefix = f"{_prefix()}/incoming/"
    if is_s3_configured():
        client, bucket = _client()
        resp = client.list_objects_v2(Bucket=bucket, Prefix=prefix)
        return [o["Key"] for o in resp.get("Contents", []) if o["Key"].endswith(".pcap")]
    incoming = _LOCAL_ROOT / prefix
    if not incoming.exists():
        return []
    return [f"{prefix}{p.name}" for p in incoming.glob("*.pcap")]


def fetch(key: str, dest_path: str) -> str:
    if is_s3_configured():
        client, bucket = _client()
        Path(dest_path).parent.mkdir(parents=True, exist_ok=True)
        client.download_file(bucket, key, dest_path)
        return dest_path
    src = _LOCAL_ROOT / key
    Path(dest_path).parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dest_path)
    return dest_path


def mark_processed(key: str) -> None:
    dest_key = _processed_key(key)
    if is_s3_configured():
        client, bucket = _client()
        client.copy_object(Bucket=bucket, CopySource={"Bucket": bucket, "Key": key}, Key=dest_key)
        client.delete_object(Bucket=bucket, Key=key)
        return
    src = _LOCAL_ROOT / key
    dest = _LOCAL_ROOT / dest_key
    dest.parent.mkdir(parents=True, exist_ok=True)
    if src.exists():
        shutil.move(str(src), str(dest))


def execution_id_from_key(key: str) -> str:
    return Path(key).stem


def status() -> dict:
    cfg = _s3_config()
    return {
        "backend": backend_name(),
        "configured": is_s3_configured(),
        "bucket": cfg.get("bucket") or None,
        "endpoint_url": cfg.get("endpoint_url") or None,
        "incoming_count": len(list_incoming()),
        "local_root": str(_LOCAL_ROOT) if not is_s3_configured() else None,
    }
