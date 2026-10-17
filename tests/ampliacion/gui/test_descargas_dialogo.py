#!/usr/bin/env python3
"""
Tests de descargas.py — diálogo de descarga (con pantalla)
==========================================================
Cubre el diálogo real de `preguntar_descarga` (y su envoltorio
`preguntar_formato`) con un Tk: elegir CSV/TXT, editar el nombre, aceptar con
Enter, cancelar con Escape y la pregunta de sobrescritura. Necesita `DISPLAY`.

Los demás caminos de `descargas.py` (sin Tk) están en
`tests/ampliacion/modulos/test_descargas_interfaz.py`.
"""

import os
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


# --------------------------------------------------------------------------
# preguntar_descarga: nombre y sobrescritura
# --------------------------------------------------------------------------
def test_preguntar_descarga_nombre_por_defecto(raiz_tk, cwd_tmp):
    raiz_tk.after(50, lambda: _invocar(raiz_tk, "csv"))
    formato, nombre, sobrescribir = descargas.preguntar_descarga(raiz_tk, "etiq")
    assert formato == "csv"
    assert nombre.startswith("etiq_")
    assert sobrescribir is False


def test_preguntar_descarga_usa_el_nombre_editado(raiz_tk, cwd_tmp):
    def editar():
        top = _top(raiz_tk)
        entrada = _buscar(top, tk.Entry)
        entrada.delete(0, "end")
        entrada.insert(0, "Mi Listado!")
        _invocar(raiz_tk, "txt")

    raiz_tk.after(50, editar)
    assert descargas.preguntar_descarga(raiz_tk, "etiq") == \
        ("txt", "Mi Listado!", False)


def test_preguntar_descarga_cancelar_devuelve_none(raiz_tk, cwd_tmp):
    raiz_tk.after(50, lambda: _invocar(raiz_tk, "csv", boton="Cancelar"))
    assert descargas.preguntar_descarga(raiz_tk, "etiq") is None


def test_preguntar_descarga_pide_sobrescribir_si_existe(raiz_tk, cwd_tmp,
                                                        monkeypatch):
    carpeta = os.path.join(str(cwd_tmp), "descargas")
    os.makedirs(carpeta)
    open(os.path.join(carpeta, "mio.csv"), "w").close()
    llamadas = []
    monkeypatch.setattr(
        descargas, "_confirmar_sobrescribir",
        lambda padre, existentes: llamadas.append(existentes) or True)

    def editar():
        top = _top(raiz_tk)
        entrada = _buscar(top, tk.Entry)
        entrada.delete(0, "end")
        entrada.insert(0, "mio")
        _invocar(raiz_tk, "csv")

    raiz_tk.after(50, editar)
    assert descargas.preguntar_descarga(raiz_tk, "etiq") == ("csv", "mio", True)
    assert llamadas and llamadas[0][0].endswith("mio.csv")
