#!/usr/bin/env python3
"""
Tests de revisa_seiscomp.py — panel y catálogo
==============================================
Cubre `abrir_panel` (panel de revisión embebido) y `abrir_catalogo` (listado
crudo) con **ventanas reales** y CSV sintéticos en el formato real. Necesita
`DISPLAY`.
"""

import tkinter as tk
from tkinter import ttk

import pytest

import revisa_seiscomp as rs

pytestmark = pytest.mark.gui


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


_CATALOGO = (
    ",Fecha_Hora,Latitud,Longitud,Prof.,Mag.,Tipo_mag.,Analista\n"
    "0,2026-09-05  00:00:02,-33.000,-71.000,30.0,5.5,ML,ana\n"
    "1,2026-09-06  12:00:05,-30.040,-70.000,20.0,4.0,ML,beto\n")

_EVENTOS = (
    "id_evento,id_origen,ot_utc,magnitud,tipo_magnitud,fases,rms,azgap,"
    "latitud,longitud,profundidad_km,agencia,operador,region,estatus,"
    "base_datos\n"
    "E1,O1,2026-09-05 00:00:00,5.0,ML,12,0.30,45,-33.000,-71.000,30.0,CSN,ana,"
    "Region,reviewed,seiscomp\n")

_FASES = (
    "id_evento,id_origen,id_pick,red,estacion,loc,cha,fase,llegada_utc,"
    "llegada_us,correccion_s,residual_s,azimut,distancia,usada,peso,polaridad,"
    "modo_pick,pick_autor,pick_agencia,pick_metodo,snr,mag_estacion,"
    "tipo_mag_estacion,tiene_magnitud,mag_est_residuo,qc_estacion,est_lat,"
    "est_lon,est_elev,est_lugar,est_pais,base_datos\n"
    "E1,O1,P1,IU,ABC,00,BHZ,P,2026-09-05 00:00:10,500000,0.0,0.25,45.0,0.5,"
    "true,1.0,,manual,aa,IU,manual,12.0,4.9,ML,Si,0.1,aprobado,-33.1,-71.1,"
    "500,Lugar,Chile,seiscomp\n")


# --------------------------------------------------------------------------
# abrir_catalogo
# --------------------------------------------------------------------------
def test_abrir_catalogo_real(raiz_tk, cwd_tmp):
    _escribir(cwd_tmp, "datos/salida_collect.csv", _CATALOGO)
    contenedor = _contenedor(raiz_tk)

    assert rs.abrir_catalogo(contenedor, "datos/salida_collect.csv",
                             "seisan") is True
    arbol = _buscar(contenedor, ttk.Treeview)
    assert arbol is not None
    assert len(arbol.get_children()) == 2


def test_abrir_catalogo_sin_archivo(raiz_tk, cwd_tmp):
    contenedor = _contenedor(raiz_tk)
    assert rs.abrir_catalogo(contenedor, "datos/no_existe.csv", "seisan") is False


def test_abrir_catalogo_solo_encabezado(raiz_tk, cwd_tmp):
    _escribir(cwd_tmp, "datos/vacio.csv",
              ",Fecha_Hora,Latitud,Longitud,Prof.,Mag.,Tipo_mag.,Analista\n")
    contenedor = _contenedor(raiz_tk)
    # Sin filas de datos no hay nada que mostrar.
    assert rs.abrir_catalogo(contenedor, "datos/vacio.csv", "seisan") is False


def test_abrir_catalogo_tiene_miniatura(raiz_tk, cwd_tmp):
    _escribir(cwd_tmp, "datos/salida_collect.csv", _CATALOGO)
    contenedor = _contenedor(raiz_tk)

    assert rs.abrir_catalogo(contenedor, "datos/salida_collect.csv",
                             "seisan") is True
    # La lista va junto a la miniatura en un divisor (lista | miniatura).
    assert _buscar(contenedor, ttk.PanedWindow) is not None


def test_catalogo_seleccionar_actualiza_miniatura(raiz_tk, cwd_tmp):
    _escribir(cwd_tmp, "datos/salida_collect.csv", _CATALOGO)
    contenedor = _contenedor(raiz_tk)
    assert rs.abrir_catalogo(contenedor, "datos/salida_collect.csv",
                             "seisan") is True
    arbol = _buscar(contenedor, ttk.Treeview)
    # Elegir una fila dispara la miniatura sin abrir ninguna ventana.
    arbol.selection_set(arbol.get_children()[0])
    arbol.event_generate("<<TreeviewSelect>>")
    raiz_tk.update()


def _casilla_hist(widget):
    return _buscar(widget, ttk.Checkbutton,
                   lambda w: w.cget("text") == "Sismicidad histórica")


def test_abrir_catalogo_tiene_casilla_hist(raiz_tk, cwd_tmp):
    _escribir(cwd_tmp, "datos/salida_collect.csv", _CATALOGO)
    contenedor = _contenedor(raiz_tk)
    assert rs.abrir_catalogo(contenedor, "datos/salida_collect.csv",
                             "seisan") is True
    chk = _casilla_hist(contenedor)
    assert chk is not None
    # Activar la casilla redibuja la miniatura sin error.
    chk.invoke()
    raiz_tk.update()


# --------------------------------------------------------------------------
# abrir_panel
# --------------------------------------------------------------------------
def test_abrir_panel_real(raiz_tk, cwd_tmp):
    _escribir(cwd_tmp, "datos/seiscomp_20260901000000_20260930235959.csv",
              _EVENTOS)
    _escribir(cwd_tmp,
              "datos/seiscomp_20260901000000_20260930235959_fases.csv", _FASES)
    contenedor = _contenedor(raiz_tk)

    ok = rs.abrir_panel(
        contenedor,
        "datos/seiscomp_20260901000000_20260930235959.csv",
        "datos/seiscomp_20260901000000_20260930235959_fases.csv")

    assert ok is True
    assert _buscar(contenedor, ttk.Treeview) is not None
    # El panel de SeisComp también trae la miniatura al lado de la lista.
    assert _buscar(contenedor, ttk.PanedWindow) is not None
    assert _casilla_hist(contenedor) is not None


def test_abrir_panel_sin_eventos(raiz_tk, cwd_tmp):
    contenedor = _contenedor(raiz_tk)
    assert rs.abrir_panel(contenedor, "datos/no_existe.csv") is False


def test_abrir_panel_fases_faltantes_requiere_permiso(raiz_tk, cwd_tmp):
    _escribir(cwd_tmp, "datos/ev.csv", _EVENTOS)
    contenedor = _contenedor(raiz_tk)
    # Sin fases: fatal salvo permiso explícito.
    assert rs.abrir_panel(contenedor, "datos/ev.csv") is False
    assert rs.abrir_panel(contenedor, "datos/ev.csv",
                          permitir_sin_fases=True) is True
