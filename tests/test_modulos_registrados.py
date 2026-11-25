"""
Todo módulo do backend tem rotas registradas no app (#9).

Spec: SPEC/2026-11-25-remove-modulos-vazios.md

Um pacote em src/backend/modules sem `router.py`, ou com um router que o main.py não registra, é
código morto: foi o caso de clients, landing e queue, que só tinham um __init__.py.
"""

from pathlib import Path

from src.backend.main import app

MODULES = Path(__file__).resolve().parents[1] / "src" / "backend" / "modules"


def packages():
    return sorted(p.name for p in MODULES.iterdir() if p.is_dir() and (p / "__init__.py").exists())


def registered_modules():
    names = set()
    for route in app.routes:
        endpoint = getattr(route, "endpoint", None)
        module = getattr(endpoint, "__module__", "")
        if module.startswith("src.backend.modules."):
            names.add(module.split(".")[3])
    return names


def test_every_module_package_has_a_router_file():
    assert [p for p in packages() if not (MODULES / p / "router.py").exists()] == []


def test_every_module_package_is_registered_in_main():
    assert sorted(set(packages()) - registered_modules()) == []


def test_the_empty_modules_are_gone():
    assert {"clients", "landing", "queue"}.isdisjoint(packages())
