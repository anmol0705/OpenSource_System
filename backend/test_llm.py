from app.core.code_analysis import build_repository_map
from app.core.investigator import InvestigationState, build_investigator_graph
from app.core.sandbox import get_sandbox_manager

manager = get_sandbox_manager()
sandbox = manager.create("https://github.com/jazzband/django-silk.git")

repo_map = build_repository_map(sandbox)

graph = build_investigator_graph(sandbox)

initial_state: InvestigationState = {
    "issue_title": "gzip middleware breaks raw response view",
    "issue_body": (
        "When @gzip_page decorator is used, the raw response view in silk shows "
        "garbled/compressed content instead of the actual response body."
    ),
    "repo_map_summary": repo_map.summary(),
    "inspected_files": {},
    "hypothesis": "",
    "target_file": "",
    "confidence": 0.0,
    "iteration": 0,
    "history": [],
}

result = graph.invoke(initial_state)

print("Final hypothesis:", result["hypothesis"])
print("Target file:", result["target_file"])
print("Confidence:", result["confidence"])
print("Iterations:", result["iteration"])
print("Files inspected:", list(result["inspected_files"].keys()))

sandbox.destroy()
