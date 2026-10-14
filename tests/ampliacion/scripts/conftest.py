"""
conftest.py de tests/ampliacion/scripts/
=======================================
Los scripts refactorizados importan `pandas` (p. ej. `compara.py`,
`proc_query_harz_2.py`), que el CI no instala. Las fixtures importan el módulo
con un stub mínimo de pandas para poder testear sus funciones puras en CI.

Solo cubren el *import*: los tests no ejercitan las ramas que usan pandas de
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


def _importar_con_pandas(nombre):
    """Importa `nombre` con pandas stubbeado y restaura `sys.modules`."""
    previo = sys.modules.get("pandas")
    sys.modules["pandas"] = _pandas_minimo()
    try:
        return importlib.import_module(nombre)
    finally:
        if previo is None:
            sys.modules.pop("pandas", None)
        else:
            sys.modules["pandas"] = previo


@pytest.fixture
def compara():
    """Importa `compara` con pandas stubbeado."""
    return _importar_con_pandas("compara")


@pytest.fixture
def proc_query_harz_2():
    """Importa `proc_query_harz_2` con pandas stubbeado."""
    return _importar_con_pandas("proc_query_harz_2")
