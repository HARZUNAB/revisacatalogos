"""
conftest.py de tests/ampliacion/red/
===================================
`consultaapi.py` importa `pandas` y `requests` a nivel de módulo, y el CI solo
instala `numpy` y `pytest`. La fixture `consultaapi` importa el módulo con
stubs mínimos de esas dos dependencias, de modo que los tests corran también
en CI.

Los stubs solo cubren el *import*: los tests reemplazan `requests.get` con
`monkeypatch` y nunca ejercitan pandas (las ramas de pandas, como `_guardar`
o el parseo de GFZ, quedan fuera del alcance de estos tests).
"""

import importlib
import sys
import types

import pytest


class _ModuloRequests(types.ModuleType):
    """Stub mínimo de `requests`: solo expone `get`, que reemplaza cada test."""

    def __init__(self):
        super().__init__("requests")
        self.get = None


def _pandas_minimo():
    mod = types.ModuleType("pandas")
    mod.DataFrame = object
    mod.to_datetime = lambda *a, **k: None
    mod.read_csv = lambda *a, **k: None
    return mod


@pytest.fixture
def consultaapi():
    """
    Importa `consultaapi` con `pandas` y `requests` stubbeados.

    `sys.modules` se restaura después del import para no ensuciar el resto de
    la suite; el módulo importado ya quedó con la referencia al stub de
    `requests`, que los tests parchean.
    """
    previos = {n: sys.modules.get(n) for n in ("pandas", "requests")}
    sys.modules["pandas"] = _pandas_minimo()
    sys.modules["requests"] = _ModuloRequests()
    try:
        modulo = importlib.import_module("consultaapi")
    finally:
        for nombre, previo in previos.items():
            if previo is None:
                sys.modules.pop(nombre, None)
            else:
                sys.modules[nombre] = previo
    return modulo
