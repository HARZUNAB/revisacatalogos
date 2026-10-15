#!/usr/bin/env python3
"""
Tests de app.py — ventanas de consulta
======================================
Cubre la construcción y el comportamiento de las ventanas "No actualizados",
"Catálogos", "Eventos repetidos" y "No publicados". **Ventana real + datos
sintéticos**: las dependencias pesadas (revisor, descargas) se sustituyen con
stubs. Necesita `DISPLAY`.

No se cubren el filtro por texto ni el orden por encabezado de "No publicados":
son callbacks internos que solo se disparan con eventos Tk (poco confiables en
tests).
"""

import tkinter as tk
from tkinter import ttk

import pytest

import app as appmod

pytestmark = pytest.mark.gui


def _toplevel(raiz, titulo):
    for w in raiz.winfo_children():
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


# --------------------------------------------------------------------------
# No actualizados
# --------------------------------------------------------------------------
def test_no_actualizados_estructura_y_build_perezoso(app_factory, raiz_gui):
    _, inst = app_factory()
    llamadas = []
    inst._abrir_no_actualizados = \
        lambda fuente, contenedor=None: llamadas.append(fuente)

    inst._ver_no_actualizados()

    top = _toplevel(raiz_gui, "No actualizados")
    assert top is not None
    cuaderno = _buscar(top, ttk.Notebook)
    assert _tab_texts(cuaderno) == ["SeisComp", "Seisan"]
    assert llamadas == ["seiscomp"]

    # Cambiar de pestaña construye la otra fuente (perezoso).
    cuaderno.select(cuaderno.tabs()[1])
    cuaderno.event_generate("<<NotebookTabChanged>>")
    raiz_gui.update()
    assert llamadas == ["seiscomp", "seisan"]


# --------------------------------------------------------------------------
# Catálogos
# --------------------------------------------------------------------------
def test_catalogos_estructura_y_reuso(app_factory, raiz_gui):
    _, inst = app_factory()
    llamadas = []
    inst._construir_catalogo = \
        lambda clave, seleccionar=False: llamadas.append(clave)

    inst._ver_catalogos()

    top = _toplevel(raiz_gui, "Catálogos")
    assert top is not None
    assert inst.marco_catalogos is top
    assert inst.seiscomp_frame is not None
    assert inst.seisan_frame is not None
    assert inst.eventquery_frame is not None
    assert _tab_texts(_buscar(top, ttk.Notebook)) == \
        ["SeisComp", "Seisan", "eventquery"]
    assert llamadas == ["seiscomp"]
    assert top.protocol("WM_DELETE_WINDOW")

    # Segunda vez: reutiliza la misma ventana, no crea otra.
    inst._ver_catalogos()
    toples = [w for w in raiz_gui.winfo_children()
              if isinstance(w, tk.Toplevel) and w.title() == "Catálogos"]
    assert len(toples) == 1
    assert inst.marco_catalogos is top


# --------------------------------------------------------------------------
# Repetidos
# --------------------------------------------------------------------------
def _boton(top, texto):
    return _buscar(top, ttk.Button, lambda w: w.cget("text") == texto)


def test_repetidos_con_informe(app_factory, raiz_gui, cwd_tmp, monkeypatch):
    _, inst = app_factory()
    (cwd_tmp / "informes").mkdir(exist_ok=True)
    (cwd_tmp / "informes" / "rep_publica_amplio.txt").write_text(
        "uno\ndos\n", encoding="utf-8")

    descargado = {}

    def descargar_texto(padre, lineas, etiqueta, cwd=None):
        descargado["lineas"] = lineas
        descargado["etiqueta"] = etiqueta
        return "informes/descarga.txt"

    monkeypatch.setattr(appmod.descargas, "descargar_texto", descargar_texto)

    inst._ver_repetidos()

    top = _toplevel(raiz_gui, "Eventos repetidos")
    arbol = _buscar(top, ttk.Treeview)
    assert len(arbol.get_children()) == len(appmod.REP_FILES)
    # La primera fila (rep_publica_amplio) tiene datos y queda seleccionada.
    # El conteo resta 1 (asume que la primera línea es encabezado).
    primera = arbol.get_children()[0]
    assert arbol.item(primera, "values")[1] == "1"
    boton = _boton(top, "Descargar informe")
    assert not boton.instate(["disabled"])

    boton.invoke()
    assert descargado["lineas"] == ["uno\n", "dos\n"]
    assert descargado["etiqueta"] == "rep_publica_amplio"


def test_repetidos_sin_archivos(app_factory, raiz_gui, cwd_tmp):
    _, inst = app_factory()
    inst._ver_repetidos()
    top = _toplevel(raiz_gui, "Eventos repetidos")
    arbol = _buscar(top, ttk.Treeview)
    valores = [arbol.item(i, "values") for i in arbol.get_children()]
    assert len(valores) == len(appmod.REP_FILES)
    assert all(v[1] == "0" for v in valores)
    assert _boton(top, "Descargar informe").instate(["disabled"])


# --------------------------------------------------------------------------
# No publicados
# --------------------------------------------------------------------------
_CSV_NO_PUB = (
    ",Fecha_Hora,Latitud,Longitud,Prof.,Mag.,Tipo_mag.,Analista\n"
    "0,2026-01-01  00:00:00,-30.0,-71.0,10.0,4.5,ML,ana\n"
    "1,2026-01-02  00:00:00,-31.0,-72.0,20.0,3.0,ML,beto\n")


def _escribir_no_pub(cwd, contenido=_CSV_NO_PUB):
    datos = cwd / "datos"
    datos.mkdir(exist_ok=True)
    (datos / "no_pub_desde_2_5_seiscomp_estricto.csv").write_text(
        contenido, encoding="utf-8")


def test_no_publicados_tabla_y_descargar_todo(app_factory, raiz_gui, cwd_tmp,
                                              monkeypatch):
    _, inst = app_factory()
    _escribir_no_pub(cwd_tmp)
    descargado = {}

    def descargar_tabla(padre, encabezados, filas, etiqueta, cwd=None,
                        aviso=True):
        descargado["filas"] = filas
        descargado["etiqueta"] = etiqueta
        return "datos/descarga.csv"

    monkeypatch.setattr(appmod.descargas, "descargar_tabla", descargar_tabla)

    inst._ver_no_publicados()

    top = _toplevel(raiz_gui, "No publicados")
    assert _tab_texts(_buscar(top, ttk.Notebook)) == ["SeisComp", "Seisan"]
    arbol = _buscar(top, ttk.Treeview)
    assert len(arbol.get_children()) == 2
    assert not _boton(top, "Descargar").instate(["disabled"])

    _boton(top, "Descargar todo").invoke()
    assert len(descargado["filas"]) == 2
    assert descargado["etiqueta"] == "no publicados seiscomp"


def test_no_publicados_sin_csv(app_factory, raiz_gui, cwd_tmp):
    _, inst = app_factory()
    inst._ver_no_publicados()
    top = _toplevel(raiz_gui, "No publicados")
    arbol = _buscar(top, ttk.Treeview)
    assert len(arbol.get_children()) == 0
    assert _boton(top, "Descargar").instate(["disabled"])
