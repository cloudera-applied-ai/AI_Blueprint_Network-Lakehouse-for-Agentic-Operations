"""
LLM Request Queue Service
Manages a queue of LLM requests with rate limiting and concurrent execution control.
Supports parallel processing of multiple LLM requests.
"""
import asyncio
import httpx
import uuid
import time
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import deque
import threading
from concurrent.futures import ThreadPoolExecutor, Future

from .net import ssl_context


class JobStatus(str, Enum):
    PENDING = "pending"
    QUEUED = "queued"  # In queue waiting for worker
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class LLMJob:
    """Represents a single LLM request job"""
    id: str
    messages: List[Dict[str, str]]
    created_at: datetime
    status: JobStatus = JobStatus.PENDING
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    priority: int = 0  # Higher = more priority
    future: Optional[Future] = None  # For tracking async execution

    # Request configuration
    provider: str = "cloudera"
    api_url: str = ""
    headers: Dict[str, str] = field(default_factory=dict)
    payload: Dict[str, Any] = field(default_factory=dict)


class LLMQueueService:
    """
    Manages LLM request queue with:
    - Configurable concurrent request limit
    - Rate limiting (requests per second)
    - Priority queue support
    - Job status tracking
    - Parallel processing via thread pool
    - Background worker for async job processing
    """

    def __init__(
        self,
        max_concurrent: int = 3,
        rate_limit_per_second: float = 2.0,
        request_timeout: float = 90.0,
        max_retries: int = 3
    ):
        self.max_concurrent = max_concurrent
        self.rate_limit_per_second = rate_limit_per_second
        self.request_timeout = request_timeout
        self.max_retries = max_retries

        # Job storage
        self.jobs: Dict[str, LLMJob] = {}
        self.pending_queue: deque = deque()

        # Rate limiting
        self.last_request_time: float = 0
        self.active_requests: int = 0

        # Thread pool for parallel LLM requests
        self.executor = ThreadPoolExecutor(max_workers=max_concurrent, thread_name_prefix="llm_worker")

        # Background worker control
        self.worker_running = False
        self.worker_thread: Optional[threading.Thread] = None

        # Threading lock for thread-safe operations
        self.lock = threading.Lock()

        # Persistent HTTP client with connection pooling
        self._http_client: Optional[httpx.Client] = None
        self._client_lock = threading.Lock()

        # Stats
        self.stats = {
            "total_submitted": 0,
            "total_completed": 0,
            "total_failed": 0,
            "total_timeout": 0,
            "total_retries": 0,
            "parallel_peak": 0,
        }

        print(f"🚀 LLM Queue Service initialized: max_concurrent={max_concurrent}, rate_limit={rate_limit_per_second}/s, max_retries={max_retries}, parallel=True")

    def submit_job(
        self,
        messages: List[Dict[str, str]],
        provider: str,
        api_url: str,
        headers: Dict[str, str],
        payload: Dict[str, Any],
        priority: int = 0
    ) -> str:
        """
        Submit a new LLM request to the queue.
        Returns job ID for status polling.
        """
        job_id = str(uuid.uuid4())

        job = LLMJob(
            id=job_id,
            messages=messages,
            created_at=datetime.utcnow(),
            priority=priority,
            provider=provider,
            api_url=api_url,
            headers=headers,
            payload=payload,
        )

        with self.lock:
            self.jobs[job_id] = job
            self.pending_queue.append(job_id)
            self.stats["total_submitted"] += 1

        print(f"📥 Job {job_id[:8]} submitted (queue size: {len(self.pending_queue)}, active: {self.active_requests})")

        return job_id

    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of a job"""
        job = self.jobs.get(job_id)
        if not job:
            return None

        return {
            "id": job.id,
            "status": job.status.value,
            "created_at": job.created_at.isoformat(),
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "result": job.result,
            "error": job.error,
        }

    def get_queue_status(self) -> Dict[str, Any]:
        """Get overall queue status"""
        with self.lock:
            return {
                "pending": len(self.pending_queue),
                "active": self.active_requests,
                "max_concurrent": self.max_concurrent,
                "rate_limit": self.rate_limit_per_second,
                "stats": self.stats.copy(),
            }

    def can_process_now(self) -> bool:
        """Check if we can process a request now (rate limiting + concurrency)"""
        with self.lock:
            # Check concurrent limit
            if self.active_requests >= self.max_concurrent:
                return False

            # Check rate limit
            now = time.time()
            time_since_last = now - self.last_request_time
            min_interval = 1.0 / self.rate_limit_per_second

            if time_since_last < min_interval:
                return False

            return True

    def _get_next_job(self) -> Optional[LLMJob]:
        """Get next job from queue (priority aware)"""
        with self.lock:
            if not self.pending_queue:
                return None

            # For now, simple FIFO. Could implement priority queue later.
            job_id = self.pending_queue.popleft()
            job = self.jobs.get(job_id)

            if job and job.status == JobStatus.PENDING:
                job.status = JobStatus.PROCESSING
                job.started_at = datetime.utcnow()
                self.active_requests += 1
                self.last_request_time = time.time()
                return job

            return None

    def _complete_job(self, job: LLMJob, result: Optional[Dict], error: Optional[str] = None, timed_out: bool = False):
        """Mark a job as complete"""
        with self.lock:
            job.completed_at = datetime.utcnow()
            job.result = result
            job.error = error

            if error and timed_out:
                job.status = JobStatus.TIMEOUT
                self.stats["total_timeout"] += 1
            elif error:
                job.status = JobStatus.FAILED
                self.stats["total_failed"] += 1
            else:
                job.status = JobStatus.COMPLETED
                self.stats["total_completed"] += 1

            self.active_requests = max(0, self.active_requests - 1)

        status_emoji = "✅" if not error else "❌"
        print(f"{status_emoji} Job {job.id[:8]} completed (queue: {len(self.pending_queue)}, active: {self.active_requests})")

    def process_job_sync(self, job: LLMJob) -> Dict[str, Any]:
        """
        Process a single job synchronously.
        Used by the sync endpoint.
        """
        try:
            with httpx.Client(timeout=self.request_timeout, verify=ssl_context()) as client:
                response = client.post(
                    job.api_url,
                    json=job.payload,
                    headers=job.headers
                )
                response.raise_for_status()
                result = response.json()
                self._complete_job(job, result)
                return result

        except httpx.TimeoutException:
            error = f"Request timed out after {self.request_timeout}s"
            self._complete_job(job, None, error, timed_out=True)
            raise Exception(error)

        except httpx.HTTPStatusError as e:
            error = f"HTTP {e.response.status_code}: {e.response.text[:500]}"
            self._complete_job(job, None, error)
            raise Exception(error)

        except Exception as e:
            error = str(e)
            self._complete_job(job, None, error)
            raise

    async def process_job_async(self, job: LLMJob) -> Dict[str, Any]:
        """
        Process a single job asynchronously.
        Used by the async endpoint with polling.
        """
        try:
            async with httpx.AsyncClient(timeout=self.request_timeout, verify=ssl_context()) as client:
                response = await client.post(
                    job.api_url,
                    json=job.payload,
                    headers=job.headers
                )
                response.raise_for_status()
                result = response.json()
                self._complete_job(job, result)
                return result

        except httpx.TimeoutException:
            error = f"Request timed out after {self.request_timeout}s"
            self._complete_job(job, None, error, timed_out=True)
            raise Exception(error)

        except httpx.HTTPStatusError as e:
            error = f"HTTP {e.response.status_code}: {e.response.text[:500]}"
            self._complete_job(job, None, error)
            raise Exception(error)

        except Exception as e:
            error = str(e)
            self._complete_job(job, None, error)
            raise

    def cleanup_old_jobs(self, max_age_seconds: int = 300):
        """Remove completed/failed jobs older than max_age_seconds"""
        cutoff = datetime.utcnow()
        removed = 0

        with self.lock:
            jobs_to_remove = []
            for job_id, job in self.jobs.items():
                if job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.TIMEOUT]:
                    if job.completed_at:
                        age = (cutoff - job.completed_at).total_seconds()
                        if age > max_age_seconds:
                            jobs_to_remove.append(job_id)

            for job_id in jobs_to_remove:
                del self.jobs[job_id]
                removed += 1

        if removed > 0:
            print(f"🧹 Cleaned up {removed} old jobs")

    def _get_http_client(self) -> httpx.Client:
        """Get or create a persistent HTTP client with connection pooling."""
        with self._client_lock:
            if self._http_client is None or self._http_client.is_closed:
                # Create client with connection pooling and keepalive
                limits = httpx.Limits(
                    max_connections=self.max_concurrent * 2,
                    max_keepalive_connections=self.max_concurrent,
                    keepalive_expiry=30.0  # Keep connections alive for 30 seconds
                )
                self._http_client = httpx.Client(
                    timeout=httpx.Timeout(self.request_timeout, connect=10.0),
                    limits=limits,
                    http2=False,  # Stick with HTTP/1.1 for better compatibility
                    verify=ssl_context(),  # cluster-internal CA (CAII) lives in the system store
                )
                print("🔌 Created new HTTP client with connection pooling")
            return self._http_client

    def _close_http_client(self):
        """Close the HTTP client."""
        with self._client_lock:
            if self._http_client and not self._http_client.is_closed:
                self._http_client.close()
                self._http_client = None
                print("🔌 Closed HTTP client")

    def _worker_process_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Worker function to process a single job with retry logic.
        Runs in thread pool.
        """
        job = self.jobs.get(job_id)
        if not job:
            return None

        # Mark as processing
        with self.lock:
            job.status = JobStatus.PROCESSING
            job.started_at = datetime.utcnow()

        last_error = None
        timed_out = False
        for attempt in range(self.max_retries):
            try:
                client = self._get_http_client()
                response = client.post(
                    job.api_url,
                    json=job.payload,
                    headers=job.headers
                )
                response.raise_for_status()
                result = response.json()
                self._complete_job(job, result)
                return result

            except httpx.TimeoutException as e:
                # Don't retry timeouts: a generation that blew the read timeout
                # will do it again, and each retry re-runs the full request on
                # the GPU while the caller's wait budget keeps draining.
                last_error = f"Request timed out after {self.request_timeout}s"
                timed_out = True
                print(f"⏱️ LLM request timeout (non-retryable): {job.api_url}")
                break

            except httpx.ConnectError as e:
                last_error = f"Connection error: {str(e)}"
                print(f"🔴 LLM connection error (attempt {attempt + 1}/{self.max_retries}): {job.api_url} - {e}")
                # Reset client on connection error
                self._close_http_client()
                with self.lock:
                    self.stats["total_retries"] += 1

            except httpx.HTTPStatusError as e:
                # Don't retry on 4xx errors (client errors)
                if 400 <= e.response.status_code < 500:
                    last_error = f"HTTP {e.response.status_code}: {e.response.text[:500]}"
                    print(f"🔴 LLM HTTP error (non-retryable): {last_error}")
                    break
                # Retry on 5xx errors (server errors)
                last_error = f"HTTP {e.response.status_code}: {e.response.text[:500]}"
                print(f"🔴 LLM HTTP error (attempt {attempt + 1}/{self.max_retries}): {last_error}")
                with self.lock:
                    self.stats["total_retries"] += 1

            except Exception as e:
                last_error = f"Unexpected error: {str(e)}"
                print(f"🔴 LLM unexpected error (attempt {attempt + 1}/{self.max_retries}): {e}")
                with self.lock:
                    self.stats["total_retries"] += 1

            # Exponential backoff between retries
            if attempt < self.max_retries - 1:
                backoff = min(2 ** attempt, 10)  # 1s, 2s, 4s... max 10s
                print(f"⏳ Retrying in {backoff}s...")
                time.sleep(backoff)

        # All retries exhausted (or a non-retryable error broke the loop).
        # _complete_job handles status + stats classification.
        self._complete_job(job, None, last_error, timed_out=timed_out)
        return None

    def submit_and_process_parallel(
        self,
        messages: List[Dict[str, str]],
        provider: str,
        api_url: str,
        headers: Dict[str, str],
        payload: Dict[str, Any],
        priority: int = 0
    ) -> str:
        """
        Submit a job and start processing it in the thread pool.
        Returns job_id immediately - results retrieved via get_job_status().
        """
        job_id = self.submit_job(messages, provider, api_url, headers, payload, priority)
        job = self.jobs.get(job_id)

        if job:
            # Rate limit: compute the wait under the lock, sleep OUTSIDE it so
            # workers completing jobs (which need the lock) aren't stalled.
            while True:
                with self.lock:
                    now = time.time()
                    min_interval = 1.0 / self.rate_limit_per_second
                    wait_time = min_interval - (now - self.last_request_time)
                    if wait_time <= 0:
                        # Claim the slot
                        self.active_requests += 1
                        self.last_request_time = now

                        # Track peak parallelism
                        if self.active_requests > self.stats["parallel_peak"]:
                            self.stats["parallel_peak"] = self.active_requests
                        break
                time.sleep(wait_time)

            # Submit to thread pool
            job.status = JobStatus.QUEUED
            future = self.executor.submit(self._worker_process_job, job_id)
            job.future = future

            print(f"🔄 Job {job_id[:8]} submitted to parallel worker (active: {self.active_requests})")

        return job_id

    def start_background_worker(self):
        """
        Start background worker that processes queued jobs.
        Jobs submitted via submit_job() will be processed automatically.
        """
        if self.worker_running:
            return

        self.worker_running = True

        def worker_loop():
            print("🏃 Background worker started")
            last_cleanup = time.time()
            cleanup_interval = 60  # Cleanup old jobs every 60 seconds

            while self.worker_running:
                try:
                    # Check if we can process more jobs
                    if self.active_requests < self.max_concurrent and self.pending_queue:
                        # Check rate limit
                        with self.lock:
                            now = time.time()
                            min_interval = 1.0 / self.rate_limit_per_second
                            time_since_last = now - self.last_request_time

                            if time_since_last >= min_interval:
                                # Get next job
                                try:
                                    job_id = self.pending_queue.popleft()
                                except IndexError:
                                    time.sleep(0.1)
                                    continue

                                job = self.jobs.get(job_id)
                                if job and job.status == JobStatus.PENDING:
                                    self.active_requests += 1
                                    self.last_request_time = time.time()

                                    if self.active_requests > self.stats["parallel_peak"]:
                                        self.stats["parallel_peak"] = self.active_requests

                                    # Submit to thread pool
                                    job.status = JobStatus.QUEUED
                                    future = self.executor.submit(self._worker_process_job, job_id)
                                    job.future = future
                                    print(f"🔄 Worker processing job {job_id[:8]} (parallel: {self.active_requests})")

                    time.sleep(0.1)  # Small sleep to prevent busy loop

                    # Periodic cleanup of old completed/failed jobs
                    if time.time() - last_cleanup > cleanup_interval:
                        self.cleanup_old_jobs(max_age_seconds=300)
                        last_cleanup = time.time()

                except Exception as e:
                    print(f"❌ Worker error: {e}")
                    time.sleep(1)

            print("🛑 Background worker stopped")

        self.worker_thread = threading.Thread(target=worker_loop, daemon=True)
        self.worker_thread.start()

    def stop_background_worker(self):
        """Stop the background worker and close HTTP client"""
        self.worker_running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=5)
        # Close HTTP client on shutdown
        self._close_http_client()

    def wait_for_job(self, job_id: str, timeout: float = 120.0) -> Optional[Dict[str, Any]]:
        """
        Wait for a job to complete and return its result.
        Useful for blocking calls that want to use the queue.
        """
        result, _error = self.wait_for_job_outcome(job_id, timeout=timeout)
        return result

    def wait_for_job_outcome(
        self, job_id: str, timeout: float = 120.0
    ) -> tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Wait for a job and return (result, error).

        On success error is None. On failure result is None and error carries
        the real cause (HTTP status + body, connect error, timeout) so callers
        can surface it instead of a generic "failed in the queue" message.
        The waiter never mutates the job — a worker may still be running it.
        """
        job = self.jobs.get(job_id)
        if not job:
            return None, f"Job {job_id} not found in queue"

        start_time = time.time()
        while time.time() - start_time < timeout:
            if job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.TIMEOUT]:
                return job.result, job.error
            time.sleep(0.1)

        return None, (
            f"Gave up waiting after {timeout:.0f}s "
            f"(job still {job.status.value}; queue busy or endpoint slow)"
        )

    def submit_batch(
        self,
        requests: List[Dict[str, Any]],
        provider: str,
        api_url: str,
        headers: Dict[str, str],
        base_payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Submit multiple LLM requests as a batch.
        All requests are queued and processed in parallel up to max_concurrent limit.

        Args:
            requests: List of request dicts, each containing:
                - messages: List[Dict[str, str]] - The messages for this request
                - priority: int (optional) - Priority level (higher = more priority)
                - request_id: str (optional) - Custom ID for tracking
            provider: LLM provider name
            api_url: API endpoint URL
            headers: Request headers
            base_payload: Base payload template (messages will be merged)

        Returns:
            Dict with batch_id and list of job_ids
        """
        batch_id = f"batch-{uuid.uuid4().hex[:12]}"
        job_ids = []

        print(f"📦 Batch {batch_id}: Submitting {len(requests)} requests")

        for idx, request in enumerate(requests):
            messages = request.get('messages', [])
            priority = request.get('priority', 0)
            custom_id = request.get('request_id', f"{batch_id}-{idx}")

            # Create payload for this request
            payload = base_payload.copy()
            payload['messages'] = messages

            # Submit job
            job_id = self.submit_job(
                messages=messages,
                provider=provider,
                api_url=api_url,
                headers=headers,
                payload=payload,
                priority=priority
            )

            job_ids.append({
                "job_id": job_id,
                "request_id": custom_id,
                "index": idx
            })

        with self.lock:
            self.stats["total_submitted"] += len(requests) - len(requests)  # Already counted in submit_job

        print(f"📦 Batch {batch_id}: All {len(job_ids)} jobs queued")

        return {
            "batch_id": batch_id,
            "total_requests": len(requests),
            "jobs": job_ids,
            "status": "queued"
        }

    def get_batch_status(self, job_ids: List[str]) -> Dict[str, Any]:
        """
        Get status of multiple jobs (batch status).

        Returns aggregated status and individual job statuses.
        """
        statuses = []
        completed = 0
        failed = 0
        pending = 0
        processing = 0

        for job_id in job_ids:
            status = self.get_job_status(job_id)
            if status:
                statuses.append(status)
                if status['status'] == 'completed':
                    completed += 1
                elif status['status'] in ['failed', 'timeout']:
                    failed += 1
                elif status['status'] == 'processing':
                    processing += 1
                else:
                    pending += 1

        total = len(job_ids)
        all_done = (completed + failed) == total

        return {
            "total": total,
            "completed": completed,
            "failed": failed,
            "pending": pending,
            "processing": processing,
            "all_done": all_done,
            "success_rate": (completed / total * 100) if total > 0 else 0,
            "jobs": statuses
        }

    def wait_for_batch(
        self,
        job_ids: List[str],
        timeout: float = 300.0,
        poll_interval: float = 0.5
    ) -> Dict[str, Any]:
        """
        Wait for all jobs in a batch to complete.

        Args:
            job_ids: List of job IDs to wait for
            timeout: Maximum time to wait in seconds
            poll_interval: Time between status checks

        Returns:
            Batch status with all results
        """
        start_time = time.time()

        while time.time() - start_time < timeout:
            status = self.get_batch_status(job_ids)

            if status['all_done']:
                print(f"✅ Batch complete: {status['completed']}/{status['total']} succeeded")
                return status

            time.sleep(poll_interval)

        # Timeout - return current status
        status = self.get_batch_status(job_ids)
        status['timeout'] = True
        status['error'] = f"Batch timeout after {timeout}s"
        print(f"⏰ Batch timeout: {status['completed']}/{status['total']} completed")
        return status

    def submit_batch_parallel(
        self,
        requests: List[Dict[str, Any]],
        provider: str,
        api_url: str,
        headers: Dict[str, str],
        base_payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Submit batch and immediately start parallel processing.
        Jobs are submitted to the thread pool for concurrent execution.

        This is the fastest method for batch processing as it bypasses
        the background worker and directly uses the thread pool.
        """
        batch_id = f"batch-{uuid.uuid4().hex[:12]}"
        job_ids = []

        print(f"⚡ Batch {batch_id}: Fast parallel submit of {len(requests)} requests")

        for idx, request in enumerate(requests):
            messages = request.get('messages', [])
            priority = request.get('priority', 0)
            custom_id = request.get('request_id', f"{batch_id}-{idx}")

            # Create payload for this request
            payload = base_payload.copy()
            payload['messages'] = messages

            # Create job
            job_id = str(uuid.uuid4())
            job = LLMJob(
                id=job_id,
                messages=messages,
                created_at=datetime.utcnow(),
                priority=priority,
                provider=provider,
                api_url=api_url,
                headers=headers,
                payload=payload,
            )

            with self.lock:
                self.jobs[job_id] = job
                self.stats["total_submitted"] += 1

            # Respect rate limiting with small stagger
            with self.lock:
                now = time.time()
                min_interval = 1.0 / self.rate_limit_per_second
                time_since_last = now - self.last_request_time

                if time_since_last < min_interval:
                    wait_time = min_interval - time_since_last
                    time.sleep(wait_time)

                self.active_requests += 1
                self.last_request_time = time.time()

                if self.active_requests > self.stats["parallel_peak"]:
                    self.stats["parallel_peak"] = self.active_requests

            # Submit to thread pool immediately
            job.status = JobStatus.QUEUED
            future = self.executor.submit(self._worker_process_job, job_id)
            job.future = future

            job_ids.append({
                "job_id": job_id,
                "request_id": custom_id,
                "index": idx
            })

        print(f"⚡ Batch {batch_id}: All {len(job_ids)} jobs submitted to parallel workers")

        return {
            "batch_id": batch_id,
            "total_requests": len(requests),
            "jobs": job_ids,
            "status": "processing",
            "parallel": True
        }


# Global queue instance with parallel processing enabled
# OPTIMIZED: Reduced concurrency for GPU relief
llm_queue = LLMQueueService(
    max_concurrent=2,  # Reduced from 5 to 2 for GPU optimization
    rate_limit_per_second=1.0,  # Reduced from 5.0 to 1.0 for gentler GPU usage
    # Read timeout per request. Generous on purpose: a 2000-4000 token
    # generation on a small local endpoint (e.g. Ollama, which processes
    # requests serially by default) can easily exceed 90s when two jobs
    # land on it at once — and timeouts are not retried.
    request_timeout=180.0
)

# Start background worker automatically
llm_queue.start_background_worker()
