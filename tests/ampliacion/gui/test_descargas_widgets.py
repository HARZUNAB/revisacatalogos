#!/usr/bin/env python3
"""
Tests de descargas.py — widgets y descargas (interfaz real)
===========================================================
Cubre con **Tk real**: `encima_de` (grab modal), `_etiqueta_secundaria` (con
ttkbootstrap y con ttk estándar) y `descargar_tabla`/`descargar_texto`
pilotando el diálogo real de formato. Solo se sustituye `_avisar_exito`
(messagebox modal, bloqueante). Necesita `DISPLAY`.
"""

import os
import tkinter as tk
from tkinter import ttk

import pytest

import descargas

pytestmark = pytest.mark.gui


def _buscar(widget, tipo, predicado=None):
    for hijo in widget.winfo_children():
        if isinstance(hijo, tipo) and (predicado is None or predicado(hijo)):
            return hijo
        encontrado = _buscar(hijo, tipo, predicado)
        if encontrado is not None:
            return encontrado
    return None


def _top(raiz):
    return next(w for w in raiz.winfo_children() if isinstance(w, tk.Toplevel))


def _toplevel_visible(raiz):
    top = tk.Toplevel(raiz)
    top.deiconify()
    top.update()
    return top


# --------------------------------------------------------------------------
# encima_de (grab real)
# --------------------------------------------------------------------------
def test_encima_de_modal_toma_el_grab(raiz_tk):
    ventana = _toplevel_visible(raiz_tk)
    descargas.encima_de(raiz_tk, ventana, modal=True)
    raiz_tk.update()
    assert ventana.grab_current() is ventana
    ventana.grab_release()


def test_encima_de_no_modal_no_toma_el_grab(raiz_tk):
    ventana = _toplevel_visible(raiz_tk)
    descargas.encima_de(raiz_tk, ventana, modal=False)
    raiz_tk.update()
    assert ventana.grab_current() is None


def test_encima_de_sin_ventana_no_toma_el_grab(raiz_tk):
    padre = _toplevel_visible(raiz_tk)
    descargas.encima_de(padre)
    raiz_tk.update()
    assert padre.grab_current() is None


def test_encima_de_no_mapeada_no_toma_el_grab(raiz_tk):
    ventana = tk.Toplevel(raiz_tk)
    ventana.withdraw()
    raiz_tk.update()
    descargas.encima_de(raiz_tk, ventana, modal=True)
    raiz_tk.update()
    assert ventana.grab_current() is None


# --------------------------------------------------------------------------
# _etiqueta_secundaria (ttk real)
# --------------------------------------------------------------------------
def test_etiqueta_secundaria_con_ttkbootstrap(raiz_tk):
    import ttkbootstrap

    marco = ttkbootstrap.ttk.Frame(raiz_tk)
    label = descargas._etiqueta_secundaria(ttkbootstrap.ttk, marco, "hola")
    assert label.cget("text") == "hola"


def test_etiqueta_secundaria_fallback_ttk_estandar(raiz_tk):
    # ttk estándar rechaza bootstyle: _etiqueta_secundaria cae al fallback sin
    # romper y devuelve la Label.
    marco = ttk.Frame(raiz_tk)
    label = descargas._etiqueta_secundaria(ttk, marco, "hola")
    assert isinstance(label, ttk.Label)
    assert label.cget("text") == "hola"


# --------------------------------------------------------------------------
# descargar_tabla / descargar_texto con el diálogo real
# --------------------------------------------------------------------------
def _elegir_formato(raiz, valor):
    """Marca el radio y pulsa Descargar en el diálogo de formato abierto."""
    top = _top(raiz)
    radio = _buscar(top, ttk.Radiobutton, lambda w: w.cget("value") == valor)
    radio.invoke()
    _buscar(top, ttk.Button, lambda w: w.cget("text") == "Descargar").invoke()


def test_descargar_tabla_dialogo_real(raiz_tk, cwd_tmp, monkeypatch):
    avisos = []
    monkeypatch.setattr(descargas, "_avisar_exito",
                        lambda padre, ruta: avisos.append(ruta))
    raiz_tk.after(50, lambda: _elegir_formato(raiz_tk, "csv"))

    ruta = descargas.descargar_tabla(raiz_tk, ["a", "b"], [[1, 2]], "etiq")

    assert ruta and os.path.isfile(ruta) and ruta.endswith(".csv")
    assert avisos == [ruta]


def test_descargar_tabla_cancelar(raiz_tk, cwd_tmp, monkeypatch):
    monkeypatch.setattr(descargas, "_avisar_exito",
                        lambda padre, ruta: None)

    def cancelar():
        top = _top(raiz_tk)
        _buscar(top, ttk.Button, lambda w: w.cget("text") == "Cancelar").invoke()

    raiz_tk.after(50, cancelar)
    assert descargas.descargar_tabla(raiz_tk, ["a"], [[1]], "etiq") is None
    assert not os.path.isdir(os.path.join(str(cwd_tmp), "descargas")) or \
        os.listdir(os.path.join(str(cwd_tmp), "descargas")) == []


def test_descargar_texto_real(raiz_tk, cwd_tmp, monkeypatch):
    avisos = []
    monkeypatch.setattr(descargas, "_avisar_exito",
                        lambda padre, ruta: avisos.append(ruta))

    ruta = descargas.descargar_texto(raiz_tk, ["uno", "dos"], "informe")

    assert ruta.endswith(".txt") and os.path.isfile(ruta)
    assert avisos == [ruta]
