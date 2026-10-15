"""
conftest.py de tests/ampliacion/gui/
===================================
Tests de interfaz (marcador `gui`, excluidos del CI porque necesitan pantalla).
La fixture `raiz_tk` crea una raíz Tk para los tests y la destruye al terminar;
depende de `salta_sin_display` (en `tests/conftest.py`), así que los tests se
saltean solos cuando no hay `DISPLAY`.
"""

import pytest


@pytest.fixture
def raiz_tk(salta_sin_display):
    """Raíz Tk oculta para armar ventanas en los tests."""
    import tkinter as tk

    raiz = tk.Tk()
    raiz.withdraw()
    raiz.update()
    try:
        yield raiz
    finally:
        raiz.destroy()
