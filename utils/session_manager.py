import threading
import uuid
import time
from dataclasses import dataclass
from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)

@dataclass
class GenerationJob:
    job_id: str
    url: str
    content_type: str
    model: str
    status: str  # "queued", "running", "completed", "failed"
    progress: float  # 0.0 to 1.0
    result: Optional[str] = None
    error: Optional[str] = None

class JobQueue:
    """
    Manages a queue of content generation jobs to prevent GPU overload
    by limiting concurrent LLM requests.
    """
    def __init__(self, max_concurrent: int = 1):
        self.max_concurrent = max_concurrent
        self.jobs: Dict[str, GenerationJob] = {}
        self._lock = threading.Lock()
        self._running_count = 0

    def submit(self, url: str, content_type: str, model: str, processing_func) -> str:
        """
        Submit a new job to the queue.
        :param processing_func: The function that actually performs the generation.
                                It should accept (job_id, queue_instance) to update progress.
        """
        job_id = str(uuid.uuid4())[:8]
        job = GenerationJob(
            job_id=job_id, 
            url=url, 
            content_type=content_type, 
            model=model, 
            status="queued", 
            progress=0.0
        )
        
        with self._lock:
            self.jobs[job_id] = job
            
        # Start processing in a separate thread
        thread = threading.Thread(target=self._process, args=(job_id, processing_func), daemon=True)
        thread.start()
        
        return job_id

    def _process(self, job_id: str, processing_func):
        # Wait for a slot in the concurrency limit
        while True:
            with self._lock:
                if self._running_count < self.max_concurrent:
                    self._running_count += 1
                    self.jobs[job_id].status = "running"
                    break
            time.sleep(0.5)

        try:
            # Execute the passed processing function
            # The function is responsible for calling update_progress
            result = processing_func(job_id, self)
            
            with self._lock:
                self.jobs[job_id].result = result
                self.jobs[job_id].status = "completed"
                self.jobs[job_id].progress = 1.0
                
        except Exception as e:
            logger.error(f"Job {job_id} failed: {e}", exc_info=True)
            with self._lock:
                self.jobs[job_id].status = "failed"
                self.jobs[job_id].error = str(e)
        finally:
            with self._lock:
                self._running_count -= 1

    def update_progress(self, job_id: str, progress: float):
        """Update the progress percentage for a specific job."""
        with self._lock:
            if job_id in self.jobs:
                self.jobs[job_id].progress = min(progress, 1.0)
                logger.debug(f"Job {job_id} progress: {progress*100:.1f}%")

    def get_job_status(self, job_id: str) -> Optional[GenerationJob]:
        """Get the current state of a job."""
        with self._lock:
            return self.jobs.get(job_id)

    def get_all_jobs(self):
        """Return all jobs for queue monitoring."""
        with self._lock:
            return list(self.jobs.values())
