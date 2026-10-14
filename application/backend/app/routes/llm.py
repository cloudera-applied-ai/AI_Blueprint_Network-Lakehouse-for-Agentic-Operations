"""LLM configuration, queue, and completion endpoints"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select
from ..config import settings
from ..database import get_db
from ..models import LLMConfigModel
from ..schemas import LLMConfig, LLMConfigCreate, LLMConfigUpdate
from ..llm_queue import llm_queue, LLMJob, JobStatus
from . import safe_error_response, logger

router = APIRouter(prefix=settings.API_V1_STR, tags=["llm"])


def _prepare_llm_request(config, messages: list) -> tuple:
    """Prepare LLM request parameters based on provider config. Returns (api_url, headers, payload)"""
    provider = config.provider.lower()
    # Never default the model: it must come from the configuration saved in
    # Settings -> AI (or the effective writer config built by pcap/llm_bridge).
    if not (getattr(config, "model_name", None) or "").strip():
        raise HTTPException(
            status_code=400,
            detail="No model name configured - set Model Name in Settings -> AI",
        )

    if provider == 'openai':
        api_url = config.endpoint_url or "https://api.openai.com/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config.api_key}"
        }
        payload = {
            "model": config.model_name,
            "messages": messages,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens
        }

    elif provider == 'anthropic':
        api_url = config.endpoint_url or "https://api.anthropic.com/v1/messages"
        headers = {
            "Content-Type": "application/json",
            "x-api-key": config.api_key,
            "anthropic-version": "2023-06-01"
        }
        system_msg = next((m['content'] for m in messages if m['role'] == 'system'), None)
        anthropic_messages = [m for m in messages if m['role'] != 'system']
        payload = {
            "model": config.model_name,
            "messages": anthropic_messages,
            "max_tokens": config.max_tokens,
            "temperature": config.temperature
        }
        if system_msg:
            payload["system"] = system_msg

    elif provider == 'ollama':
        if not config.endpoint_url:
            raise HTTPException(status_code=400, detail="ollama requires endpoint_url (e.g. http://host:11434)")
        api_url = config.endpoint_url.rstrip('/')
        if not api_url.endswith('/chat/completions'):
            if api_url.endswith('/v1'):
                api_url = f"{api_url}/chat/completions"
            elif '/v1' not in api_url:
                api_url = f"{api_url}/v1/chat/completions"
            else:
                api_url = f"{api_url}/chat/completions"
        headers = {"Content-Type": "application/json"}
        payload = {
            "model": config.model_name,
            "messages": messages,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens
        }

    elif provider in ['cloudera', 'custom']:
        if not config.endpoint_url:
            raise HTTPException(status_code=400, detail=f"{provider} requires endpoint_url")

        api_url = config.endpoint_url
        if not api_url.endswith('/chat/completions'):
            if api_url.endswith('/v1'):
                api_url = f"{api_url}/chat/completions"
            elif '/v1' not in api_url:
                api_url = f"{api_url}/v1/chat/completions"
            else:
                api_url = f"{api_url}/chat/completions"

        headers = {"Content-Type": "application/json"}
        if config.jwt_token:
            headers["Authorization"] = f"Bearer {config.jwt_token}"
        elif config.api_key:
            headers["Authorization"] = f"Bearer {config.api_key}"

        payload = {
            "model": config.model_name,
            "messages": messages,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens
        }
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider}")

    return api_url, headers, payload


def _get_llm_config(db: Session):
    """Helper to get LLM config from DB"""
    query = select(LLMConfigModel).where(LLMConfigModel.id == 1)
    config = db.execute(query).scalar_one_or_none()
    if not config:
        query = select(LLMConfigModel).where(LLMConfigModel.config_key == "default")
        config = db.execute(query).scalar_one_or_none()
    return config


# ===== LLM CONFIG CRUD =====

@router.get("/llm/config", response_model=LLMConfig)
def get_llm_config(db: Session = Depends(get_db)):
    """Get LLM configuration"""
    config = _get_llm_config(db)
    if not config:
        raise HTTPException(status_code=404, detail="LLM configuration not found. Create one first.")
    return config


@router.post("/llm/config", response_model=LLMConfig)
def create_or_update_llm_config(config_data: LLMConfigCreate, db: Session = Depends(get_db)):
    """Create or update LLM configuration"""
    try:
        existing = _get_llm_config(db)
        if existing:
            # exclude_unset: fields the client didn't send (e.g. jwt_token —
            # the UI never round-trips it) must not be nulled out on save.
            for key, value in config_data.model_dump(exclude_unset=True).items():
                setattr(existing, key, value)
            existing.config_key = "default"
            db.commit()
            db.refresh(existing)
            return existing
        else:
            new_config = LLMConfigModel(id=1, config_key="default", **config_data.model_dump())
            db.add(new_config)
            db.commit()
            db.refresh(new_config)
            return new_config
    except Exception as e:
        db.rollback()
        if "Duplicate key" in str(e) or "UNIQUE constraint" in str(e):
            try:
                db.rollback()
                existing = _get_llm_config(db)
                if existing:
                    for key, value in config_data.model_dump(exclude_unset=True).items():
                        setattr(existing, key, value)
                    existing.config_key = "default"
                    db.commit()
                    db.refresh(existing)
                    return existing
            except Exception as retry_error:
                db.rollback()
                raise HTTPException(status_code=500, detail=safe_error_response(retry_error, "LLM config update"))
        raise HTTPException(status_code=500, detail=safe_error_response(e, "LLM config creation"))


@router.patch("/llm/config", response_model=LLMConfig)
def update_llm_config(config_data: LLMConfigUpdate, db: Session = Depends(get_db)):
    """Partially update LLM configuration"""
    try:
        query = select(LLMConfigModel).where(LLMConfigModel.config_key == "default")
        config = db.execute(query).scalar_one_or_none()
        if not config:
            raise HTTPException(status_code=404, detail="LLM configuration not found. Create one first.")

        update_data = config_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(config, key, value)

        db.commit()
        db.refresh(config)
        return config
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=safe_error_response(e, "LLM config update"))


@router.delete("/llm/config")
def delete_llm_config(db: Session = Depends(get_db)):
    """Delete LLM configuration"""
    try:
        query = select(LLMConfigModel).where(LLMConfigModel.config_key == "default")
        config = db.execute(query).scalar_one_or_none()
        if not config:
            raise HTTPException(status_code=404, detail="LLM configuration not found")

        db.delete(config)
        db.commit()
        return {"status": "success", "message": "LLM configuration deleted"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=safe_error_response(e, "LLM config deletion"))


# ===== LLM QUEUE =====

@router.get("/llm/queue/status")
def get_llm_queue_status():
    """Get the current LLM queue status"""
    return llm_queue.get_queue_status()


@router.get("/llm/queue/job/{job_id}")
def get_llm_job_status(job_id: str):
    """Get status of a specific LLM job"""
    status = llm_queue.get_job_status(job_id)
    if not status:
        raise HTTPException(status_code=404, detail="Job not found")
    return status


@router.post("/llm/queue/submit")
def submit_llm_job(request: dict, db: Session = Depends(get_db)):
    """Submit an LLM request to the queue (async). Returns job_id for polling."""
    config = _get_llm_config(db)
    if not config:
        raise HTTPException(status_code=404, detail="LLM configuration not found")
    if not config.enabled:
        raise HTTPException(status_code=403, detail="LLM is not enabled")

    messages = request.get('messages', [])
    if not messages:
        raise HTTPException(status_code=400, detail="Messages are required")

    api_url, headers, payload = _prepare_llm_request(config, messages)
    job_id = llm_queue.submit_job(
        messages=messages,
        provider=config.provider,
        api_url=api_url,
        headers=headers,
        payload=payload,
        priority=request.get('priority', 0)
    )

    return {
        "job_id": job_id,
        "status": "pending",
        "queue_position": len(llm_queue.pending_queue),
        "message": "Job submitted. Poll /llm/queue/job/{job_id} for status."
    }


@router.post("/llm/complete")
def llm_complete(request: dict, db: Session = Depends(get_db)):
    """Proxy LLM completion requests through the backend with queue management (blocking)."""
    import time

    config = _get_llm_config(db)
    if not config:
        raise HTTPException(status_code=404, detail="LLM configuration not found. Configure LLM first.")
    if not config.enabled:
        raise HTTPException(status_code=403, detail="LLM is not enabled")

    messages = request.get('messages', [])
    if not messages:
        raise HTTPException(status_code=400, detail="Messages are required")

    api_url, headers, payload = _prepare_llm_request(config, messages)
    job_id = llm_queue.submit_job(
        messages=messages,
        provider=config.provider,
        api_url=api_url,
        headers=headers,
        payload=payload,
        priority=request.get('priority', 0)
    )

    max_wait = 120
    waited = 0
    while not llm_queue.can_process_now() and waited < max_wait:
        time.sleep(0.5)
        waited += 0.5

    if waited >= max_wait:
        raise HTTPException(status_code=503, detail="Queue timeout - too many pending requests")

    job = llm_queue.jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=500, detail="Job not found after submission")

    try:
        llm_queue.pending_queue.remove(job_id)
    except ValueError:
        pass

    job.status = JobStatus.PROCESSING
    job.started_at = datetime.utcnow()
    llm_queue.active_requests += 1
    llm_queue.last_request_time = time.time()

    try:
        result = llm_queue.process_job_sync(job)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=safe_error_response(e, "LLM request"))


@router.post("/llm/test-connection")
def test_llm_connection(request: dict = None):
    """Probe the configured LLM through the real request path (queue + provider
    handling). Body: {"role": "analyst" | "writer"}. The writer role exercises
    the writer model's endpoint/auth so a broken two-model config is caught
    here instead of mid-analysis."""
    from ..pcap import llm_bridge  # local import: llm_bridge imports this module

    role = (request or {}).get("role", "analyst")
    if role not in ("analyst", "writer"):
        raise HTTPException(status_code=400, detail="role must be 'analyst' or 'writer'")
    return llm_bridge.test_connection(role=role)


# ===== LLM BATCH =====

@router.post("/llm/batch/submit")
def submit_llm_batch(request: dict, db: Session = Depends(get_db)):
    """Submit multiple LLM requests as a batch (async)."""
    config = _get_llm_config(db)
    if not config:
        raise HTTPException(status_code=404, detail="LLM configuration not found")
    if not config.enabled:
        raise HTTPException(status_code=403, detail="LLM is not enabled")

    requests_list = request.get('requests', [])
    if not requests_list:
        raise HTTPException(status_code=400, detail="No requests provided")
    if len(requests_list) > 50:
        raise HTTPException(status_code=400, detail="Maximum 50 requests per batch")

    for idx, req in enumerate(requests_list):
        if not req.get('messages'):
            raise HTTPException(status_code=400, detail=f"Request {idx} missing messages")

    sample_messages = requests_list[0].get('messages', [])
    api_url, headers, base_payload = _prepare_llm_request(config, sample_messages)
    base_payload.pop('messages', None)

    use_parallel = request.get('parallel', True)
    if use_parallel:
        batch_result = llm_queue.submit_batch_parallel(
            requests=requests_list, provider=config.provider,
            api_url=api_url, headers=headers, base_payload=base_payload
        )
    else:
        batch_result = llm_queue.submit_batch(
            requests=requests_list, provider=config.provider,
            api_url=api_url, headers=headers, base_payload=base_payload
        )

    return batch_result


@router.get("/llm/batch/status")
def get_llm_batch_status(
    job_ids: str = Query(..., description="Comma-separated list of job IDs")
):
    """Get status of multiple jobs (batch status)."""
    job_id_list = [jid.strip() for jid in job_ids.split(',') if jid.strip()]
    if not job_id_list:
        raise HTTPException(status_code=400, detail="No job IDs provided")
    if len(job_id_list) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 job IDs per request")
    return llm_queue.get_batch_status(job_id_list)


@router.post("/llm/batch/wait")
def wait_for_llm_batch(
    request: dict,
    timeout: float = Query(120.0, description="Maximum time to wait in seconds")
):
    """Wait for a batch of jobs to complete (blocking)."""
    job_ids = request.get('job_ids', [])
    if not job_ids:
        raise HTTPException(status_code=400, detail="No job IDs provided")
    if len(job_ids) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 job IDs per request")

    timeout = min(timeout, 300.0)
    return llm_queue.wait_for_batch(job_ids, timeout=timeout)


@router.post("/llm/batch/complete")
def llm_batch_complete(request: dict, db: Session = Depends(get_db)):
    """Submit batch and wait for all results (blocking)."""
    config = _get_llm_config(db)
    if not config:
        raise HTTPException(status_code=404, detail="LLM configuration not found")
    if not config.enabled:
        raise HTTPException(status_code=403, detail="LLM is not enabled")

    requests_list = request.get('requests', [])
    if not requests_list:
        raise HTTPException(status_code=400, detail="No requests provided")
    if len(requests_list) > 20:
        raise HTTPException(status_code=400, detail="Maximum 20 requests for blocking batch")

    timeout = min(request.get('timeout', 120), 300.0)

    for idx, req in enumerate(requests_list):
        if not req.get('messages'):
            raise HTTPException(status_code=400, detail=f"Request {idx} missing messages")

    sample_messages = requests_list[0].get('messages', [])
    api_url, headers, base_payload = _prepare_llm_request(config, sample_messages)
    base_payload.pop('messages', None)

    batch_result = llm_queue.submit_batch_parallel(
        requests=requests_list, provider=config.provider,
        api_url=api_url, headers=headers, base_payload=base_payload
    )

    job_ids = [job['job_id'] for job in batch_result['jobs']]
    final_status = llm_queue.wait_for_batch(job_ids, timeout=timeout)

    return {"batch_id": batch_result['batch_id'], "status": final_status}
