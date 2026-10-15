#!/usr/bin/env python3
"""
Tests de revisa_seiscomp.py — estaciones y sin arribos ampliado
==============================================================
Cubre `_ventana_estaciones` y `_ventana_sin_arribos_ampliada` con **ventana
real** y datos sintéticos. Sin mocks. Necesita `DISPLAY`.
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

NO_PICADAS = [
    {"distancia_km": "12.3", "red": "IU", "estacion": "ABC", "loc_ref": "00",
     "cha_ref": "BHZ", "streams_vigentes": 2, "est_elev": "1500",
     "est_lugar": "Lugar", "est_pais": "Chile", "radio_km": 400.0,
     "actividad_ventana": "1"},
    {"distancia_km": "40.0", "red": "CX", "estacion": "XYZ", "loc_ref": "",
     "cha_ref": "HHZ", "streams_vigentes": 1, "est_elev": "600",
     "est_lugar": "Otro", "est_pais": "Chile", "radio_km": 400.0,
     "actividad_ventana": "0"},
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


def _tabs(win):
    cuaderno = _buscar(win, ttk.Notebook)
    return [cuaderno.tab(t, "text") for t in cuaderno.tabs()]


def _padre(raiz):
    padre = tk.Toplevel(raiz)
    padre.withdraw()
    return padre


# --------------------------------------------------------------------------
# _ventana_estaciones
# --------------------------------------------------------------------------
def test_estaciones_real(raiz_tk, cwd_tmp):
    win = rs._ventana_estaciones(_padre(raiz_tk), EVENTO, FASES, NO_PICADAS,
                                 str(cwd_tmp), etiqueta_fuente="seiscomp")
    assert win.title() == "Estaciones del evento E1"
    assert _tabs(win) == ["Con arribos", "Sin arribos"]
    assert _buscar(win, ttk.Treeview) is not None


def test_estaciones_sin_archivo_no_picadas(raiz_tk, cwd_tmp):
    win = rs._ventana_estaciones(_padre(raiz_tk), EVENTO, FASES, [],
                                 str(cwd_tmp), hay_no_picadas=False)
    assert _label(win, "no trae el archivo de estaciones") is not None


def test_estaciones_reusa_ventana(raiz_tk, cwd_tmp):
    padre = _padre(raiz_tk)
    w1 = rs._ventana_estaciones(padre, EVENTO, FASES, NO_PICADAS,
                                str(cwd_tmp))
    w2 = rs._ventana_estaciones(padre, dict(EVENTO, id_evento="E2"), FASES,
                                NO_PICADAS, str(cwd_tmp), ventana_previa=w1)
    assert w2 is w1
    assert w1.title() == "Estaciones del evento E2"


# --------------------------------------------------------------------------
# _ventana_sin_arribos_ampliada
# --------------------------------------------------------------------------
def test_sin_arribos_ampliada(raiz_tk, cwd_tmp):
    win = rs._ventana_sin_arribos_ampliada(_padre(raiz_tk), EVENTO, NO_PICADAS,
                                           400.0, "seiscomp", str(cwd_tmp))
    assert win.title() == "Sin arribos ampliado — E1"
    assert _label(win, "radio 400 km") is not None
    assert _label(win, "2 estaciones") is not None
    assert _buscar(win, ttk.Treeview) is not None
