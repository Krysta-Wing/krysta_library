import json
from typing import Tuple, Dict
from .trace import ExecutionTrace

class ValidationRule:
    """Abstract base class for all sandbox evaluation rules."""
    def evaluate(self, trace: ExecutionTrace) -> Tuple[bool, str]:
        raise NotImplementedError


class ExitCodeZeroRule(ValidationRule):
    """Verifies that the sandboxed process wrapped up operations with a clean exit status."""
    def evaluate(self, trace: ExecutionTrace) -> Tuple[bool, str]:
        if trace.timeout_hit:
            return False, "Sandbox execution exceeded the allocated runtime wall clock limit."
        if trace.exit_code is None:
            return False, "Process terminated abruptly without returning a valid exit status code."
        if trace.exit_code != 0:
            return False, f"Process terminated with unhandled non-zero exit status: {trace.exit_code}."
        return True, "Process completed runtime operations cleanly with exit code 0."


class ValidJsonRule(ValidationRule):
    """Ensures the console stdout stream can be compiled into structured JSON metadata."""
    def evaluate(self, trace: ExecutionTrace) -> Tuple[bool, str]:
        # Collect and concatenate all stdout text chunks
        combined_output = "".join([
            line.get("text", "") 
            for line in trace.stdout_lines 
            if line.get("type") == "stdout"
        ])
        
        # Strip out system lifecycle banners injected by the daemon infrastructure
        clean_payload = combined_output.replace("SYSTEM // EXECUTION_STARTED", "").strip()
        
        if not clean_payload:
            return False, "Process stdout stream is completely empty. No data payload found to parse."
        
        try:
            json.loads(clean_payload)
            return True, "Stdout stream successfully compiled into valid structural JSON."
        except json.JSONDecodeError as e:
            return False, f"Malformed output layout. Failed to parse stream as structural JSON. Details: {str(e)}"


class NoNetworkCallsRule(ValidationRule):
    """Inspects log traces to detect unauthorized outbound socket connection attempts."""
    def evaluate(self, trace: ExecutionTrace) -> Tuple[bool, str]:
        # Check standard low-level connection trace patterns and error string indicators
        for frame in trace.stdout_lines:
            text = frame.get("text", "").lower()
            if any(marker in text for marker in ["socket", "http", "connection refused", "urllib", "requests"]):
                return False, f"Security sandbox violation: Rogue external network handshake detected: '{frame.get('text')}'"
        return True, "No outbound socket or data link requests detected during script lifecycle tracking."


class RuleEngine:
    """Orchestrates sequential trace assessments against the configured ruleset profile."""
    def __init__(self):
        self.rules = [
            ExitCodeZeroRule(),
            ValidJsonRule(),
            NoNetworkCallsRule()
        ]

    def validate(self, trace: ExecutionTrace) -> Dict[str, any]:
        results = {}
        overall_passed = True
        
        for rule in self.rules:
            rule_name = rule.__class__.__name__
            passed, reason = rule.evaluate(trace)
            if not passed:
                overall_passed = False
            
            results[rule_name] = {
                "status": "PASS" if passed else "FAIL",
                "reason": reason
            }
            
        return {
            "passed": overall_passed,
            "results": results
        }