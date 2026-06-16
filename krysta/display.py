import time

RULE_DISPLAY_NAMES = {
    "NoNetworkCallsRule": "no_network_calls",
    "ExitCodeZeroRule": "exit_code_zero",
    "NoFilesystemAccessRule": "no_filesystem_access",
    "MemoryLimitRule": "memory_limit",
    "ValidJsonRule": "valid_json",
}

async def run_with_display(sandbox, code=None, code_path=None, language="python", timeout_ms=10000):
    import json as _json

    job_id_holder = {}
    start_time = time.time()
    stdout_buffer = []

    print(f" KRYSTA RUN")
    print(f" Spawning stateful sandbox ({language}:3.11-alpine)... ", end="", flush=True)

    rules_result = []
    final_status = None


    async for event in sandbox.execute(code=code, code_path=code_path, language=language, timeout_ms=timeout_ms):
        print(f"[DEBUG] etype={event['type']} text={event.get('text')}")
        etype = event["type"]

        if etype == "system" and event["text"] == "EXECUTION_STARTED":
            print("[OK]")
            if sandbox.session_id:
                print(f" Session mounted: session_id={sandbox.session_id}")
            print(f"[STREAM] executing...")
            print("-" * 67)

        elif etype == "stdout":
            print(event["text"])
            stdout_buffer.append(event["text"])

        elif etype == "stderr":
            print(event["text"])

        elif etype == "rules":
            rules_result = _json.loads(event["text"])
            # print(f"[DEBUG RULES] parsed {len(rules_result)} rules")

        elif etype in ("done", "timeout", "error"):
            final_status = etype

    elapsed = time.time() - start_time
    print("-" * 67)

    if final_status == "done":
        print(f" DONE      Execution finished in {elapsed:.2f}s")
    elif final_status == "timeout":
        print(f" TIMEOUT   Execution exceeded time limit ({elapsed:.2f}s)")
    else:
        print(f" ERROR     Execution failed ({elapsed:.2f}s)")

    security_rules = [r for r in rules_result if r.get("category") == "security"]
    optional_rules = [r for r in rules_result if r.get("category") == "optional"]

    print(f" VALIDATE  Running security policies...")
    all_security_passed = True
    for rule in security_rules:
        name = RULE_DISPLAY_NAMES.get(rule["rule"], rule["rule"])
        status = "PASS" if rule["result"] == "PASS" else "FAIL"
        print(f"  |  {status} {name:<22} ({rule['reason']})")
        if rule["result"] != "PASS":
            all_security_passed = False

    if optional_rules:
        print(f" CHECKS    Optional output checks (informational)...")
        for rule in optional_rules:
            name = RULE_DISPLAY_NAMES.get(rule["rule"], rule["rule"])
            status = "PASS" if rule["result"] == "PASS" else "SKIP"
            print(f"  |  {status} {name:<22} ({rule['reason']})")

    print()
    if all_security_passed:
        print(f" SUCCESS   All security checks passed. Safe to execute.")
    else:
        print(f" BLOCKED   Security policy violation. Execution unsafe.")

    return {"status": final_status, "stdout": stdout_buffer, "rules": rules_result}