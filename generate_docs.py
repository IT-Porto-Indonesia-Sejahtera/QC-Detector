"""
Auto-generate API Reference documentation pages for MkDocs.

Scans the project's Python packages and creates a markdown file for each module
using the mkdocstrings directive (`::: module.path`), so that docstrings
are automatically extracted and rendered.

Usage:
    python generate_docs.py

This will regenerate all files in docs/api/. Run this when you add new modules.
"""

import os

# Project root
ROOT = os.path.dirname(os.path.abspath(__file__))
DOCS_API = os.path.join(ROOT, "docs", "api")

# Packages to document and their display names
PACKAGES = {
    "model": {
        "display": "Model",
        "description": "Computer vision and measurement modules.",
        "skip": ["__init__", "classifier", "inference"],  # Skip empty/legacy modules
    },
    "backend": {
        "display": "Backend",
        "description": "Backend services — database, ArUco, SKU management.",
        "skip": ["__init__", "sku_cache", "plc_handler"],
    },
}


def slug(name: str) -> str:
    """Convert module name to URL-friendly slug."""
    return name.replace("_", "-")


def generate_module_page(package: str, module: str, out_dir: str):
    """Generate a single API reference page for a module."""
    module_path = f"{package}.{module}"
    title = module

    content = f"""# {title}

::: {module_path}
"""

    filename = f"{slug(module)}.md"
    filepath = os.path.join(out_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"  Generated: {filepath}")


def generate_package_docs(package: str, config: dict):
    """Generate API reference pages for all modules in a package."""
    pkg_dir = os.path.join(ROOT, package)
    out_dir = os.path.join(DOCS_API, package)
    os.makedirs(out_dir, exist_ok=True)

    skip = config.get("skip", [])

    print(f"\n📦 Package: {package}/")

    # Find all .py files in the package
    for filename in sorted(os.listdir(pkg_dir)):
        if not filename.endswith(".py"):
            continue

        module = filename[:-3]  # Remove .py

        if module in skip:
            print(f"  Skipped:   {module}")
            continue

        generate_module_page(package, module, out_dir)


def main():
    print("🔄 Generating API documentation pages...\n")

    for package, config in PACKAGES.items():
        generate_package_docs(package, config)

    print("\n✅ Done! Run 'mkdocs serve' to preview.")
    print("   Or run 'mkdocs build' to generate the static site.")


if __name__ == "__main__":
    main()
