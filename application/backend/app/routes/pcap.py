"""Packet-capture analysis endpoints (manual upload + chat + reports)."""
import asyncio
import logging
import os
import tempfile
from datetime import date

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models import PcapChatMessageModel
from ..pcap import analysis
from ..pcap.chat import reply as chat_reply
from ..pcap.docx_report import build_docx
from ..pcap.report import generate_report
from ..pcap.schemas import ChatMessage
from . import logger

router = APIRouter(prefix=settings.API_V1_STR, tags=["pcap"])

_DOCX_MEDIA = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


class ChatBody(BaseModel):
    capture_id: str
    messages: list[ChatMessage]


class ReportBody(BaseModel):
    capture_id: str


class DocxBody(BaseModel):
    capture_id: str
    include_chat: bool = False
    messages: list[ChatMessage] | None = None


def _capture_response(capture) -> dict:
    return {
        "capture_id": capture.id,
        "source": capture.source,
        "filename": capture.filename,
        "headend_id": capture.headend_id,
        "edge_execution_id": capture.edge_execution_id,
        "metadata": capture.metadata.model_dump(),
        "agents": [a.model_dump() for a in capture.agents],
    }


@router.post("/pcap/analyze")
async def analyze(file: UploadFile = File(...), db: Session = Depends(get_db)) -> dict:
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pcap") as tmp:
        tmp.write(await file.read())
        tmp.flush()
    try:
        capture = await analysis.analyze_pcap_file(tmp.name, file.filename, source="upload")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        os.unlink(tmp.name)
    analysis.persist_capture(db, capture)
    return _capture_response(capture)


@router.get("/pcap/captures")
def list_captures(limit: int = 50, db: Session = Depends(get_db)) -> list[dict]:
    return analysis.list_captures(db, limit=min(limit, 200))


@router.get("/pcap/captures/{capture_id}")
def get_capture(capture_id: str, db: Session = Depends(get_db)) -> dict:
    capture = analysis.get_capture(db, capture_id)
    if capture is None:
        raise HTTPException(status_code=404, detail="Capture not found")
    payload = _capture_response(capture)
    if capture.edge_execution_id:
        payload["edge_context"] = _edge_context(db, capture.edge_execution_id)
    return payload


def _edge_context(db: Session, execution_id: str) -> dict | None:
    from ..models import EdgeAnomalyExecutionModel

    row = db.query(EdgeAnomalyExecutionModel).filter_by(execution_id=execution_id).first()
    if row is None:
        return None
    return {
        "execution_id": row.execution_id,
        "headend_id": row.headend_id,
        "headend_name": row.headend_name,
        "scenario_id": row.scenario_id,
        "pcap_source": row.pcap_source,
        "staging_backend": row.staging_backend,
        "staged_uri": row.staged_uri,
        "edge_actions": row.edge_actions or [],
    }


@router.post("/pcap/chat")
def chat_endpoint(body: ChatBody, db: Session = Depends(get_db)) -> dict:
    capture = analysis.get_capture(db, body.capture_id)
    if capture is None:
        raise HTTPException(status_code=404, detail="Capture not found")
    try:
        answer = chat_reply(capture, body.messages)
    except Exception as exc:  # noqa: BLE001
        logger.error("pcap chat failed: %s", exc)
        raise HTTPException(status_code=502, detail=f"Chat failed: {exc}") from exc
    try:
        last_user = next((m for m in reversed(body.messages) if m.role == "user"), None)
        if last_user is not None:
            db.add(PcapChatMessageModel(capture_id=body.capture_id, role="user", content=last_user.content))
        db.add(PcapChatMessageModel(capture_id=body.capture_id, role="assistant", content=answer))
        db.commit()
    except Exception:  # noqa: BLE001
        db.rollback()
    return {"reply": answer}


@router.post("/pcap/report")
def report_endpoint(body: ReportBody, db: Session = Depends(get_db)) -> dict:
    capture = analysis.get_capture(db, body.capture_id)
    if capture is None:
        raise HTTPException(status_code=404, detail="Capture not found")
    try:
        return {"report_markdown": generate_report(capture)}
    except Exception as exc:  # noqa: BLE001
        logger.error("pcap report failed: %s", exc)
        raise HTTPException(status_code=502, detail=f"Report generation failed: {exc}") from exc


@router.post("/pcap/report/docx")
def report_docx(body: DocxBody, db: Session = Depends(get_db)) -> StreamingResponse:
    capture = analysis.get_capture(db, body.capture_id)
    if capture is None:
        raise HTTPException(status_code=404, detail="Capture not found")

    edge_event = _edge_context(db, capture.edge_execution_id) if capture.edge_execution_id else None
    if edge_event and edge_event.get("headend_name"):
        edge_event["site"] = {
            "name": edge_event.get("headend_name"),
            "location": edge_event.get("headend_id"),
            "model_name": "edge-anomaly-detector-v2",
        }

    transcript = None
    if body.include_chat:
        if body.messages:
            transcript = [{"role": m.role, "content": m.content} for m in body.messages]
        else:
            rows = (
                db.query(PcapChatMessageModel)
                .filter(PcapChatMessageModel.capture_id == body.capture_id)
                .order_by(PcapChatMessageModel.created_at, PcapChatMessageModel.id)
                .all()
            )
            transcript = [{"role": r.role, "content": r.content} for r in rows]

    try:
        buf = build_docx(capture, edge_event=edge_event, chat_transcript=transcript)
    except Exception as exc:  # noqa: BLE001
        logger.error("pcap docx failed: %s", exc)
        raise HTTPException(status_code=502, detail=f"Report generation failed: {exc}") from exc

    filename = f"pcap-incident-report-{date.today().isoformat()}.docx"
    return StreamingResponse(
        buf, media_type=_DOCX_MEDIA,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
