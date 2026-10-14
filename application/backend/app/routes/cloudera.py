"""Cloudera services configuration and status endpoints"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from ..config import settings
from ..database import get_db
from ..models import ClouderaServicesModel
from ..schemas import ClouderaServices, ClouderaServicesCreate, ClouderaServicesUpdate
from . import safe_error_response, logger

router = APIRouter(prefix=settings.API_V1_STR, tags=["cloudera"])


def _get_cloudera_config(db: Session):
    """Helper to get Cloudera config"""
    config = db.execute(select(ClouderaServicesModel).where(ClouderaServicesModel.id == 1)).scalar_one_or_none()
    if not config:
        config = db.execute(select(ClouderaServicesModel).where(ClouderaServicesModel.config_key == "default")).scalar_one_or_none()
    return config


@router.post("/cloudera/services/test/s3")
def test_s3_staging():
    """Probe the configured S3 staging bucket (head_bucket). Local fallback ⇒ ok=False."""
    from ..edge import staging
    return staging.test_s3()


@router.get("/cloudera/services", response_model=ClouderaServices)
def get_cloudera_services(db: Session = Depends(get_db)):
    """Get Cloudera services configuration"""
    services = _get_cloudera_config(db)
    if not services:
        raise HTTPException(status_code=404, detail="Cloudera services not configured. Create configuration first.")
    return services


@router.post("/cloudera/services", response_model=ClouderaServices)
def create_or_update_cloudera_services(services_data: ClouderaServicesCreate, db: Session = Depends(get_db)):
    """Create or update Cloudera services configuration"""
    try:
        existing = _get_cloudera_config(db)
        if existing:
            for key, value in services_data.model_dump().items():
                setattr(existing, key, value)
            existing.config_key = "default"
            db.commit()
            db.refresh(existing)
            return existing
        else:
            new_config = ClouderaServicesModel(id=1, config_key="default", **services_data.model_dump())
            db.add(new_config)
            db.commit()
            db.refresh(new_config)
            return new_config
    except Exception as e:
        db.rollback()
        if "Duplicate key" in str(e) or "UNIQUE constraint" in str(e):
            try:
                db.rollback()
                existing = _get_cloudera_config(db)
                if existing:
                    for key, value in services_data.model_dump().items():
                        setattr(existing, key, value)
                    existing.config_key = "default"
                    db.commit()
                    db.refresh(existing)
                    return existing
            except Exception as retry_error:
                db.rollback()
                raise HTTPException(status_code=500, detail=safe_error_response(retry_error, "Cloudera services save"))
        raise HTTPException(status_code=500, detail=safe_error_response(e, "Cloudera services creation"))


@router.patch("/cloudera/services", response_model=ClouderaServices)
def update_cloudera_services(services_data: ClouderaServicesUpdate, db: Session = Depends(get_db)):
    """Partially update Cloudera services configuration"""
    try:
        config = _get_cloudera_config(db)
        if not config:
            raise HTTPException(status_code=404, detail="Cloudera services not configured.")
        update_data = services_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(config, key, value)
        db.commit()
        db.refresh(config)
        return config
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=safe_error_response(e, "Cloudera services update"))


@router.get("/cloudera/services/status")
def get_cloudera_services_status(db: Session = Depends(get_db)):
    """Get status of all Cloudera services"""
    config = _get_cloudera_config(db)
    if not config:
        return {"configured": False, "services": []}

    services = [
        {"service": "nifi", "name": "Apache NiFi", "enabled": config.nifi_enabled, "status": config.nifi_status, "url": config.nifi_url},
        {"service": "kafka", "name": "Apache Kafka", "enabled": config.kafka_enabled, "status": config.kafka_status, "url": config.kafka_bootstrap_servers},
        {"service": "spark", "name": "Apache Spark", "enabled": config.spark_enabled, "status": config.spark_status, "url": config.spark_master_url},
        {"service": "kudu", "name": "Apache Kudu", "enabled": config.kudu_enabled, "status": config.kudu_status, "url": config.kudu_master_addresses},
        {"service": "iceberg", "name": "Apache Iceberg", "enabled": config.iceberg_enabled, "status": config.iceberg_status, "url": config.iceberg_catalog_url},
        {"service": "atlas", "name": "Apache Atlas", "enabled": config.atlas_enabled, "status": config.atlas_status, "url": config.atlas_url},
        {"service": "airflow", "name": "Apache Airflow", "enabled": config.airflow_enabled, "status": config.airflow_status, "url": config.airflow_url},
        {"service": "cml", "name": "Cloudera ML", "enabled": config.cml_enabled, "status": config.cml_status, "url": config.cml_workspace_url},
        {"service": "cdw", "name": "Cloudera Data Warehouse", "enabled": config.cdw_enabled, "status": config.cdw_status, "url": config.cdw_jdbc_url},
    ]

    return {
        "configured": True,
        "services": services,
        "summary": {
            "total": len(services),
            "enabled": sum(1 for s in services if s["enabled"]),
            "connected": sum(1 for s in services if s["status"] == "connected"),
        }
    }


@router.post("/cloudera/services/test/{service_name}")
async def test_cloudera_service_connection(service_name: str, db: Session = Depends(get_db)):
    """Test connection to a specific Cloudera service"""
    import httpx

    from ..net import ssl_context

    config = _get_cloudera_config(db)
    if not config:
        raise HTTPException(status_code=404, detail="Cloudera services not configured")

    service_map = {
        "nifi": ("nifi_url", "nifi_enabled", "nifi_status"),
        "kafka": ("kafka_bootstrap_servers", "kafka_enabled", "kafka_status"),
        "spark": ("spark_master_url", "spark_enabled", "spark_status"),
        "kudu": ("kudu_master_addresses", "kudu_enabled", "kudu_status"),
        "iceberg": ("iceberg_catalog_url", "iceberg_enabled", "iceberg_status"),
        "atlas": ("atlas_url", "atlas_enabled", "atlas_status"),
        "airflow": ("airflow_url", "airflow_enabled", "airflow_status"),
        "cml": ("cml_workspace_url", "cml_enabled", "cml_status"),
        "cdw": ("cdw_jdbc_url", "cdw_enabled", "cdw_status"),
    }

    if service_name not in service_map:
        raise HTTPException(status_code=400, detail=f"Unknown service: {service_name}")

    url_field, enabled_field, status_field = service_map[service_name]
    url = getattr(config, url_field)
    enabled = getattr(config, enabled_field)

    if not enabled:
        return {"service": service_name, "status": "disabled", "message": "Service is not enabled"}
    if not url:
        setattr(config, status_field, "error")
        db.commit()
        return {"service": service_name, "status": "error", "message": "No URL configured"}

    try:
        if service_name in ["nifi", "atlas", "airflow", "cml"]:
            async with httpx.AsyncClient(timeout=10.0, verify=ssl_context()) as client:
                health_endpoints = {
                    "nifi": "/nifi-api/system-diagnostics",
                    "atlas": "/api/atlas/admin/status",
                    "airflow": "/health",
                    "cml": "/api/v1/projects",
                }
                endpoint = health_endpoints.get(service_name, "/health")
                test_url = url.rstrip('/') + endpoint

                headers = {}
                if service_name == "atlas":
                    username, password = config.atlas_username, config.atlas_password
                    if username and password:
                        import base64
                        headers["Authorization"] = f"Basic {base64.b64encode(f'{username}:{password}'.encode()).decode()}"
                elif service_name == "airflow":
                    username, password = config.airflow_username, config.airflow_password
                    if username and password:
                        import base64
                        headers["Authorization"] = f"Basic {base64.b64encode(f'{username}:{password}'.encode()).decode()}"
                elif service_name == "cml":
                    if config.cml_api_key:
                        headers["Authorization"] = f"Bearer {config.cml_api_key}"

                response = await client.get(test_url, headers=headers)
                status = "connected" if response.status_code < 400 else "error"
                setattr(config, status_field, status)
                db.commit()
                msg = "Connection successful" if status == "connected" else f"HTTP {response.status_code}"
                return {"service": service_name, "status": status, "message": msg}
        else:
            setattr(config, status_field, "configured")
            db.commit()
            return {"service": service_name, "status": "configured", "message": f"{service_name.upper()} is configured."}

    except httpx.ConnectError:
        setattr(config, status_field, "error")
        db.commit()
        return {"service": service_name, "status": "error", "message": "Connection refused"}
    except httpx.TimeoutException:
        setattr(config, status_field, "error")
        db.commit()
        return {"service": service_name, "status": "error", "message": "Connection timeout"}
    except Exception as e:
        setattr(config, status_field, "error")
        db.commit()
        return {"service": service_name, "status": "error", "message": str(e)}
