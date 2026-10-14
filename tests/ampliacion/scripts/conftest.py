"""
conftest.py de tests/ampliacion/scripts/
=======================================
Los scripts refactorizados importan `pandas` (p. ej. `compara.py`), que el CI
no instala. La fixture `compara` importa el módulo con un stub mínimo de pandas
para poder testear sus funciones puras en CI.

Solo cubre el *import*: los tests no ejercitan las ramas que usan pandas de
verdad (esas quedan cubiertas por el golden del arnés, que corre localmente).
"""

import importlib
import sys
import types

import pytest


def _pandas_minimo():
    mod = types.ModuleType("pandas")
    mod.DataFrame = object
    mod.to_datetime = lambda *a, **k: None
    mod.read_csv = lambda *a, **k: None
    return mod


@pytest.fixture
def compara():
    """Importa `compara` con pandas stubbeado y restaura `sys.modules`."""
    previo = sys.modules.get("pandas")
    sys.modules["pandas"] = _pandas_minimo()
    try:
        modulo = importlib.import_module("compara")
    finally:
        if previo is None:
            sys.modules.pop("pandas", None)
        else:
            sys.modules["pandas"] = previo
    return modulo
