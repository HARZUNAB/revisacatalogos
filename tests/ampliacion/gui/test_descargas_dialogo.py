#!/usr/bin/env python3
"""
Tests de descargas.py — diálogo de formato (con pantalla)
========================================================
Cubre el diálogo real de `preguntar_formato` con un Tk: elegir CSV/TXT,
cancelar, aceptar con Enter y cancelar con Escape. Necesita `DISPLAY`.

Los demás caminos de `descargas.py` (sin Tk) están en
`tests/ampliacion/modulos/test_descargas_interfaz.py`.
"""

import tkinter as tk
from tkinter import ttk

import pytest

import descargas

pytestmark = pytest.mark.gui


@pytest.fixture(autouse=True)
def formato_inicial(monkeypatch):
    """Resetea la última elección para que el valor por defecto sea predecible."""
    monkeypatch.setattr(descargas, "_ultimo_formato", "csv")


def _top(padre):
    return next(w for w in padre.winfo_children() if isinstance(w, tk.Toplevel))


def _buscar(widget, tipo, predicado=None):
    for hijo in widget.winfo_children():
        if isinstance(hijo, tipo) and (predicado is None or predicado(hijo)):
            return hijo
        encontrado = _buscar(hijo, tipo, predicado)
        if encontrado is not None:
            return encontrado
    return None


def _invocar(padre, valor=None, boton="Descargar"):
    """Marca un radio (si hace falta) y pulsa un botón del diálogo abierto."""
    top = _top(padre)
    if valor is not None:
        radio = _buscar(top, ttk.Radiobutton,
                        lambda w: w.cget("value") == valor)
        radio.invoke()
    pulsar = _buscar(top, ttk.Button, lambda w: w.cget("text") == boton)
    pulsar.invoke()


# --------------------------------------------------------------------------
# Elegir y cancelar con los botones
# --------------------------------------------------------------------------
def test_elegir_txt(raiz_tk):
    raiz_tk.after(50, lambda: _invocar(raiz_tk, "txt"))
    assert descargas.preguntar_formato(raiz_tk) == "txt"
    assert descargas._ultimo_formato == "txt"


def test_elegir_csv(raiz_tk):
    raiz_tk.after(50, lambda: _invocar(raiz_tk, "csv"))
    assert descargas.preguntar_formato(raiz_tk) == "csv"


def test_descargar_sin_tocar_el_radio_usa_el_ultimo(raiz_tk):
    # Con el radio por defecto (csv) y Descargar, devuelve el último formato.
    raiz_tk.after(50, lambda: _invocar(raiz_tk))
    assert descargas.preguntar_formato(raiz_tk) == "csv"


def test_cancelar_devuelve_none(raiz_tk):
    raiz_tk.after(50, lambda: _invocar(raiz_tk, "txt", boton="Cancelar"))
    assert descargas.preguntar_formato(raiz_tk) is None
    # Cancelar no cambia la última elección.
    assert descargas._ultimo_formato == "csv"


# --------------------------------------------------------------------------
# Atajos de teclado
# --------------------------------------------------------------------------
def test_atajos_enter_y_escape_enlazados(raiz_tk):
    # Generar los eventos depende del foco (poco confiable en tests), así que
    # se verifica que el diálogo tenga los atajos enlazados y se cierra con el
    # botón para que `wait_window` retorne.
    def revisar():
        top = _top(raiz_tk)
        assert top.bind("<Return>")
        assert top.bind("<Escape>")
        _invocar(raiz_tk, "txt")

    raiz_tk.after(50, revisar)
    assert descargas.preguntar_formato(raiz_tk) == "txt"
