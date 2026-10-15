#!/usr/bin/env python3
"""
Tests de revisa_seiscomp.py — no actualizados
=============================================
Cubre `_no_actualizados` (helper puro) y `abrir_no_actualizados` (listado real
embebido) con `datos/atribucion_<fuente>.csv` sintético en el formato real.
Necesita `DISPLAY` para la parte de ventana.
"""

import tkinter as tk
from tkinter import ttk

import pytest

import revisa_seiscomp as rs

pytestmark = pytest.mark.gui

_ATRIBUCION = (
    "n_fila_eventquery,fecha_eventquery,lat_eventquery,lon_eventquery,"
    "prof_eventquery,mag_eventquery,tipo_mag_eventquery,percibido,fecha_local,"
    "lat_local,lon_local,prof_local,mag_local,tipo_mag_local,analista,dt_seg,"
    "dlat,dlon,dist_km,n_candidatos,fuente\n"
    "0,2026-09-05 00:00:00,-33.000,-71.000,30.0,5.0,ML,S,"
    "2026-09-05 00:00:02,-33.000,-71.000,30.0,5.5,ML,ana,2.0,0.000,0.000,,1,"
    "seiscomp\n")

_ATRIBUCION_SIN_DISCREPANCIA = (
    "n_fila_eventquery,fecha_eventquery,lat_eventquery,lon_eventquery,"
    "prof_eventquery,mag_eventquery,tipo_mag_eventquery,percibido,fecha_local,"
    "lat_local,lon_local,prof_local,mag_local,tipo_mag_local,analista,dt_seg,"
    "dlat,dlon,dist_km,n_candidatos,fuente\n"
    "0,2026-09-05 00:00:00,-33.000,-71.000,30.0,5.0,ML,S,"
    "2026-09-05 00:00:02,-33.000,-71.000,30.0,5.0,ML,ana,2.0,0.000,0.000,,1,"
    "seiscomp\n")


def _buscar(widget, tipo, predicado=None):
    for hijo in widget.winfo_children():
        if isinstance(hijo, tipo) and (predicado is None or predicado(hijo)):
            return hijo
        encontrado = _buscar(hijo, tipo, predicado)
        if encontrado is not None:
            return encontrado
    return None


def _escribir(cwd, rel, texto):
    ruta = cwd / rel
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(texto, encoding="utf-8")
    return ruta


def _contenedor(raiz):
    marco = ttk.Frame(raiz)
    marco.pack()
    return marco


# --------------------------------------------------------------------------
# _no_actualizados (helper)
# --------------------------------------------------------------------------
def test_no_actualizados_helper(cwd_tmp):
    _escribir(cwd_tmp, "datos/atribucion_seiscomp.csv", _ATRIBUCION)
    filas = rs._no_actualizados("seiscomp")
    assert len(filas) == 1
    assert filas[0]["analista"] == "ana"
    # La discrepancia se anota (mag difiere 5.5 vs 5.0).
    assert filas[0]["discrepancias"] == "mag"


def test_no_actualizados_helper_sin_archivo(cwd_tmp):
    assert rs._no_actualizados("seiscomp") is None


def test_no_actualizados_helper_sin_discrepancias(cwd_tmp):
    _escribir(cwd_tmp, "datos/atribucion_seiscomp.csv",
              _ATRIBUCION_SIN_DISCREPANCIA)
    assert rs._no_actualizados("seiscomp") == []


# --------------------------------------------------------------------------
# abrir_no_actualizados (ventana real)
# --------------------------------------------------------------------------
def test_abrir_no_actualizados_real(raiz_tk, cwd_tmp):
    _escribir(cwd_tmp, "datos/atribucion_seiscomp.csv", _ATRIBUCION)
    contenedor = _contenedor(raiz_tk)

    assert rs.abrir_no_actualizados(contenedor, "seiscomp") is True
    arbol = _buscar(contenedor, ttk.Treeview)
    assert arbol is not None
    assert len(arbol.get_children()) == 1


def test_abrir_no_actualizados_sin_csv(raiz_tk, cwd_tmp):
    contenedor = _contenedor(raiz_tk)
    assert rs.abrir_no_actualizados(contenedor, "seiscomp") is False


def test_abrir_no_actualizados_sin_discrepancias(raiz_tk, cwd_tmp):
    _escribir(cwd_tmp, "datos/atribucion_seiscomp.csv",
              _ATRIBUCION_SIN_DISCREPANCIA)
    contenedor = _contenedor(raiz_tk)
    # Con CSV pero sin cruces discrepantes: tabla vacía, pero operativa.
    assert rs.abrir_no_actualizados(contenedor, "seiscomp") is True
    arbol = _buscar(contenedor, ttk.Treeview)
    assert len(arbol.get_children()) == 0
