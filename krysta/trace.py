import json
import os
from dotenv import load_dotenv
from upstash_redis import Redis
from typing import List, Dict, Optional

load_dotenv(dotenv_path=".env.local")

class ExecutionTrace:
    def __init__(
        self,
        job_id: str,
        duration_ms: int = 0,
        stdout_lines: List[Dict] = None,
        exit_code: int = None,
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
        Connects to Upstash Redis via REST API, inspects the execution status,
        and maps the execution trace.
        """
        redis_url = os.getenv("UPSTASH_REDIS_REST_URL")
        redis_token = os.getenv("UPSTASH_REDIS_REST_TOKEN")

        if not redis_url:
            raise ValueError("[TRACE] Missing UPSTASH_REDIS_REST_URL environment variable.")
        if not redis_token:
            raise ValueError("[TRACE] Missing UPSTASH_REDIS_REST_TOKEN environment variable.")

        client = Redis(url=redis_url, token=redis_token)

        # Read the lifecycle state directly from the status key
        status = client.get(f"status:{job_id}") or "unknown"
        
        raw_lines = client.lrange(f"stdout:{job_id}", 0, -1) or []

        stdout_lines = [
           {
              "type": "stdout",
              "text": (
                  line.decode("utf-8")
                  if isinstance(line, bytes)
                  else line
               ).strip()
            }
            for line in raw_lines
        ]

        # Read persisted duration metric
        raw_lines = client.lrange(f"stdout:{job_id}", 0, -1) or []

        stdout_lines = [
              {
                 "type": "stdout",
                 "text": (
                    line.decode("utf-8")
                    if isinstance(line, bytes)
                    else line
                 ).strip()
              }
              for line in raw_lines
        ]

        duration_ms = 0
        timeout_hit = (status == "timeout")

        try:
          exit_code = int(client.get(f"exitcode:{job_id}") or -1)
        except (TypeError, ValueError):
          exit_code = -1

        if status == "timeout":
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