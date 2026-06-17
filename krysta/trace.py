import os
from dotenv import load_dotenv
from upstash_redis import Redis
from typing import List, Dict

load_dotenv(dotenv_path=".env.local", override=True)


class ExecutionTrace:
    def __init__(
        self,
        job_id: str,
        duration_ms: int = 0,
        stdout_lines: List[Dict] = None,
        exit_code: int = None,
        timeout_hit: bool = False,
        memory_used_mb: float = 0.0,
        filesystem_access_detected: bool = False
    ):
        self.job_id = job_id
        self.duration_ms = duration_ms
        self.stdout_lines = stdout_lines or []
        self.exit_code = exit_code
        self.timeout_hit = timeout_hit
        self.memory_used_mb = memory_used_mb
        self.filesystem_access_detected = filesystem_access_detected

    @classmethod
    def from_redis(cls, job_id: str):
        redis_url = os.getenv("UPSTASH_REDIS_REST_URL")
        redis_token = os.getenv("UPSTASH_REDIS_REST_TOKEN")

        if not redis_url:
            raise ValueError("[TRACE] Missing UPSTASH_REDIS_REST_URL environment variable.")

        if not redis_token:
            raise ValueError("[TRACE] Missing UPSTASH_REDIS_REST_TOKEN environment variable.")

        client = Redis(url=redis_url, token=redis_token)

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

        duration_ms = 0
        raw_duration = client.get(f"metrics:duration:{job_id}")

        if raw_duration:
            try:
                duration_ms = int(raw_duration)
            except (TypeError, ValueError):
                pass

        memory_used_mb = 0.0
        raw_memory = client.get(f"metrics:memory:{job_id}")

        if raw_memory:
            try:
                memory_used_mb = float(raw_memory)
            except (TypeError, ValueError):
                pass

        filesystem_access_detected = False
        raw_fs = client.get(f"metrics:filesystem:{job_id}")

        if raw_fs:
            filesystem_access_detected = str(raw_fs).lower() == "true"

        timeout_hit = status == "timeout"

        try:
            exit_code = int(client.get(f"exitcode:{job_id}") or -1)
        except (TypeError, ValueError):
            exit_code = -1

        if timeout_hit:
            exit_code = None

        return cls(
            job_id=job_id,
            duration_ms=duration_ms,
            stdout_lines=stdout_lines,
            exit_code=exit_code,
            timeout_hit=timeout_hit,
            memory_used_mb=memory_used_mb,
            filesystem_access_detected=filesystem_access_detected
        )

    def to_dict(self) -> dict:
        return {
            "job_id": self.job_id,
            "duration_ms": self.duration_ms,
            "memory_used_mb": self.memory_used_mb,
            "filesystem_access_detected": self.filesystem_access_detected,
            "stdout_lines": self.stdout_lines,
            "exit_code": self.exit_code,
            "timeout_hit": self.timeout_hit
        }