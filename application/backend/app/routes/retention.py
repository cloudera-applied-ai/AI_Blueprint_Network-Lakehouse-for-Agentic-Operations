"""Data retention endpoints"""
from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from ..config import settings
from ..database import get_db
from ..models import KPIMetricsModel

router = APIRouter(prefix=settings.API_V1_STR, tags=["retention"])


@router.get("/retention/status")
def get_retention_status(db: Session = Depends(get_db)):
    """Get data retention service status and statistics"""
    from ..data_retention import data_retention_service
    from ..models import (
        KPIMetrics1MinModel, KPIMetrics5MinModel,
        KPIMetricsHourlyModel, KPIMetricsDailyModel
    )

    raw_count = db.execute(select(func.count(KPIMetricsModel.id))).scalar()
    min1_count = db.execute(select(func.count(KPIMetrics1MinModel.id))).scalar()
    min5_count = db.execute(select(func.count(KPIMetrics5MinModel.id))).scalar()
    hourly_count = db.execute(select(func.count(KPIMetricsHourlyModel.id))).scalar()
    daily_count = db.execute(select(func.count(KPIMetricsDailyModel.id))).scalar()

    return {
        "service_stats": data_retention_service.get_stats(),
        "record_counts": {
            "raw_5sec": raw_count,
            "aggregated_1min": min1_count,
            "aggregated_5min": min5_count,
            "aggregated_hourly": hourly_count,
            "aggregated_daily": daily_count,
            "total": raw_count + min1_count + min5_count + hourly_count + daily_count,
        },
        "timestamp": datetime.now().isoformat(),
    }


@router.post("/retention/cleanup")
async def trigger_cleanup():
    """Manually trigger data cleanup"""
    from ..data_retention import data_retention_service
    await data_retention_service._cleanup_old_data()
    return {
        "status": "success",
        "message": "Cleanup triggered",
        "stats": data_retention_service.get_stats(),
    }
