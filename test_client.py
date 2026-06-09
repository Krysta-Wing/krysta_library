import asyncio
import json
from krysta.noa import Noa

GATEWAY_URL = "http://localhost:3000"

async def test_noa_intelligence(name, code, expected_rule_result):
    print(f"\n============================================================")
    print(f"TESTING NOA INTEL: {name}")
    print(f"============================================================")
    
    async with Noa(gateway_url=GATEWAY_URL) as claw:
        async for event in claw.execute(language="python", code=code, timeout_ms=3000):
            if event.get("type") == "rules":
                print(f"[RULE EVALUATION] -> {event.get('text')}")
            elif event.get("type") == "error":
                print(f"[SANDBOX ERROR] -> {event.get('text')}")
                
    print(f"EXPECTED NOA BEHAVIOR: {expected_rule_result}")

async def main():
    # 1. Testing Syntax Errors (Missing colons, bad indents)
    await test_noa_intelligence(
        "RAW SYNTAX FAILURE",
        """
def broken_function()
    print("Missing colon after function def!")
broken_function()
""",
        "ExitCodeZeroRule should FAIL. NoA must flag the syntax token crash."
    )

    # 2. Testing Logic Errors (Dividing by zero)
    await test_noa_intelligence(
        "ZERO DIVISION ERROR",
        """
x = 10
y = 0
result = x / y
print(result)
""",
        "ExitCodeZeroRule should FAIL. NoA must catch ZeroDivisionError in stderr."
    )

    # 3. Testing Infinite Loops (Watchdog timeout trigger)
    await test_noa_intelligence(
        "INFINITE LOOP HANG",
        """
import time
print("Entering endless trap...")
while True:
    pass
""",
        "TimeoutRule should FAIL. NoA must kill the task exactly at 3000ms."
    )

    # 4. Testing Bad JSON Outputs
    await test_noa_intelligence(
        "INVALID JSON FORMAT STRING",
        """
print("{'status': operational, elements: 5}") # Single quotes & unquoted keys
""",
        "ValidJsonRule should FAIL. NoA must recognize this is not valid global JSON."
    )

if __name__ == "__main__":
    asyncio.run(main())
