"""Each layer only imports the layers below it."""

import ast
import sys
from pathlib import Path

import cadence_ia

PACKAGE = Path(cadence_ia.__file__).parent

# The standard library, minus what would mean I/O leaking into the domain.
FORBIDDEN_STDLIB = {"sqlite3", "os", "xml", "json", "urllib", "http"}


def imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules |= {alias.name for alias in node.names}
        elif isinstance(node, ast.ImportFrom) and node.level == 0:
            modules.add(node.module)
    return modules


def test_domain_only_imports_stdlib_and_itself():
    for path in (PACKAGE / "domain").glob("*.py"):
        for module in imported_modules(path):
            top = module.split(".")[0]
            allowed = module.startswith("cadence_ia.domain") or (
                top in sys.stdlib_module_names and top not in FORBIDDEN_STDLIB
            )
            assert allowed, f"{path.name} imports {module}"


def test_storage_only_imports_stdlib_domain_and_itself():
    for path in (PACKAGE / "storage").glob("*.py"):
        for module in imported_modules(path):
            allowed = (
                module.startswith(("cadence_ia.domain", "cadence_ia.storage"))
                or module.split(".")[0] in sys.stdlib_module_names
            )
            assert allowed, f"storage/{path.name} imports {module}"


def _imports_of(package: str) -> list[tuple[str, str]]:
    return [
        (f"{package}/{path.relative_to(PACKAGE / package).as_posix()}", module)
        for path in (PACKAGE / package).rglob("*.py")
        for module in imported_modules(path)
    ]


def test_services_know_nothing_about_http():
    for name, module in _imports_of("services"):
        assert not module.startswith(("fastapi", "starlette", "cadence_ia.api")), f"{name} imports {module}"


def test_llm_only_sees_the_domain():
    for name, module in _imports_of("llm"):
        assert not module.startswith(
            ("fastapi", "cadence_ia.api", "cadence_ia.services", "cadence_ia.storage")
        ), f"{name} imports {module}"


def test_routes_go_through_services():
    """Only api/deps.py may open the database; routes and schemas use services."""
    for name, module in _imports_of("api"):
        if name != "api/deps.py":
            assert not module.startswith("cadence_ia.storage"), f"{name} imports {module}"
