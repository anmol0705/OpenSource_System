from app.core.code_analysis import build_repository_map
from app.core.sandbox import get_sandbox_manager

manager = get_sandbox_manager()
sandbox = manager.create("https://github.com/jazzband/django-silk.git")

repo_map = build_repository_map(sandbox)
print(f"Analyzed {len(repo_map.files)} files")
print()
print(repo_map.summary()[:1500])  # first 1500 chars, full repo would be long

sandbox.destroy()
