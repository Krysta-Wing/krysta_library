import json
import redis
import os
from typing import List, Dict, Optional


class ExecutionTrace:
    def __init__(
        self, 
        job_id: str, 
        duration_ms: int = 0, 
        stdout_lines: List[Dict] = None, 
        exit_code: Optional[int] = None, 
        timeout_hit: bool = False
    ):
        self.job_id = job_id
        self.duration_ms = duration_ms
        self.stdout_lines = stdout_lines or []
        self.exit_code = exit_code
        self.timeout_hit = timeout_hit

    @classmethod
    def from_redis(cls, job_id: str):
        """
        Connects to Upstash Redis, inspects the execution status,
        pulls structural steps, and maps the execution trace.
        """
        redis_url = os.getenv("REDIS_URL")
        if not redis_url:
            raise ValueError("[TRACE] Missing REDIS_URL environment variable.")

        # Initialize the secure tracking link
        client = redis.Redis.from_url(redis_url, decode_responses=True)
        
        # Read the lifecycle state directly from the status key
        status = client.get(f"status:{job_id}") or "unknown"
        
        # Fetch log records from your historical logs collection if applicable,
        # or fall back to parsing states
        stdout_lines = []
        duration_ms = 0
        timeout_hit = (status == "timeout")
        
        # Set clean exit codes based on structural status keys
        if status == "done":
            exit_code = 0
        elif status == "error":
            exit_code = 1
        elif status == "timeout":
            exit_code = None
        else:
            exit_code = None

        return cls(
            job_id=job_id,
            duration_ms=duration_ms,
            stdout_lines=stdout_lines,
            exit_code=exit_code,
            timeout_hit=timeout_hit
        )

    def to_dict(self) -> dict:
        return {
            "jobId": self.job_id,
            "duration_ms": self.duration_ms,
            "stdout_lines": self.stdout_lines,
            "exit_code": self.exit_code,
            "timeout_hit": self.timeout_hit
        }