import asyncio
from krysta import Claw

async def main():
    # 1. Initialize the pristine SDK surface targeting your active cluster
    client = Claw(gateway_url="http://localhost:3000")
    
    print("[1/3] Dispatching script execution block to sandbox...")
    
    # 2. Execute a valid Python payload using the automated orchestration wrapper
    trace = await client.execute(
        language="python",
        code='print("{\\"status\\": \\"healthy\\", \\"processed_nodes\\": 24}")'
    )
    
    print(f"\n[2/3] Execution closed out in {trace.duration_ms}ms with code: {trace.exit_code}")
    
    # 3. Pass the trace telemetry through the validator rule engine
    report = client.validate(trace)
    print(f"[3/3] Overall Sandbox Verification Result -> {report['passed']}")
    print(f"Detailed Rule Breakdown: {report['results']}")

if __name__ == "__main__":
    asyncio.run(main())