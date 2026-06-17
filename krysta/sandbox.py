

import json
from typing import Tuple, Dict
from .trace import ExecutionTrace


class ValidationRule:
    """Abstract base class for all sandbox evaluation rules."""
    def evaluate(self, trace: ExecutionTrace) -> Tuple[bool, str]:
        raise NotImplementedError


class ExitCodeZeroRule(ValidationRule):
    """Process must exit cleanly."""
    def evaluate(self, trace: ExecutionTrace) -> Tuple[bool, str]:
        if trace.timeout_hit:
            return False, "Sandbox execution exceeded runtime limit"

        if trace.exit_code is None:
            return False, "No exit code available"

        if trace.exit_code != 0:
            return False, f"Process exited with code {trace.exit_code}"

        return True, "Exit code clean"


class ValidJsonRule(ValidationRule):
    """Stdout should be valid JSON (optional rule)."""
    def evaluate(self, trace: ExecutionTrace) -> Tuple[bool, str]:
        combined_output = "".join(
            [
                line.get("text", "")
                for line in trace.stdout_lines
                if line.get("type") == "stdout"
            ]
        )

        clean_payload = combined_output.replace(
            "SYSTEM // EXECUTION_STARTED",
            ""
        ).strip()

        if not clean_payload:
            return False, "Empty stdout"

        try:
            json.loads(clean_payload)
            return True, "Valid JSON"
        except json.JSONDecodeError:
            return False, "Invalid JSON"


class NoNetworkCallsRule(ValidationRule):
    """Detect outbound network activity."""
    def evaluate(self, trace: ExecutionTrace) -> Tuple[bool, str]:
        for frame in trace.stdout_lines:
            text = frame.get("text", "").lower()

            if any(
                marker in text
                for marker in [
                    "socket",
                    "http",
                    "urllib",
                    "requests",
                    "connection refused"
                ]
            ):
                return False, "Network activity detected"

        return True, "No network activity"


class MemoryLimitRule(ValidationRule):
    """Verify memory usage remains below 128 MB."""
    def evaluate(self, trace: ExecutionTrace) -> Tuple[bool, str]:
        if trace.memory_used_mb > 128:
            return False, "Memory limit exceeded"

        return True, "Memory usage within limits"


class NoFilesystemAccessRule(ValidationRule):
    """Verify no filesystem access occurred."""
    def evaluate(self, trace: ExecutionTrace) -> Tuple[bool, str]:
        if trace.filesystem_access_detected:
            return False, "Filesystem access detected"

        return True, "No filesystem access detected"


class RuleEngine:
    """Runs all validation rules and produces final report."""

    OPTIONAL_RULES = {
        "ValidJsonRule"
    }

    def __init__(self):
        self.rules = [
            ExitCodeZeroRule(),
            ValidJsonRule(),
            NoNetworkCallsRule(),
            MemoryLimitRule(),
            NoFilesystemAccessRule()
        ]

    def validate(self, trace: ExecutionTrace) -> Dict[str, any]:
        results = {}
        overall_passed = True

        for rule in self.rules:
            rule_name = rule.__class__.__name__

            passed, _ = rule.evaluate(trace)

            # Optional rules do not affect overall status
            if not passed and rule_name not in self.OPTIONAL_RULES:
                overall_passed = False

            results[rule_name] = "PASS" if passed else "FAIL"

        return {
            "passed": overall_passed,
            "results": results
        }