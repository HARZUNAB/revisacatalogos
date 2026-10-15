#!/usr/bin/env python3
"""
Tests de revisa_seiscomp.py — análisis rápido
=============================================
Cubre `analizar_sin_arribos` (helper) y `_ventana_analisis_rapido` con **ventana
real** y CSV sintético. Sin mocks. Necesita `DISPLAY`.
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

NO_PICADAS = (
    "id_evento,id_origen,red,estacion,loc_ref,cha_ref,streams_vigentes,"
    "distancia_km,est_lat,est_lon,est_elev,est_lugar,est_pais,radio_km,"
    "actividad_ventana,waveform_status,availability_source,cobertura_desde,"
    "cobertura_hasta\n"
    "E1,O1,IU,ABC,00,BHZ,2,10.0,-33.1,-71.1,500,Lugar,Chile,400.0,2,"
    "NO_CONSULTADO,,,\n"
    "E1,O1,CX,XYZ,,HHZ,1,120.0,-33.2,-71.2,600,Otro,Chile,400.0,0,"
    "NO_CONSULTADO,,,\n")


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


def _escribir(cwd, rel, texto):
    ruta = cwd / rel
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(texto, encoding="utf-8")
    return ruta


def _padre(raiz):
    padre = tk.Toplevel(raiz)
    padre.withdraw()
    return padre


# --------------------------------------------------------------------------
# analizar_sin_arribos (helper)
# --------------------------------------------------------------------------
def test_analizar_sin_arribos(cwd_tmp):
    ruta = _escribir(cwd_tmp, "datos/np.csv", NO_PICADAS)
    resumenes = rs.analizar_sin_arribos(str(ruta), [EVENTO])
    assert len(resumenes) == 1
    resumen = resumenes[0]
    # Solo la de 10 km entra en el umbral (50 km por defecto); con actividad 2.
    assert resumen["destacadas"] == 1
    assert resumen["cercanas"] == 0
    assert resumen["total"] == 2
    assert resumen["evento"] is EVENTO


def test_analizar_sin_arribos_sin_archivo(cwd_tmp):
    assert rs.analizar_sin_arribos("datos/no_existe.csv", [EVENTO]) == []


# --------------------------------------------------------------------------
# _ventana_analisis_rapido (ventana real)
# --------------------------------------------------------------------------
def test_ventana_analisis_rapido(raiz_tk, cwd_tmp):
    ruta = _escribir(cwd_tmp, "datos/np.csv", NO_PICADAS)
    win = rs._ventana_analisis_rapido(_padre(raiz_tk), str(ruta), [EVENTO],
                                      str(cwd_tmp), etiqueta_fuente="seiscomp")

    assert win.title() == "Análisis rápido — estaciones sin arribos cercanas"
    assert _tabs(win) == ["Contexto", "Resultados"]
    assert _label(win, "Analiza TODO el catálogo (1 eventos)") is not None
    arbol = _buscar(win, ttk.Treeview)
    assert arbol is not None
    assert len(arbol.get_children()) == 1
