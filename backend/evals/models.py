from dataclasses import dataclass


@dataclass
class EvalExample:
    """One real, verifiable test case — a past issue with a known-correct
    fix, sourced from a real merged PR. source_pr_url exists purely as
    an audit trail proving this ground truth is real, not invented.
    """

    repo_clone_url: str
    issue_title: str
    issue_body: str
    ground_truth_file: str
    source_pr_url: str


@dataclass
class EvalResult:
    """What actually happened when we ran one example through the real
    Investigator graph, plus whether it matched ground truth.
    """

    example: EvalExample
    predicted_file: str
    confidence: float
    iterations: int
    correct: bool
