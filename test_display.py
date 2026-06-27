from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest

_display_spec = spec_from_file_location(
    "krysta_display", Path(__file__).parent / "krysta" / "display.py"
)
assert _display_spec is not None
assert _display_spec.loader is not None
display = module_from_spec(_display_spec)
_display_spec.loader.exec_module(display)


class FakeSandbox:
    session_id = None

    async def execute(self, **_kwargs):
        yield {"type": "system", "text": "EXECUTION_STARTED"}
        yield {"type": "stdout_batch", "text": '["first", "second"]'}
        yield {"type": "done", "text": ""}


@pytest.mark.asyncio
async def test_run_with_display_handles_stdout_batch(capsys):
    result = await display.run_with_display(FakeSandbox(), code="print('ignored')")

    assert result["status"] == "done"
    assert result["stdout"] == ["first", "second"]
    output = capsys.readouterr().out
    assert "first" in output
    assert "second" in output
