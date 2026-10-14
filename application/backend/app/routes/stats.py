"""Statistics endpoints"""
from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from ..config import settings
from ..database import get_db
from ..models import FiberNodeModel, KPIMetricsModel, AlertModel, SelfHealingActionModel

router = APIRouter(prefix=settings.API_V1_STR, tags=["stats"])


@router.get("/stats")
def get_statistics(db: Session = Depends(get_db)):
    """Get overall statistics (useful for monitoring and NiFi dashboards)"""
    from ..background_tasks import background_generator

    node_count = db.execute(select(func.count(FiberNodeModel.id))).scalar()
    kpi_count = db.execute(select(func.count(KPIMetricsModel.id))).scalar()
    alert_count = db.execute(select(func.count(AlertModel.id))).scalar()
    action_count = db.execute(select(func.count(SelfHealingActionModel.id))).scalar()

    return {
        "nodes": node_count,
        "kpi_metrics": kpi_count,
        "alerts": alert_count,
        "actions": action_count,
        "timestamp": datetime.now().isoformat(),
        "background_generator": background_generator.get_stats(),
    }
