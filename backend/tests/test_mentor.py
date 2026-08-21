import uuid
from unittest.mock import MagicMock, patch

from httpx import ASGITransport, AsyncClient

from app.core.cost_tracker import RunCostTracker
from app.core.mentor import (
    MAX_HINTS,
    Hint,
    MentorState,
    build_mentor_resume_graph,
    build_mentor_start_graph,
    make_generate_hint_node,
    should_continue_mentoring,
)
from app.core.sandbox import get_sandbox_manager
from app.main import app


def make_fake_sandbox() -> MagicMock:
    return MagicMock()


def make_hint_llm_mock(hint: Hint) -> MagicMock:
    mock_llm = MagicMock()
    mock_llm.with_structured_output.return_value.invoke.return_value = hint
    return mock_llm


def make_state(
    proficiency: str = "intermediate",
    hint_count: int = 0,
    hints_given: list[str] | None = None,
    reference_solution: str = "def foo(): return 2",
    human_attempt: str = "",
    test_command: str = "pytest",
) -> MentorState:
    return {
        "issue_title": "off-by-one bug",
        "issue_body": "foo() returns the wrong value",
        "target_file": "app.py",
        "original_content": "def foo(): return 1",
        "reference_solution": reference_solution,
        "human_attempt": human_attempt,
        "test_command": test_command,
        "test_output": "",
        "tests_passed": False,
        "proficiency": proficiency,
        "hint_count": hint_count,
        "hints_given": hints_given if hints_given is not None else [],
    }


@patch("app.core.mentor.get_llm")
def test_first_hint_does_not_reveal_solution(mock_get_llm: MagicMock) -> None:
    mock_llm = make_hint_llm_mock(
        Hint(hint_text="think about the loop bound", reveals_solution=False)
    )
    mock_get_llm.return_value = mock_llm

    generate_hint = make_generate_hint_node()
    result = generate_hint(make_state(hint_count=0))

    prompt = mock_llm.with_structured_output.return_value.invoke.call_args[0][0]
    assert "Do NOT reveal the fix. reveals_solution must be false." in prompt
    assert "safety-valve reveal" not in prompt
    assert result["hint_count"] == 1
    assert result["hints_given"] == ["think about the loop bound"]


@patch("app.core.mentor.get_llm")
def test_hint_style_differs_by_proficiency(mock_get_llm: MagicMock) -> None:
    mock_llm = make_hint_llm_mock(Hint(hint_text="hint", reveals_solution=False))
    mock_get_llm.return_value = mock_llm

    generate_hint = make_generate_hint_node()

    generate_hint(make_state(proficiency="beginner", hint_count=0))
    beginner_prompt = mock_llm.with_structured_output.return_value.invoke.call_args[0][0]
    assert "Be generous" in beginner_prompt

    generate_hint(make_state(proficiency="advanced", hint_count=0))
    advanced_prompt = mock_llm.with_structured_output.return_value.invoke.call_args[0][0]
    assert "single probing question" in advanced_prompt

    assert beginner_prompt != advanced_prompt


@patch("app.core.mentor.get_llm")
def test_max_hints_forces_reveal(mock_get_llm: MagicMock) -> None:
    mock_llm = make_hint_llm_mock(Hint(hint_text="here's the fix", reveals_solution=True))
    mock_get_llm.return_value = mock_llm

    generate_hint = make_generate_hint_node()
    generate_hint(make_state(hint_count=MAX_HINTS))

    prompt = mock_llm.with_structured_output.return_value.invoke.call_args[0][0]
    assert "safety-valve reveal" in prompt
    assert "Set reveals_solution=true" in prompt


def test_passing_attempt_routes_to_end_not_generate_hint() -> None:
    still_failing = make_state(hints_given=["h1"])
    assert should_continue_mentoring(still_failing) == "generate_hint"

    passing = make_state()
    passing["tests_passed"] = True
    assert should_continue_mentoring(passing) == "end"


@patch("app.core.mentor.get_llm")
def test_resume_graph_skips_hint_generation_for_passing_attempt(mock_get_llm: MagicMock) -> None:
    mock_llm = make_hint_llm_mock(Hint(hint_text="unused", reveals_solution=False))
    mock_get_llm.return_value = mock_llm

    sandbox = make_fake_sandbox()
    sandbox.run_tests.return_value = (True, "")

    graph = build_mentor_resume_graph(sandbox)
    state = make_state(
        human_attempt="def foo(): return 2", hint_count=1, hints_given=["earlier hint"]
    )

    result = graph.invoke(state)

    mock_llm.with_structured_output.return_value.invoke.assert_not_called()
    assert result["tests_passed"] is True
    assert result["hint_count"] == 1
    assert result["hints_given"] == ["earlier hint"]


@patch("app.core.mentor.build_implementation_graph")
@patch("app.core.mentor.get_llm")
def test_resume_graph_never_invokes_implementer(
    mock_get_llm: MagicMock, mock_build_impl: MagicMock
) -> None:
    mock_get_llm.return_value = make_hint_llm_mock(Hint(hint_text="hint", reveals_solution=False))

    sandbox = make_fake_sandbox()
    sandbox.run_tests.return_value = (False, "still failing")

    resume_graph = build_mentor_resume_graph(sandbox)
    resume_graph.invoke(make_state(human_attempt="def foo(): return 1"))

    mock_build_impl.assert_not_called()

    mock_build_impl.return_value.invoke.return_value = {"current_content": "reference fix"}
    cost_tracker = RunCostTracker()
    start_graph = build_mentor_start_graph(sandbox, cost_tracker)
    start_graph.invoke(make_state(reference_solution="", human_attempt=""))

    mock_build_impl.assert_called_once()


async def test_submit_attempt_distinguishes_session_vs_sandbox_not_found() -> None:
    fake_manager = MagicMock()
    fake_manager.get_mentor_session.return_value = None
    app.dependency_overrides[get_sandbox_manager] = lambda: fake_manager
    transport = ASGITransport(app=app)

    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                f"/sandboxes/mentor/{uuid.uuid4()}/submit-attempt",
                json={"human_attempt": "def foo(): return 2"},
            )
        assert response.status_code == 404
        assert "session not found" in response.json()["detail"].lower()

        fake_manager.get_mentor_session.return_value = {
            "_workspace_id": str(uuid.uuid4()),
            "issue_title": "t",
            "issue_body": "b",
            "target_file": "app.py",
            "original_content": "x",
            "reference_solution": "y",
            "test_command": "pytest",
            "proficiency": "beginner",
            "hint_count": 0,
            "hints_given": [],
        }
        fake_manager.get.return_value = None

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                f"/sandboxes/mentor/{uuid.uuid4()}/submit-attempt",
                json={"human_attempt": "def foo(): return 2"},
            )
        assert response.status_code == 404
        detail = response.json()["detail"].lower()
        assert "sandbox" in detail
        assert "no longer exists" in detail
        assert detail != "mentor session not found"
    finally:
        app.dependency_overrides.pop(get_sandbox_manager, None)
