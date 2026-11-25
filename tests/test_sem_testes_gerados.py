"""
Os testes gerados da AP1 não voltam (#3).

Spec: SPEC/2026-11-25-fim-dos-testes-gerados.md

O tests/generate_tests.py escrevia, para cada módulo, um tests/test_<módulo>.py com 1.000
funções `test_<módulo>_scenario_<n>` que conferiam um dicionário fixo, sem importar a aplicação.
"""

import re
from pathlib import Path

TESTS = Path(__file__).resolve().parent
GENERATED = re.compile(r"^def test_\w+_scenario_\d+\(", re.M)


def test_the_generator_is_gone():
    assert not (TESTS / "generate_tests.py").exists()


def test_no_generated_test_file_is_left():
    leftovers = [p.name for p in TESTS.glob("test_*.py") if GENERATED.search(p.read_text(encoding="utf-8"))]
    assert leftovers == []


def test_every_module_has_api_tests():
    modules = sorted(
        p.name for p in (TESTS.parent / "src" / "backend" / "modules").iterdir()
        if p.is_dir() and (p / "router.py").exists()
    )
    tested = {p.stem for p in TESTS.glob("test_*.py")}
    missing = [m for m in modules if not any(t.startswith(f"test_{m}") for t in tested)]
    assert missing == []
