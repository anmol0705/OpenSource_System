from unittest.mock import MagicMock, patch

import pytest

from app.core.cost_tracker import RunCostExceededError, RunCostTracker
from app.core.implementer import (
    ImplementationState,
    Patch,
    build_implementation_graph,
)


def make_fake_sandbox() -> MagicMock:
    return MagicMock()


def make_structured_llm_mock(patch_result: Patch) -> MagicMock:
    mock_llm = MagicMock()
    raw_message = MagicMock()
    raw_message.usage_metadata = {"input_tokens": 100, "output_tokens": 200}
    mock_llm.with_structured_output.return_value.invoke.return_value = {
        "raw": raw_message,
        "parsed": patch_result,
    }
    return mock_llm


def make_initial_state(
    test_command: str = "pytest", target_file: str = "app.py"
) -> ImplementationState:
    return {
        "issue_title": "test issue",
        "issue_body": "test body",
        "target_file": target_file,
        "original_content": "def foo(): return 1",
        "current_content": "def foo(): return 1",
        "test_command": test_command,
        "test_output": "",
        "tests_passed": False,
        "teaching_summary": "",
        "iteration": 0,
        "history": [],
        "skill_context": "junior developer",
    }


@patch("app.core.implementer.get_llm")
def test_implementer_stops_immediately_when_first_attempt_passes(mock_get_llm: MagicMock) -> None:
    mock_get_llm.return_value = make_structured_llm_mock(
        Patch(
            explanation="fixed it",
            new_file_content="def foo(): return 2",
            teaching_summary="lesson",
        )
    )

    sandbox = make_fake_sandbox()
    sandbox.run_tests.return_value = (True, "")

    cost_tracker = RunCostTracker()
    graph = build_implementation_graph(sandbox, cost_tracker)

    result = graph.invoke(make_initial_state())

    assert result["tests_passed"] is True
    assert result["iteration"] == 1
    sandbox.run_tests.assert_called_once()


@patch("app.core.implementer.get_llm")
def test_implementer_retries_with_test_output_and_stops_at_max_iterations(
    mock_get_llm: MagicMock,
) -> None:
    mock_get_llm.return_value = make_structured_llm_mock(
        Patch(
            explanation="attempt",
            new_file_content="def foo(): return 2",
            teaching_summary="lesson",
        )
    )

    sandbox = make_fake_sandbox()
    sandbox.run_tests.return_value = (False, "AssertionError: expected 2, got 1")

    cost_tracker = RunCostTracker()
    graph = build_implementation_graph(sandbox, cost_tracker)

    result = graph.invoke(make_initial_state())

    assert result["tests_passed"] is False
    from app.core.implementer import MAX_IMPLEMENTATION_ITERATIONS

    assert result["iteration"] == MAX_IMPLEMENTATION_ITERATIONS
    assert sandbox.run_tests.call_count == MAX_IMPLEMENTATION_ITERATIONS


@patch("app.core.implementer.get_llm")
def test_disallowed_target_file_is_rejected_without_writing(mock_get_llm: MagicMock) -> None:
    mock_get_llm.return_value = make_structured_llm_mock(
        Patch(explanation="attempt", new_file_content="malicious", teaching_summary="lesson")
    )

    sandbox = make_fake_sandbox()

    cost_tracker = RunCostTracker()
    graph = build_implementation_graph(sandbox, cost_tracker)

    state = make_initial_state(target_file="../../etc/passwd")
    result = graph.invoke(state)

    sandbox.write_file.assert_not_called()
    assert result["tests_passed"] is False
    assert "Refused" in result["test_output"]


@patch("app.core.implementer.get_llm")
def test_disallowed_test_command_is_rejected_without_running(mock_get_llm: MagicMock) -> None:
    mock_get_llm.return_value = make_structured_llm_mock(
        Patch(
            explanation="attempt",
            new_file_content="def foo(): return 2",
            teaching_summary="lesson",
        )
    )

    sandbox = make_fake_sandbox()

    cost_tracker = RunCostTracker()
    graph = build_implementation_graph(sandbox, cost_tracker)

    state = make_initial_state(test_command="rm -rf /")
    result = graph.invoke(state)

    sandbox.run_tests.assert_not_called()
    assert result["tests_passed"] is False
    assert "Refused" in result["test_output"]


def test_cost_tracker_raises_when_exceeding_ceiling() -> None:
    tracker = RunCostTracker(max_estimated_cost_usd=0.01)

    with pytest.raises(RunCostExceededError):
        tracker.record_usage(input_tokens=100_000, output_tokens=100_000)


def test_cost_tracker_does_not_raise_when_under_ceiling() -> None:
    tracker = RunCostTracker(max_estimated_cost_usd=0.50)

    tracker.record_usage(input_tokens=100, output_tokens=100)

    assert tracker.total_cost_usd < 0.50
