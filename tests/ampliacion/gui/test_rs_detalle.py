#!/usr/bin/env python3
"""
Tests de revisa_seiscomp.py — ventana detalle
=============================================
Cubre `_ventana_detalle` con **ventana real** y datos sintéticos. Sin mocks.
Necesita `DISPLAY`.
"""

import tkinter as tk
from tkinter import ttk

import pytest

import revisa_seiscomp as rs

pytestmark = pytest.mark.gui

EVENTO = {
    "id_evento": "E1", "id_origen": "O1", "ot_utc": "2026-09-05 00:00:00",
    "magnitud": "5.0", "tipo_magnitud": "ML", "fases": "12", "rms": "0.3",
    "azgap": "45", "latitud": "-33.000", "longitud": "-71.000",
    "profundidad_km": "30.0", "agencia": "CSN", "operador": "ana",
    "region": "Region", "estatus": "reviewed", "base_datos": "seiscomp",
}

FASES = [
    {"red": "IU", "estacion": "ABC", "loc": "00", "cha": "BHZ", "fase": "P",
     "llegada_utc": "2026-09-05 00:00:10", "llegada_us": "500000",
     "usada": "true", "modo_pick": "manual", "azimut": "30", "distancia": "0.5",
     "tiene_magnitud": "Si", "mag_estacion": "4.1", "tipo_mag_estacion": "ML",
     "mag_est_residuo": "0.1"},
    {"red": "CX", "estacion": "XYZ", "loc": "", "cha": "HHZ", "fase": "S",
     "llegada_utc": "2026-09-05 00:00:20", "llegada_us": "0",
     "usada": "false", "modo_pick": "automatic", "azimut": "80",
     "distancia": "1.2", "tiene_magnitud": "No", "mag_est_residuo": ""},
]


def _buscar(widget, tipo, predicado=None):
    for hijo in widget.winfo_children():
        if isinstance(hijo, tipo) and (predicado is None or predicado(hijo)):
            return hijo
        encontrado = _buscar(hijo, tipo, predicado)
        if encontrado is not None:
            return encontrado
    return None


def _label(widget, fragmento):
    return _buscar(widget, ttk.Label,
                   lambda w: fragmento in str(w.cget("text")))


def _padre(raiz):
    padre = tk.Toplevel(raiz)
    padre.withdraw()
    return padre


def test_detalle_real(raiz_tk):
    win = rs._ventana_detalle(_padre(raiz_tk), EVENTO, FASES,
                              etiqueta_fuente="seiscomp",
                              al_estaciones=lambda: None)
    assert win.winfo_exists()
    assert win.title() == "Parámetros del evento E1"
    assert _buscar(win, ttk.Button,
                   lambda w: w.cget("text") == "Estaciones") is not None
    # El resumen de llegadas.
    assert _label(win, "llegadas de") is not None


def test_detalle_sin_boton_estaciones(raiz_tk):
    # Sin callback no se arma el botón (fuentes sin llegadas).
    win = rs._ventana_detalle(_padre(raiz_tk), EVENTO, FASES)
    assert _buscar(win, ttk.Button,
                   lambda w: w.cget("text") == "Estaciones") is None


def test_detalle_sin_fases(raiz_tk):
    win = rs._ventana_detalle(_padre(raiz_tk), EVENTO, [], sin_fases=True)
    assert _label(win, "no trae detalle de llegadas") is not None


def test_detalle_reusa_ventana(raiz_tk):
    padre = _padre(raiz_tk)
    w1 = rs._ventana_detalle(padre, EVENTO, FASES)
    w2 = rs._ventana_detalle(padre, dict(EVENTO, id_evento="E2"), FASES,
                             ventana_previa=w1)
    assert w2 is w1
    assert w1.title() == "Parámetros del evento E2"
