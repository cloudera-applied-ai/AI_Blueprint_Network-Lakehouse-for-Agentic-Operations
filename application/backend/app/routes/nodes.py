"""Fiber node endpoints - generate and query nodes"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from typing import Optional
from ..config import settings
from ..database import get_db
from ..models import FiberNodeModel, HeadendModel, CMTSModel, HubModel, AmplifierModel
from ..schemas import FiberNode, FiberNodeListResponse, GenerateNodesRequest
from ..generator import generate_all_infrastructure
from . import safe_error_response, logger

router = APIRouter(prefix=settings.API_V1_STR, tags=["nodes"])


@router.post("/generate/nodes", response_model=dict)
def generate_nodes(
    request: GenerateNodesRequest,
    regenerate: bool = Query(False, description="Clear existing nodes before generating new ones"),
    db: Session = Depends(get_db),
):
    """Generate and store all cable plant infrastructure (headends, hubs, CMTS, nodes, amplifiers)"""
    try:
        import time
        start_time = time.time()

        if regenerate:
            print(f"Clearing existing infrastructure...")
            db.execute(AmplifierModel.__table__.delete())
            db.execute(FiberNodeModel.__table__.delete())
            db.execute(HubModel.__table__.delete())
            db.execute(CMTSModel.__table__.delete())
            db.execute(HeadendModel.__table__.delete())
            db.commit()
            print(f"   Existing infrastructure cleared")

        print(f"Generating cable network infrastructure...")
        infra = generate_all_infrastructure()

        # Extract fiber nodes (apply service_area/count filters)
        fiber_nodes = infra["fiber_nodes"]
        if request.service_area:
            fiber_nodes = [n for n in fiber_nodes if n["service_area"] == request.service_area][:request.count]
        else:
            fiber_nodes = fiber_nodes[:request.count]

        # Get the set of node_ids to filter related infrastructure
        node_ids = {n["node_id"] for n in fiber_nodes}
        headend_ids = {n["headend_id"] for n in fiber_nodes}
        hub_ids = {n["hub_id"] for n in fiber_nodes}

        headends = [h for h in infra["headends"] if h["headend_id"] in headend_ids]
        hubs = [h for h in infra["hubs"] if h["hub_id"] in hub_ids]
        cmts_devices = [c for c in infra["cmts_devices"] if c["headend_id"] in headend_ids]
        amplifiers = [a for a in infra["amplifiers"] if a["node_id"] in node_ids]

        # Assign sequential IDs
        for idx, item in enumerate(headends, start=1):
            item['id'] = idx
        for idx, item in enumerate(hubs, start=1):
            item['id'] = idx
        for idx, item in enumerate(cmts_devices, start=1):
            item['id'] = idx
        for idx, item in enumerate(fiber_nodes, start=1):
            item['id'] = idx
        for idx, item in enumerate(amplifiers, start=1):
            item['id'] = idx

        # Insert in dependency order
        if headends:
            db.execute(HeadendModel.__table__.insert(), headends)
        if cmts_devices:
            db.execute(CMTSModel.__table__.insert(), cmts_devices)
        if hubs:
            db.execute(HubModel.__table__.insert(), hubs)
        if fiber_nodes:
            db.execute(FiberNodeModel.__table__.insert(), fiber_nodes)
        if amplifiers:
            db.execute(AmplifierModel.__table__.insert(), amplifiers)
        db.commit()

        elapsed = time.time() - start_time
        counts = {
            "headends": len(headends),
            "cmts_devices": len(cmts_devices),
            "hubs": len(hubs),
            "fiber_nodes": len(fiber_nodes),
            "amplifiers": len(amplifiers),
        }
        total = sum(counts.values())
        print(f"Inserted {total} infrastructure records in {elapsed:.2f}s: {counts}")

        return {
            "status": "success",
            "message": f"Generated {len(fiber_nodes)} fiber nodes + supporting infrastructure in {elapsed:.2f}s",
            "count": len(fiber_nodes),
            "counts": counts,
            "elapsed_seconds": round(elapsed, 2),
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=safe_error_response(e, "node generation"))


@router.get("/nodes", response_model=FiberNodeListResponse)
def get_nodes(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=10000, description="Number of records to return"),
    region: Optional[str] = Query(None, description="Filter by region"),
    status: Optional[str] = Query(None, description="Filter by status"),
    node_type: Optional[str] = Query(None, description="Filter by node type"),
    db: Session = Depends(get_db),
):
    """Get fiber nodes with pagination and filtering"""
    query = select(FiberNodeModel)

    if region:
        query = query.where(FiberNodeModel.region == region)
    if status:
        query = query.where(FiberNodeModel.status == status)
    if node_type:
        query = query.where(FiberNodeModel.node_type == node_type)

    count_query = select(func.count()).select_from(query.alias())
    total = db.execute(count_query).scalar()

    query = query.offset(skip).limit(limit)
    result = db.execute(query)
    nodes = result.scalars().all()

    return {
        "total": total,
        "page": skip // limit + 1,
        "page_size": limit,
        "items": nodes,
    }


@router.get("/nodes/{node_id}", response_model=FiberNode)
def get_node(node_id: str, db: Session = Depends(get_db)):
    """Get specific fiber node by ID"""
    query = select(FiberNodeModel).where(FiberNodeModel.node_id == node_id)
    result = db.execute(query)
    node = result.scalar_one_or_none()

    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    return node


@router.get("/nodes/metadata/summary")
def get_node_metadata_summary(db: Session = Depends(get_db)):
    """Get summary of node metadata including node types, regions with counts."""
    # Consolidated: single query with UNION ALL for all groupings (4 round-trips → 1)
    from sqlalchemy import union_all, literal

    type_q = select(
        literal('node_type').label('category'),
        func.coalesce(FiberNodeModel.node_type, 'Unknown').label('value'),
        func.count(FiberNodeModel.node_id).label('count'),
    ).where(FiberNodeModel.node_type.isnot(None)).group_by(FiberNodeModel.node_type)

    region_q = select(
        literal('region').label('category'),
        func.coalesce(FiberNodeModel.region, 'Unknown').label('value'),
        func.count(FiberNodeModel.node_id).label('count'),
    ).where(FiberNodeModel.region.isnot(None)).group_by(FiberNodeModel.region)

    status_q = select(
        literal('status').label('category'),
        func.coalesce(FiberNodeModel.status, 'Unknown').label('value'),
        func.count(FiberNodeModel.node_id).label('count'),
    ).where(FiberNodeModel.status.isnot(None)).group_by(FiberNodeModel.status)

    total_q = select(
        literal('total').label('category'),
        literal('all').label('value'),
        func.count(FiberNodeModel.node_id).label('count'),
    )

    combined = union_all(type_q, region_q, status_q, total_q)
    rows = db.execute(combined).all()

    node_types = []
    regions = []
    statuses = []
    total_count = 0

    for row in rows:
        if row.category == 'node_type':
            node_types.append({"value": row.value, "count": row.count})
        elif row.category == 'region':
            regions.append({"value": row.value, "count": row.count})
        elif row.category == 'status':
            statuses.append({"value": row.value, "count": row.count})
        elif row.category == 'total':
            total_count = row.count

    return {
        "total_nodes": total_count,
        "node_types": node_types,
        "docsis_versions": [],
        "regions": regions,
        "statuses": statuses,
    }
