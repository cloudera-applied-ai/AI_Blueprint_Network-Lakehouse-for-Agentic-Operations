"""Weather endpoints"""
from datetime import datetime, timedelta
from collections import defaultdict
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from ..config import settings
from ..database import get_db
from ..models import FiberNodeModel, KPIMetricsModel

router = APIRouter(prefix=settings.API_V1_STR, tags=["weather"])


@router.get("/weather/summary")
def get_weather_summary(db: Session = Depends(get_db)):
    """Get global weather summary for the dashboard."""
    from ..schemas import WeatherSummaryResponse, WeatherRegionSummary

    subquery = (
        select(
            KPIMetricsModel.node_id,
            func.max(KPIMetricsModel.timestamp).label('max_ts')
        )
        .where(KPIMetricsModel.weather_conditions.isnot(None))
        .where(KPIMetricsModel.timestamp > datetime.now() - timedelta(minutes=10))
        .group_by(KPIMetricsModel.node_id)
        .subquery()
    )

    query = (
        select(
            KPIMetricsModel.node_id,
            KPIMetricsModel.weather_conditions,
            KPIMetricsModel.weather_impact,
            KPIMetricsModel.temperature_outdoor,
            KPIMetricsModel.precipitation_mm,
            KPIMetricsModel.wind_speed_kmh,
            FiberNodeModel.region
        )
        .join(
            subquery,
            (KPIMetricsModel.node_id == subquery.c.node_id) &
            (KPIMetricsModel.timestamp == subquery.c.max_ts)
        )
        .outerjoin(FiberNodeModel, KPIMetricsModel.node_id == FiberNodeModel.node_id)
    )

    results = db.execute(query).fetchall()

    if not results:
        return WeatherSummaryResponse(
            timestamp=datetime.now(),
            total_nodes_with_weather=0,
            nodes_with_significant_impact=0,
            weather_conditions_summary={},
            regions=[],
            extreme_weather_nodes=[],
            avg_global_impact=0.0
        )

    conditions_count = defaultdict(int)
    region_data = defaultdict(lambda: {
        'node_count': 0,
        'conditions': defaultdict(int),
        'temps': [],
        'winds': [],
        'precips': [],
        'impacts': [],
        'impacted_count': 0
    })
    extreme_nodes = []
    significant_impact_count = 0
    total_impact = 0.0
    impact_count = 0

    for row in results:
        node_id, conditions, impact, temp, precip, wind, region = row

        if conditions:
            conditions_count[conditions] += 1

        if impact is not None:
            total_impact += impact
            impact_count += 1
            if impact > 0.3:
                significant_impact_count += 1
            if impact > 0.5:
                extreme_nodes.append(node_id)

        region_key = region or 'Unknown'
        rd = region_data[region_key]
        rd['node_count'] += 1
        if conditions:
            rd['conditions'][conditions] += 1
        if temp is not None:
            rd['temps'].append(temp)
        if wind is not None:
            rd['winds'].append(wind)
        if precip is not None:
            rd['precips'].append(precip)
        if impact is not None:
            rd['impacts'].append(impact)
            if impact > 0.1:
                rd['impacted_count'] += 1

    region_summaries = []
    for region_name, rd in region_data.items():
        region_summaries.append(WeatherRegionSummary(
            region=region_name,
            node_count=rd['node_count'],
            conditions=dict(rd['conditions']),
            avg_temperature=round(sum(rd['temps']) / len(rd['temps']), 1) if rd['temps'] else None,
            avg_wind_speed=round(sum(rd['winds']) / len(rd['winds']), 1) if rd['winds'] else None,
            avg_precipitation=round(sum(rd['precips']) / len(rd['precips']), 2) if rd['precips'] else None,
            avg_weather_impact=round(sum(rd['impacts']) / len(rd['impacts']), 3) if rd['impacts'] else 0.0,
            nodes_with_impact=rd['impacted_count']
        ))

    region_summaries.sort(key=lambda x: x.avg_weather_impact, reverse=True)

    return WeatherSummaryResponse(
        timestamp=datetime.now(),
        total_nodes_with_weather=len(results),
        nodes_with_significant_impact=significant_impact_count,
        weather_conditions_summary=dict(conditions_count),
        regions=region_summaries,
        extreme_weather_nodes=extreme_nodes[:20],
        avg_global_impact=round(total_impact / impact_count, 3) if impact_count > 0 else 0.0
    )


@router.get("/weather/node/{node_id}")
def get_node_weather(node_id: str, db: Session = Depends(get_db)):
    """Get current weather data for a specific node"""
    from ..schemas import NodeWeatherResponse

    query = (
        select(
            KPIMetricsModel.weather_conditions,
            KPIMetricsModel.weather_impact,
            KPIMetricsModel.temperature_outdoor,
            KPIMetricsModel.precipitation_mm,
            KPIMetricsModel.wind_speed_kmh,
            KPIMetricsModel.timestamp
        )
        .where(KPIMetricsModel.node_id == node_id)
        .where(KPIMetricsModel.weather_conditions.isnot(None))
        .order_by(KPIMetricsModel.timestamp.desc())
        .limit(1)
    )

    result = db.execute(query).fetchone()

    if not result:
        return NodeWeatherResponse(node_id=node_id)

    return NodeWeatherResponse(
        node_id=node_id,
        weather_conditions=result[0],
        weather_impact=result[1],
        temperature_outdoor=result[2],
        precipitation_mm=result[3],
        wind_speed_kmh=result[4],
        last_updated=result[5]
    )
