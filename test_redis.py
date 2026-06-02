from dotenv import load_dotenv
load_dotenv(dotenv_path=".env.local")
import os
from upstash_redis import Redis

client = Redis(url=os.getenv("UPSTASH_REDIS_REST_URL"), token=os.getenv("UPSTASH_REDIS_REST_TOKEN"))

job_id = "claw_job_1780372900586_4r255"  # last job id from your test
print("status:", client.get(f"status:{job_id}"))
print("stdout:", client.lrange(f"stdout:{job_id}", 0, -1))