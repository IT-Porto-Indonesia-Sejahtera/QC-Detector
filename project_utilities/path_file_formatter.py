import os
import platform

def normalize_path(path: str) -> str:
    path = path.replace("\\", "/")

    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    project_name = os.path.basename(project_root)

    if f"/{project_name}/" in path:
        while path.count(f"/{project_name}/") > 1:
            path = path.replace(f"{project_name}/", "", 1)

    if path.startswith(project_name + "/"):
        path = path[len(project_name) + 1:]

    if not os.path.isabs(path):
        path = os.path.join(project_root, path)

    if "windows" in platform.system().lower():
        path = path.replace("/", "\\")

    if not os.path.exists(path):
        print(f"[WARN] File not found at: {path}")

    return os.path.abspath(path)
