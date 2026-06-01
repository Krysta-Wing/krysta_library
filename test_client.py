import asyncio
from krysta import Claw

async def main():
    # 1. Initialize the SDK pointing to your local Next.js api gateway server
    gateway_url = "http://localhost:3000"
    
    # Simple python code payload to run in the sandbox
    test_code = """
import time
print("SYSTEM // HELLO FROM KRYSTA PYTHON SDK")
for i in range(3):
    print(f"STEP // Processing batch index {i}")
    time.sleep(1)
print("SYSTEM // PASSING COMPLETE")
"""

    print(f"[TEST] Initializing Claw client targeting {gateway_url}...")
    
    # 2. Enter the persistent HTTP engine connection pool context manager loop
    async with Claw(gateway_url=gateway_url) as claw:
        try:
            print("[TEST] Submitting execution job block to pipeline queue...")
            
            # 3. Stream back logs from the worker daemon via SSE line-by-line
            async for event in claw.execute(language="python", code=test_code, timeout_ms=8000):
                # Clean CLI output logging
                event_type = event.get("type", "UNKNOWN").upper()
                text = event.get("text", "")
                
                if text:
                    print(f"[{event_type}] {text}")
                else:
                    print(f"[{event_type}] Lifecycle frame update received.")
                    
        except Exception as e:
            print(f"\n[TEST ERROR] Execution pipe crashed: {e}")

if __name__ == "__main__":
    # Run the async test event loop block
    asyncio.run(main())