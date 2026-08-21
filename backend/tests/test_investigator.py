from unittest.mock import MagicMock, patch

from app.core.investigator import (
    Hypothesis,
    InvestigationState,
    build_investigator_graph,
)


def make_fake_sandbox(file_contents: dict[str, str]) -> MagicMock:
    sandbox = MagicMock()
    sandbox.read_file.side_effect = lambda path: file_contents.get(
        path.replace("/workspace/repo/", "")
    )
    return sandbox


@patch("app.core.investigator.get_llm")
def test_investigator_stops_at_max_iterations_if_never_confident(mock_get_llm: MagicMock) -> None:
    # Every call returns low confidence — the loop should hit MAX_ITERATIONS
    # and stop there, never running forever. This is the exact safety net
    # we built after burning real API budget without one — worth locking
    # in with a test so it can never silently regress.
    mock_llm = MagicMock()
    mock_llm.with_structured_output.return_value.invoke.return_value = Hypothesis(
        reasoning="still not sure", target_file="app.py", confidence=0.1
    )
    mock_get_llm.return_value = mock_llm

    sandbox = make_fake_sandbox({"app.py": "def foo(): pass"})
    graph = build_investigator_graph(sandbox)

    initial_state: InvestigationState = {
        "issue_title": "test issue",
        "issue_body": "test body",
        "repo_map_summary": "app.py: functions: foo",
        "inspected_files": {},
        "hypothesis": "",
        "target_file": "",
        "confidence": 0.0,
        "iteration": 0,
        "history": [],
    }

    result = graph.invoke(initial_state)

    assert result["iteration"] == 5
    assert result["confidence"] < 0.75


@patch("app.core.investigator.get_llm")
def test_investigator_forces_at_least_one_inspection(mock_get_llm: MagicMock) -> None:
    # Even if the FIRST call claims high confidence, we should never trust
    # it before at least one real file has been inspected — this is the
    # calibration bug we caught by hand; this test makes sure it stays fixed.
    mock_llm = MagicMock()
    mock_llm.with_structured_output.return_value.invoke.return_value = Hypothesis(
        reasoning="very confident immediately", target_file="app.py", confidence=0.99
    )
    mock_get_llm.return_value = mock_llm

    sandbox = make_fake_sandbox({"app.py": "def foo(): pass"})
    graph = build_investigator_graph(sandbox)

    initial_state: InvestigationState = {
        "issue_title": "test issue",
        "issue_body": "test body",
        "repo_map_summary": "app.py: functions: foo",
        "inspected_files": {},
        "hypothesis": "",
        "target_file": "",
        "confidence": 0.0,
        "iteration": 0,
        "history": [],
    }

    result = graph.invoke(initial_state)

    assert len(result["inspected_files"]) >= 1
    assert "app.py" in result["inspected_files"]
