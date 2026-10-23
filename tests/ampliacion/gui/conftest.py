"""
conftest.py de tests/ampliacion/gui/
===================================
Tests de interfaz (marcador `gui`, excluidos del CI porque necesitan pantalla).

ttkbootstrap usa un `Style` global atado a la primera raíz: crear y destruir
varias raíces en el mismo proceso rompe las siguientes. Por eso hay **una sola
raíz para toda la sesión** (`raiz_gui`), y cada test limpia sus widgets.

Fixtures:
  * `raiz_gui`     raíz ttkbootstrap de sesión (salta la sesión sin `DISPLAY`).
  * `raiz_tk`      la raíz, limpia de widgets del test anterior.
  * `app_factory`  arma `app.App` sobre la raíz (estado dummy, sin pipeline).
"""

import os

import pytest


@pytest.fixture(scope="session")
def raiz_gui():
    """Raíz ttkbootstrap compartida por toda la sesión de tests de gui."""
    if not os.environ.get("DISPLAY"):
        pytest.skip("necesita pantalla (DISPLAY)")
    import ttkbootstrap as tb

    raiz = tb.Window(themename="flatly")
    raiz.withdraw()
    raiz.update()
    try:
        yield raiz
    finally:
        try:
            raiz.destroy()
        except Exception:
            pass


def _limpiar(raiz):
    """Destruye los widgets del test anterior sin tocar la raíz."""
    for widget in list(raiz.winfo_children()):
        try:
            widget.destroy()
        except Exception:
            pass
    raiz.update_idletasks()


@pytest.fixture
def raiz_tk(raiz_gui):
    """Raíz limpia para el test."""
    _limpiar(raiz_gui)
    return raiz_gui


@pytest.fixture
def app_factory(raiz_gui, cwd_tmp):
    """
    Crea instancias de `app.App` sobre la raíz compartida.

    No corre el pipeline: construye la ventana con rutas dummy en el directorio
    temporal (estado sintético). Al terminar cancela los `after` pendientes.
    """
    import app as appmod

    creadas = []

    def crear(estado=None, archivo=None, salida=None, progreso=None):
        _limpiar(raiz_gui)
        inst = appmod.App(
            raiz_gui,
            archivo or str(cwd_tmp / "entrada.csv"),
            salida or str(cwd_tmp / "salida.dat"),
            estado=estado, progreso=progreso)
        creadas.append(inst)
        return raiz_gui, inst

    yield crear

    for inst in creadas:
        for ident in (inst._after_drenar, inst._after_msg):
            if ident is not None:
                try:
                    raiz_gui.after_cancel(ident)
                except Exception:
                    pass
        inst._after_drenar = None
        inst._after_msg = None
    _limpiar(raiz_gui)
