"""KPI metrics endpoints - generate and query KPIs"""
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, func, text
from typing import Optional, List
from ..config import settings
from ..database import get_db
from ..models import FiberNodeModel, KPIMetricsModel
from ..schemas import KPIMetricsListResponse, GenerateKPIsRequest
from ..generator import generate_node_kpi_metrics as generate_kpi_metrics
from . import safe_error_response, logger

router = APIRouter(prefix=settings.API_V1_STR, tags=["kpis"])


@router.post("/generate/kpis", response_model=dict)
def generate_kpis(
    request: GenerateKPIsRequest,
    regenerate: bool = Query(False, description="Clear existing KPIs before generating new ones"),
    db: Session = Depends(get_db),
):
    """Generate KPI metrics for nodes (can be triggered by NiFi scheduler)"""
    try:
        import time
        start_time = time.time()

        if regenerate:
            db.execute(KPIMetricsModel.__table__.delete())
            db.commit()

        if request.node_ids:
            node_ids = request.node_ids
        else:
            query = select(FiberNodeModel.node_id)
            result = db.execute(query)
            node_ids = [row[0] for row in result.all()]

        if not node_ids:
            raise HTTPException(status_code=400, detail="No nodes found. Generate nodes first.")

        kpi_batch = []
        for node_id in node_ids:
            for i in range(request.count):
                timestamp = datetime.now() - timedelta(minutes=i * 5)
                kpi_data = generate_kpi_metrics(node_id, timestamp)
                kpi_batch.append(kpi_data)

        if kpi_batch:
            for idx, kpi in enumerate(kpi_batch, start=1):
                kpi['id'] = idx
            db.execute(KPIMetricsModel.__table__.insert(), kpi_batch)
            db.commit()

        elapsed = time.time() - start_time
        total_generated = len(kpi_batch)

        return {
            "status": "success",
            "message": f"Generated {total_generated} KPI records in {elapsed:.2f}s",
            "count": total_generated,
            "nodes": len(node_ids),
            "elapsed_seconds": round(elapsed, 2),
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=safe_error_response(e, "KPI generation"))


@router.post("/generate/historical-kpis", response_model=dict)
def generate_historical_kpis(
    days: int = Query(60, ge=1, le=90, description="Number of days of historical data"),
    interval_minutes: int = Query(60, ge=5, le=1440, description="Interval between KPI records in minutes"),
    node_ids: Optional[List[str]] = Query(None, description="Specific node IDs (default: all)"),
    db: Session = Depends(get_db),
):
    """Generate historical KPI metrics for 60 days (or custom period) with configurable intervals"""
    try:
        import time
        start_time = time.time()

        if node_ids:
            target_node_ids = node_ids
        else:
            query = select(FiberNodeModel.node_id)
            result = db.execute(query)
            target_node_ids = [row[0] for row in result.all()]

        if not target_node_ids:
            raise HTTPException(status_code=400, detail="No nodes found. Generate nodes first.")

        total_minutes = days * 24 * 60
        records_per_node = total_minutes // interval_minutes
        total_records_estimate = len(target_node_ids) * records_per_node

        print(f"Generating historical KPIs: {len(target_node_ids)} nodes, {days} days, {interval_minutes}m intervals")

        total_generated = 0
        batch_size = 50000
        current_batch = []
        id_counter = 1

        for node_idx, node_id in enumerate(target_node_ids):
            for i in range(records_per_node):
                minutes_ago = i * interval_minutes
                timestamp = datetime.now() - timedelta(minutes=minutes_ago)
                kpi_data = generate_kpi_metrics(node_id, timestamp)
                kpi_data['id'] = id_counter
                id_counter += 1
                current_batch.append(kpi_data)
                total_generated += 1

                if len(current_batch) >= batch_size:
                    db.execute(KPIMetricsModel.__table__.insert(), current_batch)
                    db.commit()
                    elapsed = time.time() - start_time
                    progress_pct = (total_generated / total_records_estimate) * 100
                    records_per_sec = total_generated / elapsed if elapsed > 0 else 0
                    print(f"   Progress: {progress_pct:.1f}% | Speed: {records_per_sec:.0f} rec/s")
                    current_batch = []

        if current_batch:
            db.execute(KPIMetricsModel.__table__.insert(), current_batch)
            db.commit()

        elapsed = time.time() - start_time
        records_per_sec = total_generated / elapsed if elapsed > 0 else 0

        return {
            "status": "success",
            "message": f"Generated {total_generated} historical KPI records in {elapsed:.1f}s",
            "count": total_generated,
            "nodes": len(target_node_ids),
            "days": days,
            "interval_minutes": interval_minutes,
            "records_per_node": records_per_node,
            "elapsed_seconds": round(elapsed, 2),
            "records_per_second": round(records_per_sec, 0),
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=safe_error_response(e, "historical KPI generation"))


@router.get("/kpis", response_model=KPIMetricsListResponse)
def get_kpis(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return (max 1000)"),
    node_id: Optional[str] = Query(None, description="Filter by node ID"),
    start_time: Optional[datetime] = Query(None, description="Start timestamp"),
    end_time: Optional[datetime] = Query(None, description="End timestamp"),
    db: Session = Depends(get_db),
):
    """Get KPI metrics with pagination and filtering"""
    query = select(KPIMetricsModel)

    if node_id:
        query = query.where(KPIMetricsModel.node_id == node_id)
    if start_time:
        query = query.where(KPIMetricsModel.timestamp >= start_time)
    if end_time:
        query = query.where(KPIMetricsModel.timestamp <= end_time)

    query = query.order_by(KPIMetricsModel.timestamp.desc())

    count_query = select(func.count()).select_from(query.alias())
    total = db.execute(count_query).scalar()

    query = query.offset(skip).limit(limit)
    kpis = db.execute(query).scalars().all()

    return {
        "total": total,
        "page": skip // limit + 1,
        "page_size": limit,
        "items": kpis,
    }


@router.get("/kpis/aggregated")
def get_aggregated_kpis(
    days: int = Query(30, ge=1, le=90, description="Number of days to aggregate"),
    granularity: str = Query("daily", description="Aggregation granularity: hourly or daily"),
    node_id: Optional[str] = Query(None, description="Filter by node ID"),
    db: Session = Depends(get_db),
):
    """Get aggregated KPI data for charting."""
    end_time = datetime.now()
    start_time_val = end_time - timedelta(days=days)

    if granularity not in ("hourly", "daily"):
        granularity = "daily"

    # Use pre-aggregated tables for efficiency instead of scanning raw kpi_metrics
    # kpi_metrics_hourly / kpi_metrics_daily already have AVG values per node per period
    if granularity == "daily":
        table = "kpi_metrics_daily"
        date_trunc = "date_trunc('day', timestamp)"
    else:
        table = "kpi_metrics_hourly"
        date_trunc = "date_trunc('hour', timestamp)"

    base_query = f"""
        SELECT
            {date_trunc} as period,
            SUM(sample_count) as record_count,
            COUNT(DISTINCT node_id) as node_count,
            AVG(ds_snr_db) as avg_ds_snr,
            AVG(packet_loss_percent) as avg_packet_loss,
            AVG(us_snr_db) as avg_us_snr,
            AVG(downstream_throughput_mbps) as avg_throughput,
            AVG(latency_ms) as avg_latency,
            AVG(jitter_ms) as avg_jitter,
            AVG(active_modems) as avg_active_modems,
            AVG(node_cpu_utilization) as avg_cpu,
            AVG(node_memory_utilization) as avg_memory,
            AVG(node_temperature) as avg_temperature
        FROM {table}
        WHERE timestamp >= :start_time
          AND timestamp <= :end_time
    """

    params = {"start_time": start_time_val, "end_time": end_time}

    if node_id:
        base_query += " AND node_id = :node_id"
        params["node_id"] = node_id

    base_query += f" GROUP BY {date_trunc} ORDER BY period ASC"

    result = db.execute(text(base_query), params)
    rows = result.fetchall()

    aggregated_data = []
    for row in rows:
        aggregated_data.append({
            "period": row[0].isoformat() if row[0] else None,
            "record_count": row[1],
            "node_count": row[2],
            "avg_ds_snr": round(row[3], 2) if row[3] else 0,
            "avg_packet_loss": round(row[4], 2) if row[4] else 0,
            "avg_us_snr": round(row[5], 2) if row[5] else 0,
            "avg_throughput": round(row[6], 2) if row[6] else 0,
            "avg_latency": round(row[7], 2) if row[7] else 0,
            "avg_jitter": round(row[8], 2) if row[8] else 0,
            "avg_active_modems": round(row[9], 0) if row[9] else 0,
            "avg_cpu": round(row[10], 2) if row[10] else 0,
            "avg_memory": round(row[11], 2) if row[11] else 0,
            "avg_temperature": round(row[12], 2) if row[12] else 0,
        })

    return {
        "days": days,
        "granularity": granularity,
        "start_time": start_time_val.isoformat(),
        "end_time": end_time.isoformat(),
        "data_points": len(aggregated_data),
        "items": aggregated_data,
    }
