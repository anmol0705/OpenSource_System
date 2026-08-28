import json
import sys
from pathlib import Path

from app.core.code_analysis import build_repository_map
from app.core.investigator import InvestigationState, build_investigator_graph
from app.core.sandbox import get_sandbox_manager

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from evals.models import EvalExample, EvalResult  # noqa: E402


def load_dataset(path: Path) -> list[EvalExample]:
    raw = json.loads(path.read_text())
    return [
        EvalExample(
            repo_clone_url=item["repo_clone_url"],
            issue_title=item["issue_title"],
            issue_body=item["issue_body"],
            ground_truth_file=item["ground_truth_file"],
            source_pr_url=item["source_pr_url"],
        )
        for item in raw
    ]


def run_single_example(example: EvalExample) -> EvalResult:
    manager = get_sandbox_manager()
    sandbox = manager.create(example.repo_clone_url)

    try:
        repo_map = build_repository_map(sandbox)
        graph = build_investigator_graph(sandbox)

        initial_state: InvestigationState = {
            "issue_title": example.issue_title,
            "issue_body": example.issue_body,
            "repo_map_summary": repo_map.summary(),
            "inspected_files": {},
            "file_histories": {},
            "hypothesis": "",
            "target_file": "",
            "confidence": 0.0,
            "check_history": False,
            "iteration": 0,
            "history": [],
        }

        result = graph.invoke(initial_state)

        return EvalResult(
            example=example,
            predicted_file=result["target_file"],
            confidence=result["confidence"],
            iterations=result["iteration"],
            correct=result["target_file"] == example.ground_truth_file,
        )
    finally:
        sandbox.destroy()


def print_report(results: list[EvalResult]) -> None:
    total = len(results)
    correct = sum(1 for r in results if r.correct)

    print(f"\n=== Eval Report ({total} examples) ===")
    print(f"Hit rate: {correct}/{total} ({100 * correct / total:.1f}%)\n")

    high_conf = [r for r in results if r.confidence >= 0.75]
    high_conf_correct = sum(1 for r in high_conf if r.correct)
    if high_conf:
        print(
            f"Calibration @ confidence>=0.75: {high_conf_correct}/{len(high_conf)} "
            f"({100 * high_conf_correct / len(high_conf):.1f}% actually correct)"
        )

    low_conf = [r for r in results if r.confidence < 0.75]
    low_conf_correct = sum(1 for r in low_conf if r.correct)
    if low_conf:
        print(
            f"Calibration @ confidence<0.75: {low_conf_correct}/{len(low_conf)} "
            f"({100 * low_conf_correct / len(low_conf):.1f}% actually correct)"
        )

    correct_iters = [r.iterations for r in results if r.correct]
    incorrect_iters = [r.iterations for r in results if not r.correct]
    if correct_iters:
        print(f"\nAvg iterations (correct): {sum(correct_iters) / len(correct_iters):.1f}")
    if incorrect_iters:
        print(f"Avg iterations (incorrect): {sum(incorrect_iters) / len(incorrect_iters):.1f}")

    print("\n=== Per-example detail ===")
    for r in results:
        status = "✓" if r.correct else "✗"
        print(
            f"{status} predicted={r.predicted_file!r} "
            f"expected={r.example.ground_truth_file!r} "
            f"confidence={r.confidence:.2f} iterations={r.iterations}"
        )


if __name__ == "__main__":
    dataset_path = Path(__file__).parent / "dataset.json"
    examples = load_dataset(dataset_path)

    print(f"Running {len(examples)} eval examples against the REAL Investigator graph...")
    print("This makes REAL LLM calls and costs REAL money.\n")

    results = [run_single_example(ex) for ex in examples]
    print_report(results)
