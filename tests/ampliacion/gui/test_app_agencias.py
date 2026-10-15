#!/usr/bin/env python3
"""
Tests de app.py — agencias y cobertura
======================================
Cubre `_cobertura_agencias`, `_detalles_cobertura`, `_ver_comparacion_agencias`
y el diálogo `_pedir_parametros_agencias`. **Interfaz real** con datos
sintéticos en el formato real. Necesita `DISPLAY`.
"""

import tkinter as tk
from tkinter import ttk

import pytest

import app as appmod

pytestmark = pytest.mark.gui


def _recorrer(widget):
    for hijo in widget.winfo_children():
        yield hijo
        for sub in _recorrer(hijo):
            yield sub


def _toplevel(raiz, titulo):
    for w in _recorrer(raiz):
        if isinstance(w, tk.Toplevel) and w.title() == titulo:
            return w
    return None


def _buscar(widget, tipo, predicado=None):
    for hijo in widget.winfo_children():
        if isinstance(hijo, tipo) and (predicado is None or predicado(hijo)):
            return hijo
        encontrado = _buscar(hijo, tipo, predicado)
        if encontrado is not None:
            return encontrado
    return None


def _tab_texts(cuaderno):
    return [cuaderno.tab(t, "text") for t in cuaderno.tabs()]


def _boton(widget, texto):
    return _buscar(widget, ttk.Button, lambda w: w.cget("text") == texto)


def _check(widget, texto):
    return _buscar(widget, ttk.Checkbutton, lambda w: w.cget("text") == texto)


def _escribir(cwd, rel, texto):
    ruta = cwd / rel
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(texto, encoding="utf-8")
    return ruta


# --------------------------------------------------------------------------
# _cobertura_agencias
# --------------------------------------------------------------------------
def test_cobertura_agencias(app_factory, cwd_tmp):
    _, inst = app_factory()
    inst._escribir_estado_agencias(
        4.0, ["EMSC"], "ventana", ("20260901000000", "20260930235959"))
    _escribir(cwd_tmp, "datos/agencias/consultaapi_EMSC.csv",
              "Fecha_Hora,Latitud\n"
              "2026-09-05 00:00:00,-33.0\n"
              "2026-09-20 12:00:00,-33.1\n")

    cob = inst._cobertura_agencias(["EMSC"])

    assert cob["solicitada"] == {"desde": "2026-09-01 00:00:00",
                                 "hasta": "2026-09-30 23:59:59",
                                 "minmag": 4.0}
    fila = cob["agencias"][0]
    assert fila["agencia"] == "EMSC"
    assert fila["eventos"] == 2
    assert fila["desde"] == "2026-09-05 00:00:00"
    assert fila["hasta"] == "2026-09-20 12:00:00"
    assert fila["rezago"] == "10.5 d"


def test_cobertura_agencias_sin_csv(app_factory, cwd_tmp):
    _, inst = app_factory()
    cob = inst._cobertura_agencias(["USGS"])
    fila = cob["agencias"][0]
    assert fila["agencia"] == "USGS"
    assert fila["eventos"] == 0
    assert fila["desde"] == "" and fila["hasta"] == "" and fila["rezago"] == ""


# --------------------------------------------------------------------------
# _detalles_cobertura
# --------------------------------------------------------------------------
def _cobertura_fija():
    return {
        "solicitada": {"desde": "2026-09-01 00:00:00",
                       "hasta": "2026-09-30 23:59:59", "minmag": 4.0},
        "agencias": [
            {"agencia": "EMSC", "eventos": 2, "desde": "2026-09-05 00:00:00",
             "hasta": "2026-09-20 12:00:00", "rezago": "10.5 d"},
            {"agencia": "USGS", "eventos": 0, "desde": "", "hasta": "",
             "rezago": ""},
        ],
    }


def test_detalles_cobertura(app_factory, raiz_gui):
    _, inst = app_factory()
    padre = tk.Toplevel(raiz_gui)
    padre.withdraw()

    inst._detalles_cobertura(padre, _cobertura_fija())

    top = _toplevel(raiz_gui, "Cobertura por agencia")
    assert top is not None
    arbol = _buscar(top, ttk.Treeview)
    assert len(arbol.get_children()) == 2
    valores = arbol.item(arbol.get_children()[0], "values")
    assert valores[0] == "EMSC" and valores[1] == "2"
    # Las agencias sin datos muestran el guion de vacío.
    valores2 = arbol.item(arbol.get_children()[1], "values")
    assert valores2[0] == "USGS" and valores2[2] == "—"


# --------------------------------------------------------------------------
# _ver_comparacion_agencias
# --------------------------------------------------------------------------
def test_ver_comparacion_agencias(app_factory, raiz_gui, cwd_tmp, monkeypatch):
    _, inst = app_factory()
    _escribir(cwd_tmp, "datos/comparacion_agencias.json", "[]")
    _escribir(cwd_tmp, "datos/agencias_sin_par.json", "[]")
    # El panel embebido de plotear tiene su propia fila y abre figuras de
    # matplotlib que interfieren con la raíz compartida; se acota acá.
    import plotear
    monkeypatch.setattr(plotear, "abrir_panel", lambda *a, **k: False)

    inst._ver_comparacion_agencias()

    top = _toplevel(raiz_gui, "Comparar agencias")
    assert top is not None
    cuaderno = _buscar(top, ttk.Notebook)
    assert _tab_texts(cuaderno) == ["Comparación",
                                    "Agencias sin contraparte con CSN"]
    assert _boton(top, "Cobertura por agencia") is not None


# --------------------------------------------------------------------------
# _pedir_parametros_agencias
# --------------------------------------------------------------------------
def _top_dialogo(raiz):
    return _toplevel(raiz, "Comparar agencias")


def test_pedir_parametros_default(app_factory, raiz_gui, cwd_tmp):
    _, inst = app_factory()
    raiz_gui.after(50, lambda: _boton(_top_dialogo(raiz_gui),
                                      "Comparar").invoke())
    res = inst._pedir_parametros_agencias()
    assert res == (4.0, ["EMSC", "USGS", "GFZ"], False, "ventana", False,
                   None, None)


def test_pedir_parametros_minmag_invalida(app_factory, raiz_gui, cwd_tmp):
    _, inst = app_factory()

    def responder():
        top = _top_dialogo(raiz_gui)
        ent = _buscar(top, ttk.Entry)   # el primero es la magnitud mínima
        ent.delete(0, "end")
        ent.insert(0, "abc")
        _boton(top, "Comparar").invoke()   # no cierra
        ent.delete(0, "end")
        ent.insert(0, "5.0")
        _boton(top, "Comparar").invoke()   # cierra

    raiz_gui.after(50, responder)
    assert inst._pedir_parametros_agencias()[0] == 5.0


def test_pedir_parametros_sin_agencia(app_factory, raiz_gui, cwd_tmp):
    _, inst = app_factory()

    def responder():
        top = _top_dialogo(raiz_gui)
        for ag in ("EMSC", "USGS", "GFZ"):
            _check(top, ag).invoke()        # destilda las tres
        _boton(top, "Comparar").invoke()    # no cierra
        _check(top, "EMSC").invoke()        # re-tilda una
        _boton(top, "Comparar").invoke()    # cierra

    raiz_gui.after(50, responder)
    assert inst._pedir_parametros_agencias()[1] == ["EMSC"]


def test_pedir_parametros_cancelar(app_factory, raiz_gui, cwd_tmp):
    _, inst = app_factory()
    raiz_gui.after(50, lambda: _boton(_top_dialogo(raiz_gui),
                                      "Cancelar").invoke())
    assert inst._pedir_parametros_agencias() is None
