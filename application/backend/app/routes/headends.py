"""Headend endpoints"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from typing import Optional
from ..config import settings
from ..database import get_db
from ..models import HeadendModel
from . import logger

router = APIRouter(prefix=settings.API_V1_STR, tags=["headends"])


@router.get("/headends")
def get_headends(
    region: Optional[str] = Query(None, description="Filter by region"),
    city: Optional[str] = Query(None, description="Filter by city"),
    status: Optional[str] = Query(None, description="Filter by status"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    db: Session = Depends(get_db),
):
    """Get list of headends with optional filtering."""
    query = select(HeadendModel)

    if region:
        query = query.where(HeadendModel.region == region)
    if city:
        query = query.where(HeadendModel.city == city)
    if status:
        query = query.where(HeadendModel.status == status)

    count_query = select(func.count(HeadendModel.id))
    if region:
        count_query = count_query.where(HeadendModel.region == region)
    if city:
        count_query = count_query.where(HeadendModel.city == city)
    if status:
        count_query = count_query.where(HeadendModel.status == status)
    total = db.execute(count_query).scalar() or 0

    query = query.order_by(HeadendModel.name).offset(skip).limit(limit)
    headends = db.execute(query).scalars().all()

    items = []
    for he in headends:
        items.append({
            "headend_id": he.headend_id,
            "name": he.name,
            "region": he.region,
            "city": he.city,
            "status": he.status,
            "tier": None,
            "location": he.service_area,
            "country": he.state,
            "power_capacity_mw": he.power_capacity_mw,
            "current_power_mw": None,
            "total_rack_units": he.total_rack_units,
            "used_rack_units": None,
        })

    return {
        "total": total,
        "items": items,
    }


@router.get("/headends/metadata/summary")
def get_headend_metadata_summary(db: Session = Depends(get_db)):
    """Get summary of headend metadata including regions, cities, and statuses with counts."""
    region_query = select(
        HeadendModel.region,
        func.count(HeadendModel.headend_id).label('count')
    ).where(HeadendModel.region.isnot(None)).group_by(HeadendModel.region)
    region_result = db.execute(region_query).all()
    regions = [{"value": row[0], "count": row[1]} for row in region_result if row[0]]

    city_query = select(
        HeadendModel.city,
        HeadendModel.region,
        func.count(HeadendModel.headend_id).label('count')
    ).where(HeadendModel.city.isnot(None)).group_by(HeadendModel.city, HeadendModel.region)
    city_result = db.execute(city_query).all()
    cities = [{"value": row[0], "count": row[2], "region": row[1]} for row in city_result if row[0]]

    status_query = select(
        HeadendModel.status,
        func.count(HeadendModel.headend_id).label('count')
    ).where(HeadendModel.status.isnot(None)).group_by(HeadendModel.status)
    status_result = db.execute(status_query).all()
    statuses = [{"value": row[0], "count": row[1]} for row in status_result if row[0]]

    total_count = db.execute(select(func.count(HeadendModel.headend_id))).scalar() or 0

    return {
        "total_headends": total_count,
        "regions": regions,
        "cities": cities,
        "statuses": statuses,
    }
