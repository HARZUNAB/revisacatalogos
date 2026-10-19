#!/usr/bin/env python3
"""
Tests de revisa_seiscomp.py — estaciones y sin arribos ampliado
==============================================================
Cubre `_ventana_estaciones` y `_ventana_sin_arribos_ampliada` con **ventana
real** y datos sintéticos. Sin mocks. Necesita `DISPLAY`.
"""

import threading
import time
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


def _buscar_todos(widget, tipo):
    encontrados = []
    for hijo in widget.winfo_children():
        if isinstance(hijo, tipo):
            encontrados.append(hijo)
        encontrados.extend(_buscar_todos(hijo, tipo))
    return encontrados


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


# --------------------------------------------------------------------------
# Formas de onda (on-demand)
# --------------------------------------------------------------------------
def test_estaciones_tiene_boton_formas_onda(raiz_tk, cwd_tmp):
    win = rs._ventana_estaciones(_padre(raiz_tk), EVENTO, FASES, NO_PICADAS,
                                 str(cwd_tmp), etiqueta_fuente="seiscomp")
    boton = _buscar(win, ttk.Button,
                    lambda w: w.cget("text") == "Consultar formas de onda")
    assert boton is not None


def test_estaciones_tabla_sin_arribos_tiene_tooltip_por_fila(raiz_tk, cwd_tmp):
    win = rs._ventana_estaciones(_padre(raiz_tk), EVENTO, FASES, NO_PICADAS,
                                 str(cwd_tmp), etiqueta_fuente="seiscomp")
    win.update()
    tablas = _buscar_todos(win, ttk.Treeview)
    # La segunda es la de sin arribos (la primera es la de llegadas).
    tabla = tablas[1]
    assert tabla.bind("<Motion>")
    # Los iid son índices, que es lo que usa el tooltip para ubicar la fila.
    assert list(tabla.get_children()) == ["0", "1"]


def test_estaciones_tooltip_muestra_la_evidencia_de_la_fila(raiz_tk, cwd_tmp):
    win = rs._ventana_estaciones(_padre(raiz_tk), EVENTO, FASES, NO_PICADAS,
                                 str(cwd_tmp), etiqueta_fuente="seiscomp")
    notebook = _buscar(win, ttk.Notebook)
    notebook.select(1)
    win.update()
    tabla = _buscar_todos(win, ttk.Treeview)[1]
    bbox = tabla.bbox(tabla.get_children()[0])
    assert bbox
    tabla.event_generate("<Motion>", x=bbox[0] + 5, y=bbox[1] + 5, when="now")

    tip = None
    fin = time.time() + 2.0
    while time.time() < fin and tip is None:
        raiz_tk.update()
        time.sleep(0.05)
        for w in _buscar_todos(win, tk.Toplevel):
            if w.overrideredirect():
                tip = w
                break
    assert tip is not None
    texto = "\n".join(
        str(c.cget("text")) for c in tip.winfo_children()
        if isinstance(c, tk.Label))
    # La primera fila (ABC) tiene actividad 1: debe decir «Indicio».
    assert "ABC" in texto and "Indicio" in texto, texto


def test_consultar_formas_muestra_progreso_y_deshabilita(raiz_tk, cwd_tmp,
                                                         monkeypatch):
    inicio = threading.Event()
    seguir = threading.Event()

    def consultar_falso(_specs, _desde, _hasta, al_progreso=None):
        if al_progreso:
            al_progreso("Consultando el archivo SDS…")
        inicio.set()
        seguir.wait(3)
        return {}

    monkeypatch.setattr(rs.disponibilidad, "consultar", consultar_falso)
    win = rs._ventana_estaciones(_padre(raiz_tk), EVENTO, FASES, NO_PICADAS,
                                 str(cwd_tmp), etiqueta_fuente="seiscomp")
    win.update()
    boton = _buscar(
        win, ttk.Button,
        lambda w: "Consultar formas de onda" in str(w.cget("text")))
    barra = _buscar(win, ttk.Progressbar)
    assert boton is not None and barra is not None
    assert barra.winfo_manager() == ""

    boton.invoke()
    assert inicio.wait(2)
    win.update()
    assert str(boton.cget("state")) == "disabled"
    assert "Consultando" in str(boton.cget("text"))
    assert barra.winfo_manager() == "pack"

    # El mensaje de fase llega por la cola y actualiza la etiqueta.
    fin = time.time() + 2.0
    while time.time() < fin and _label(win, "Consultando el archivo SDS") is None:
        win.update()
        time.sleep(0.05)
    assert _label(win, "Consultando el archivo SDS") is not None

    seguir.set()
    fin = time.time() + 3.0
    while time.time() < fin and str(boton.cget("state")) != "normal":
        win.update()
        time.sleep(0.05)
    assert str(boton.cget("state")) == "normal"
    assert "Consultar formas de onda" in str(boton.cget("text"))
    assert barra.winfo_manager() == ""


def test_consultar_disponibilidad_llena_las_filas(monkeypatch):
    filas = [dict(NO_PICADAS[0], streams_vigentes_ids="IU.ABC.00.BHZ"),
             dict(NO_PICADAS[1])]
    monkeypatch.setattr(
        rs.disponibilidad, "consultar",
        lambda specs, desde, hasta, **kwargs: {
            "IU.ABC.00.BHZ": {"status": "CON_DATOS", "source": "SDS",
                              "desde": "d", "hasta": "h"},
            "CX.XYZ..HHZ": {"status": "SIN_DATOS", "source": "",
                            "desde": "", "hasta": ""},
        })
    rs._consultar_disponibilidad(filas, rs._instante_de_evento(EVENTO))
    assert filas[0]["waveform_status"] == "CON_DATOS"
    assert filas[0]["availability_source"] == "SDS"
    assert filas[1]["waveform_status"] == "SIN_DATOS"
    assert rs._valores_no_picada(filas[0])[
        [c for c, _, _ in rs.COLUMNAS_NO_PICADA].index("formas_onda")] == "SDS"
    assert rs._valores_no_picada(filas[1])[
        [c for c, _, _ in rs.COLUMNAS_NO_PICADA].index("formas_onda")] == \
        "Sin datos"
