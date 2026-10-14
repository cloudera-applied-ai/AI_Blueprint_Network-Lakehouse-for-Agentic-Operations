"""Customer Intelligence API endpoints"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func as sql_func, case, select, and_
from typing import Optional
from ..config import settings
from ..database import get_db
from ..models import CustomerAccountModel, CustomerSentimentModel, FiberNodeModel
from . import logger

router = APIRouter(prefix=settings.API_V1_STR, tags=["customers"])


def _region_filter(region: Optional[str]):
    """Return a filter clause to restrict customers by node region."""
    if not region:
        return None
    node_subq = select(FiberNodeModel.node_id).where(
        FiberNodeModel.region == region
    ).scalar_subquery()
    return CustomerAccountModel.node_id.in_(node_subq)


@router.get("/customers/overview")
def get_customer_overview(
    region: Optional[str] = Query(None, description="Filter by region"),
    db: Session = Depends(get_db),
):
    """Customer overview: counts, plan distribution, sentiment averages, DOCSIS breakdown"""

    base_filters = []
    rf = _region_filter(region)
    if rf is not None:
        base_filters.append(rf)

    # --- Plan + status distribution (1 query) ---
    plan_q = db.query(
        CustomerAccountModel.service_plan,
        CustomerAccountModel.account_status,
        sql_func.count(CustomerAccountModel.id).label("cnt"),
        sql_func.coalesce(sql_func.sum(CustomerAccountModel.monthly_rate), 0).label("revenue"),
    )
    for f in base_filters:
        plan_q = plan_q.filter(f)
    plan_rows = plan_q.group_by(
        CustomerAccountModel.service_plan,
        CustomerAccountModel.account_status,
    ).all()

    by_plan: dict = {}
    total_customers = 0
    total_active = 0
    total_monthly_revenue = 0.0
    for row in plan_rows:
        plan = row.service_plan or "Unknown"
        if plan not in by_plan:
            by_plan[plan] = {"total": 0, "active": 0, "suspended": 0, "closed": 0, "revenue": 0.0}
        by_plan[plan]["total"] += row.cnt
        by_plan[plan]["revenue"] += float(row.revenue or 0)
        total_customers += row.cnt
        total_monthly_revenue += float(row.revenue or 0)
        status = (row.account_status or "").lower()
        if status == "active":
            by_plan[plan]["active"] += row.cnt
            total_active += row.cnt
        elif status == "suspended":
            by_plan[plan]["suspended"] += row.cnt
        elif status == "closed":
            by_plan[plan]["closed"] += row.cnt

    # --- DOCSIS breakdown (1 query) ---
    docsis_q = db.query(
        sql_func.coalesce(CustomerAccountModel.docsis_version, "Unknown").label("version"),
        sql_func.count(CustomerAccountModel.id).label("cnt"),
    )
    for f in base_filters:
        docsis_q = docsis_q.filter(f)
    docsis_rows = docsis_q.group_by("version").all()
    by_docsis = {row.version: row.cnt for row in docsis_rows}

    # --- Connection quality (1 query) ---
    quality_q = db.query(
        sql_func.sum(case((CustomerAccountModel.connection_drops_24h > 5, 1), else_=0)).label("high_drops"),
        sql_func.sum(case(
            (
                (CustomerAccountModel.actual_download_mbps != None) &
                (CustomerAccountModel.provisioned_download_mbps != None) &
                (CustomerAccountModel.actual_download_mbps >= CustomerAccountModel.provisioned_download_mbps * 0.8),
                1
            ), else_=0
        )).label("meeting"),
        sql_func.sum(case(
            (
                (CustomerAccountModel.actual_download_mbps != None) &
                (CustomerAccountModel.provisioned_download_mbps != None) &
                (CustomerAccountModel.actual_download_mbps < CustomerAccountModel.provisioned_download_mbps * 0.8),
                1
            ), else_=0
        )).label("below"),
    )
    for f in base_filters:
        quality_q = quality_q.filter(f)
    quality = quality_q.one()

    # --- Sentiment averages (1 query) ---
    # Join sentiments to customers (optionally filtered by region)
    sent_q = db.query(
        sql_func.avg(CustomerSentimentModel.sentiment_score).label("avg_sentiment"),
        sql_func.avg(CustomerSentimentModel.nps_score).label("avg_nps"),
        sql_func.count(CustomerSentimentModel.id).label("total_sentiments"),
    )
    if rf is not None:
        sent_q = sent_q.join(
            CustomerAccountModel,
            CustomerSentimentModel.account_id == CustomerAccountModel.account_id,
        ).filter(rf)
    sent = sent_q.one()

    return {
        "total_customers": total_customers,
        "total_active": total_active,
        "total_monthly_revenue": round(total_monthly_revenue, 2),
        "avg_sentiment_score": round(float(sent.avg_sentiment or 0), 3),
        "avg_nps_score": round(float(sent.avg_nps or 0), 1),
        "total_sentiments": int(sent.total_sentiments or 0),
        "by_service_plan": by_plan,
        "by_docsis_version": by_docsis,
        "connection_quality": {
            "high_drop_customers": int(quality.high_drops or 0),
            "meeting_speed_threshold": int(quality.meeting or 0),
            "below_speed_threshold": int(quality.below or 0),
        },
    }


@router.get("/customers/list")
def get_customer_list(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    service_plan: Optional[str] = Query(None),
    account_status: Optional[str] = Query(None),
    search: Optional[str] = Query(None, description="Search name or address"),
    node_id: Optional[str] = Query(None),
    region: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Paginated customer list with search/filter, includes latest sentiment score"""

    query = db.query(CustomerAccountModel)

    if node_id:
        query = query.filter(CustomerAccountModel.node_id == node_id)
    if service_plan:
        query = query.filter(CustomerAccountModel.service_plan == service_plan)
    if account_status:
        query = query.filter(CustomerAccountModel.account_status == account_status)
    if search:
        like_pattern = f"%{search}%"
        query = query.filter(
            (CustomerAccountModel.name.ilike(like_pattern))
            | (CustomerAccountModel.address.ilike(like_pattern))
        )
    rf = _region_filter(region)
    if rf is not None:
        query = query.filter(rf)

    total = query.count()
    rows = query.order_by(CustomerAccountModel.id).offset(skip).limit(limit).all()

    # Batch-fetch latest sentiment scores for these accounts
    account_ids = [r.account_id for r in rows]
    sent_map: dict = {}
    if account_ids:
        sent_rows = db.query(
            CustomerSentimentModel.account_id,
            sql_func.avg(CustomerSentimentModel.sentiment_score).label("avg_score"),
        ).filter(
            CustomerSentimentModel.account_id.in_(account_ids)
        ).group_by(CustomerSentimentModel.account_id).all()
        sent_map = {r.account_id: round(float(r.avg_score or 0), 3) for r in sent_rows}

    customers = []
    for c in rows:
        customers.append({
            "account_id": c.account_id,
            "name": c.name,
            "address": c.address,
            "city": c.city,
            "state": c.state,
            "node_id": c.node_id,
            "service_plan": c.service_plan,
            "monthly_rate": c.monthly_rate,
            "modem_manufacturer": c.modem_manufacturer,
            "modem_model": c.modem_model,
            "docsis_version": c.docsis_version,
            "provisioned_download_mbps": c.provisioned_download_mbps,
            "actual_download_mbps": c.actual_download_mbps,
            "provisioned_upload_mbps": c.provisioned_upload_mbps,
            "actual_upload_mbps": c.actual_upload_mbps,
            "connection_drops_24h": c.connection_drops_24h,
            "drop_quality": c.drop_quality,
            "account_status": c.account_status,
            "contract_status": c.contract_status,
            "tenure_months": c.tenure_months,
            "avg_sentiment_score": sent_map.get(c.account_id),
        })

    return {"total": total, "customers": customers}


@router.get("/customers/sentiment/summary")
def get_sentiment_summary(
    region: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Sentiment analytics: by source, by topic, NPS distribution"""

    base_join = []
    rf = _region_filter(region)
    if rf is not None:
        base_join.append(rf)

    def _base_query(q):
        if rf is not None:
            q = q.join(
                CustomerAccountModel,
                CustomerSentimentModel.account_id == CustomerAccountModel.account_id,
            ).filter(rf)
        return q

    # --- By source ---
    src_q = _base_query(db.query(
        CustomerSentimentModel.source,
        sql_func.count(CustomerSentimentModel.id).label("cnt"),
        sql_func.avg(CustomerSentimentModel.sentiment_score).label("avg_score"),
    ))
    src_rows = src_q.group_by(CustomerSentimentModel.source).all()
    by_source = [
        {"source": r.source, "count": r.cnt, "avg_score": round(float(r.avg_score or 0), 3)}
        for r in src_rows
    ]

    # --- By sentiment label ---
    label_q = _base_query(db.query(
        CustomerSentimentModel.sentiment_label,
        sql_func.count(CustomerSentimentModel.id).label("cnt"),
    ))
    label_rows = label_q.group_by(CustomerSentimentModel.sentiment_label).all()
    by_label = {r.sentiment_label: r.cnt for r in label_rows}

    # --- NPS distribution (only nps_survey source) ---
    nps_q = _base_query(db.query(
        CustomerSentimentModel.nps_score,
        sql_func.count(CustomerSentimentModel.id).label("cnt"),
    ).filter(CustomerSentimentModel.nps_score != None))
    nps_rows = nps_q.group_by(CustomerSentimentModel.nps_score).all()

    promoters = sum(r.cnt for r in nps_rows if r.nps_score is not None and r.nps_score >= 9)
    passives = sum(r.cnt for r in nps_rows if r.nps_score is not None and 7 <= r.nps_score <= 8)
    detractors = sum(r.cnt for r in nps_rows if r.nps_score is not None and r.nps_score <= 6)
    total_nps = promoters + passives + detractors
    nps_score = round(((promoters - detractors) / total_nps * 100), 1) if total_nps > 0 else 0

    # --- By resolution status ---
    res_q = _base_query(db.query(
        CustomerSentimentModel.resolution_status,
        sql_func.count(CustomerSentimentModel.id).label("cnt"),
    ))
    res_rows = res_q.group_by(CustomerSentimentModel.resolution_status).all()
    by_resolution = {r.resolution_status or "unknown": r.cnt for r in res_rows}

    return {
        "by_source": by_source,
        "by_label": by_label,
        "nps": {
            "score": nps_score,
            "promoters": promoters,
            "passives": passives,
            "detractors": detractors,
            "total_responses": total_nps,
        },
        "by_resolution": by_resolution,
    }


@router.get("/customers/plans/breakdown")
def get_plans_breakdown(
    region: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Service plan analytics: revenue, churn risk, speed compliance per plan"""

    base_filters = []
    rf = _region_filter(region)
    if rf is not None:
        base_filters.append(rf)

    q = db.query(
        CustomerAccountModel.service_plan,
        sql_func.count(CustomerAccountModel.id).label("total"),
        sql_func.sum(case((CustomerAccountModel.account_status == "active", 1), else_=0)).label("active"),
        sql_func.sum(case((CustomerAccountModel.account_status == "suspended", 1), else_=0)).label("suspended"),
        sql_func.sum(case((CustomerAccountModel.account_status == "closed", 1), else_=0)).label("closed"),
        sql_func.coalesce(sql_func.sum(CustomerAccountModel.monthly_rate), 0).label("monthly_revenue"),
        sql_func.avg(CustomerAccountModel.tenure_months).label("avg_tenure"),
        sql_func.avg(CustomerAccountModel.actual_download_mbps).label("avg_download"),
        sql_func.avg(CustomerAccountModel.provisioned_download_mbps).label("prov_download"),
        sql_func.sum(case(
            (
                (CustomerAccountModel.actual_download_mbps != None) &
                (CustomerAccountModel.provisioned_download_mbps != None) &
                (CustomerAccountModel.actual_download_mbps >= CustomerAccountModel.provisioned_download_mbps * 0.8),
                1
            ), else_=0
        )).label("speed_compliant"),
    )
    for f in base_filters:
        q = q.filter(f)

    rows = q.group_by(CustomerAccountModel.service_plan).all()

    plans = []
    for r in rows:
        plan_total = r.total or 1
        plans.append({
            "plan": r.service_plan or "Unknown",
            "total": r.total,
            "active": int(r.active or 0),
            "suspended": int(r.suspended or 0),
            "closed": int(r.closed or 0),
            "churn_risk_pct": round(((int(r.suspended or 0) + int(r.closed or 0)) / plan_total) * 100, 1),
            "monthly_revenue": round(float(r.monthly_revenue or 0), 2),
            "avg_tenure_months": round(float(r.avg_tenure or 0), 1),
            "avg_download_mbps": round(float(r.avg_download or 0), 1),
            "provisioned_download_mbps": round(float(r.prov_download or 0), 1),
            "speed_compliant": int(r.speed_compliant or 0),
            "speed_compliance_pct": round((int(r.speed_compliant or 0) / plan_total) * 100, 1),
        })

    plans.sort(key=lambda p: p["monthly_revenue"], reverse=True)
    return {"plans": plans}
