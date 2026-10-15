#!/usr/bin/env python3
"""
Tests de app.py — diálogos (contraseña y radio)
===============================================
Cubre los diálogos reales `_pedir_contrasena` y `_pedir_radio`, pilotados con
`after()`. **Ventana real** (sin mocks). Necesita `DISPLAY`.

El `App` se construye una vez para todo el módulo (armar la ventana principal
cuesta ~5 s) y se busca cada diálogo por su título.
"""

import os
import tkinter as tk
from tkinter import ttk

import pytest

import app as appmod

pytestmark = pytest.mark.gui

TITULO_CONTRA = "Contraseña del servidor"
TITULO_RADIO = "Radio de estaciones SeisComp"


@pytest.fixture(scope="module")
def app_dialogos(raiz_gui, tmp_path_factory):
    """Un `App` para todo el módulo, en un cwd temporal."""
    tmp = tmp_path_factory.mktemp("dialogos")
    previo = os.getcwd()
    os.chdir(str(tmp))
    inst = appmod.App(raiz_gui, str(tmp / "entrada.csv"),
                      str(tmp / "salida.dat"))
    try:
        yield inst
    finally:
        for ident in (inst._after_drenar, inst._after_msg):
            if ident is not None:
                try:
                    raiz_gui.after_cancel(ident)
                except Exception:
                    pass
        for widget in list(raiz_gui.winfo_children()):
            try:
                widget.destroy()
            except Exception:
                pass
        os.chdir(previo)


def _top(raiz, titulo):
    for w in raiz.winfo_children():
        if isinstance(w, tk.Toplevel) and w.title() == titulo:
            return w
    raise AssertionError("no está el diálogo %r" % titulo)


def _buscar(widget, tipo, predicado=None):
    for hijo in widget.winfo_children():
        if isinstance(hijo, tipo) and (predicado is None or predicado(hijo)):
            return hijo
        encontrado = _buscar(hijo, tipo, predicado)
        if encontrado is not None:
            return encontrado
    return None


def _entry(raiz, titulo):
    return _buscar(_top(raiz, titulo), ttk.Entry)


def _boton(raiz, titulo, texto):
    return _buscar(_top(raiz, titulo), ttk.Button,
                   lambda w: w.cget("text") == texto)


def _escribir(raiz, titulo, texto):
    entrada = _entry(raiz, titulo)
    entrada.delete(0, "end")
    entrada.insert(0, texto)


# --------------------------------------------------------------------------
# _pedir_contrasena
# --------------------------------------------------------------------------
def test_contrasena_aceptar(app_dialogos, raiz_gui):
    def responder():
        _escribir(raiz_gui, TITULO_CONTRA, "secreta")
        _boton(raiz_gui, TITULO_CONTRA, "Aceptar").invoke()

    raiz_gui.after(50, responder)
    assert app_dialogos._pedir_contrasena() == "secreta"


def test_contrasena_cancelar(app_dialogos, raiz_gui):
    raiz_gui.after(50, lambda: _boton(raiz_gui, TITULO_CONTRA,
                                      "Cancelar").invoke())
    assert app_dialogos._pedir_contrasena() is None


def test_contrasena_atajos_enlazados(app_dialogos, raiz_gui):
    def revisar():
        assert _entry(raiz_gui, TITULO_CONTRA).bind("<Return>")
        assert _top(raiz_gui, TITULO_CONTRA).bind("<Escape>")
        _boton(raiz_gui, TITULO_CONTRA, "Cancelar").invoke()

    raiz_gui.after(50, revisar)
    assert app_dialogos._pedir_contrasena() is None


# --------------------------------------------------------------------------
# _pedir_radio
# --------------------------------------------------------------------------
def test_radio_default_precargado(app_dialogos, raiz_gui):
    visto = {}

    def revisar():
        visto["valor"] = _entry(raiz_gui, TITULO_RADIO).get()
        _boton(raiz_gui, TITULO_RADIO, "Cancelar").invoke()

    raiz_gui.after(50, revisar)
    assert app_dialogos._pedir_radio(400.0) is None
    assert visto["valor"] == "400"


def test_radio_aceptar_valido(app_dialogos, raiz_gui):
    def responder():
        _escribir(raiz_gui, TITULO_RADIO, "250")
        _boton(raiz_gui, TITULO_RADIO, "Aceptar").invoke()

    raiz_gui.after(50, responder)
    assert app_dialogos._pedir_radio(400.0) == 250.0


def test_radio_recorta_sufijo_km(app_dialogos, raiz_gui):
    def responder():
        _escribir(raiz_gui, TITULO_RADIO, "250km")
        _boton(raiz_gui, TITULO_RADIO, "Aceptar").invoke()

    raiz_gui.after(50, responder)
    assert app_dialogos._pedir_radio(400.0) == 250.0


@pytest.mark.parametrize("valor", ["abc", "0", "-5"])
def test_radio_invalido_no_cierra(app_dialogos, raiz_gui, valor):
    def responder():
        _escribir(raiz_gui, TITULO_RADIO, valor)
        _boton(raiz_gui, TITULO_RADIO, "Aceptar").invoke()    # no debe cerrar
        _boton(raiz_gui, TITULO_RADIO, "Cancelar").invoke()   # cierra

    raiz_gui.after(50, responder)
    assert app_dialogos._pedir_radio(400.0) is None


def test_radio_atajos_enlazados(app_dialogos, raiz_gui):
    def revisar():
        assert _entry(raiz_gui, TITULO_RADIO).bind("<Return>")
        assert _top(raiz_gui, TITULO_RADIO).bind("<Escape>")
        _boton(raiz_gui, TITULO_RADIO, "Cancelar").invoke()

    raiz_gui.after(50, revisar)
    assert app_dialogos._pedir_radio(400.0) is None
