"""
conftest.py de tests/ampliacion/scripts/
=======================================
Los scripts refactorizados importan dependencias que el CI no instala:
`pandas` (`compara.py`, `proc_query_harz_2.py`, `revisacollect.py`) y
`Levenshtein` (`revisacollect.py`). Las fixtures importan el módulo con stubs
mínimos de esas dependencias para poder testear sus funciones puras en CI.

Solo cubren el *import*: los tests no ejercitan las ramas que usan pandas o
Levenshtein de verdad (esas quedan cubiertas por el golden del arnés, que corre
localmente).
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


def _levenshtein_minimo():
    mod = types.ModuleType("Levenshtein")
    mod.distance = lambda *a, **k: 0
    return mod


_STUBS = {"pandas": _pandas_minimo, "Levenshtein": _levenshtein_minimo}


def _importar_con_stubs(nombre):
    """Importa `nombre` con pandas y Levenshtein stubbeados."""
    previo = {clave: sys.modules.get(clave) for clave in _STUBS}
    for clave, fabrica in _STUBS.items():
        sys.modules[clave] = fabrica()
    try:
        return importlib.import_module(nombre)
    finally:
        for clave, valor in previo.items():
            if valor is None:
                sys.modules.pop(clave, None)
            else:
                sys.modules[clave] = valor


@pytest.fixture
def compara():
    """Importa `compara` con pandas stubbeado."""
    return _importar_con_stubs("compara")


@pytest.fixture
def proc_query_harz_2():
    """Importa `proc_query_harz_2` con pandas stubbeado."""
    return _importar_con_stubs("proc_query_harz_2")


@pytest.fixture
def revisacollect():
    """Importa `revisacollect` con pandas y Levenshtein stubbeados."""
    return _importar_con_stubs("revisacollect")
