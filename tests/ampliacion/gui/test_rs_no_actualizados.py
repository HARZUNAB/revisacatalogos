#!/usr/bin/env python3
"""
Tests de revisa_seiscomp.py — no actualizados
=============================================
Cubre `_no_actualizados` (helper puro) y `abrir_no_actualizados` (listado real
embebido) con `datos/atribucion_<fuente>.csv` sintético en el formato real.
Necesita `DISPLAY` para la parte de ventana.
"""

import os
import time
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

_ATRIBUCION_OTRA = (
    "fecha_eventquery,lat_eventquery,lon_eventquery,fecha_local,lat_local,"
    "lon_local,prof_local,mag_local,tipo_mag_local,prof_eventquery,"
    "mag_eventquery,tipo_mag_eventquery,analista,dt_seg,dist_km\n"
    "2026-09-05 00:00:00,-33.000,-71.000,2026-09-05 00:00:02,-33.000,"
    "-71.000,30.0,5.0,ML,30.0,5.0,ML,otro,2.0,0.0\n")

_CATALOGO_OTRA = (
    "Fecha_Hora,Latitud,Longitud,Prof.,Mag.,Tipo_mag.,Analista\n"
    "2026-09-05 00:00:00,-33.000,-71.000,30.0,5.0,ML,otro\n")

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


def _escribir_vigente(cwd, rel, texto):
    """Escribe una atribución después de su catálogo, para que esté vigente."""
    ruta = _escribir(cwd, rel, texto)
    futuro = time.time() + 5
    os.utime(ruta, (futuro, futuro))
    return ruta


def _contenedor(raiz):
    marco = ttk.Frame(raiz)
    marco.pack()
    return marco


@pytest.fixture(autouse=True)
def _cache_no_actualizados_limpia():
    rs._limpiar_cache_no_actualizados()
    yield
    rs._limpiar_cache_no_actualizados()


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


def test_abrir_no_actualizados_muestra_tipos_de_magnitud(
        raiz_tk, cwd_tmp, monkeypatch):
    _escribir(cwd_tmp, "datos/atribucion_seiscomp.csv", _ATRIBUCION)
    contenedor = _contenedor(raiz_tk)
    assert rs.abrir_no_actualizados(contenedor, "seiscomp") is True
    arbol = _buscar(contenedor, ttk.Treeview)
    claves = list(arbol["columns"])
    valores = arbol.item(arbol.get_children()[0], "values")

    assert arbol.heading("tipo_mag_local", "text") == \
        "Tipo mag. (SeisComp)"
    assert arbol.heading("tipo_mag_eventquery", "text") == \
        "Tipo mag. publicada"
    assert valores[claves.index("tipo_mag_local")] == "ML"
    assert valores[claves.index("tipo_mag_eventquery")] == "ML"

    exportado = {}

    def exportar(filas, valores, columnas, cwd, etiqueta, **kwargs):
        exportado["columnas"] = [c[0] for c in columnas]
        exportado["filas"] = [valores(f) for f in filas]
        return "datos/no_actualizados.csv"

    monkeypatch.setattr(rs, "_exportar_listado", exportar)
    boton = _buscar(contenedor, ttk.Button,
                    lambda w: w.cget("text") == "Descargar")
    boton.invoke()

    assert "tipo_mag_local" in exportado["columnas"]
    assert "tipo_mag_eventquery" in exportado["columnas"]
    pos_local = exportado["columnas"].index("tipo_mag_local")
    pos_publicada = exportado["columnas"].index("tipo_mag_eventquery")
    assert exportado["filas"][0][pos_local] == "ML"
    assert exportado["filas"][0][pos_publicada] == "ML"


def test_abrir_no_actualizados_sin_csv(raiz_tk, cwd_tmp):
    contenedor = _contenedor(raiz_tk)
    assert rs.abrir_no_actualizados(contenedor, "seiscomp") is False


def test_abrir_no_actualizados_tiene_aplicar(raiz_tk, cwd_tmp):
    _escribir(cwd_tmp, "datos/atribucion_seiscomp.csv", _ATRIBUCION)
    contenedor = _contenedor(raiz_tk)
    assert rs.abrir_no_actualizados(contenedor, "seiscomp") is True
    boton = _buscar(contenedor, ttk.Button,
                    lambda w: w.cget("text") == "Aplicar")
    assert boton is not None
    assert _buscar(contenedor, ttk.Button,
                   lambda w: w.cget("text") == "Mostrar todo") is not None
    # Aplicar re-filtra sin error.
    boton.invoke()
    raiz_tk.update()


def test_no_actualizados_muestra_frontera_local_y_publicada(
        raiz_tk, cwd_tmp, monkeypatch):
    _escribir(cwd_tmp, "datos/atribucion_seiscomp.csv", _ATRIBUCION)
    monkeypatch.setattr(
        rs.fronteras, "frontera_mas_cercana",
        lambda lat, lon: ("Perú", 34.9))
    contenedor = _contenedor(raiz_tk)

    assert rs.abrir_no_actualizados(contenedor, "seiscomp") is True
    arbol = _buscar(contenedor, ttk.Treeview)
    arbol.selection_set(arbol.get_children()[0])
    arbol.event_generate("<<TreeviewSelect>>")
    raiz_tk.update()

    etiqueta = _buscar(
        contenedor, ttk.Label,
        lambda w: str(w.cget("text")).startswith("Frontera local:"))
    assert etiqueta is not None
    assert "Frontera local: Perú — 34.9 km" in etiqueta.cget("text")
    assert "Frontera publicada: Perú — 34.9 km" in etiqueta.cget("text")


def test_abrir_no_actualizados_sin_discrepancias(raiz_tk, cwd_tmp):
    _escribir(cwd_tmp, "datos/atribucion_seiscomp.csv",
              _ATRIBUCION_SIN_DISCREPANCIA)
    contenedor = _contenedor(raiz_tk)
    # Con CSV pero sin cruces discrepantes: tabla vacía, pero operativa.
    assert rs.abrir_no_actualizados(contenedor, "seiscomp") is True
    arbol = _buscar(contenedor, ttk.Treeview)
    assert len(arbol.get_children()) == 0



def test_no_actualizados_clasifica_con_la_otra_fuente(cwd_tmp):
    _escribir(cwd_tmp, "datos/salida_collect.csv", _CATALOGO_OTRA)
    _escribir(cwd_tmp, "datos/atribucion_seiscomp.csv", _ATRIBUCION)
    _escribir_vigente(cwd_tmp, "datos/atribucion_seisan.csv", _ATRIBUCION_OTRA)

    filas = rs._no_actualizados("seiscomp")

    assert len(filas) == 1
    assert filas[0]["publicacion_probable"] == "Otra fuente"
    assert filas[0]["revision"] == "Baja"
    assert filas[0]["revision_orden"] == 3


def test_no_actualizados_columnas_y_ayuda(raiz_tk, cwd_tmp, monkeypatch):
    _escribir(cwd_tmp, "datos/salida_collect.csv", _CATALOGO_OTRA)
    _escribir(cwd_tmp, "datos/atribucion_seiscomp.csv", _ATRIBUCION)
    _escribir_vigente(cwd_tmp, "datos/atribucion_seisan.csv", _ATRIBUCION_OTRA)
    contenedor = _contenedor(raiz_tk)

    assert rs.abrir_no_actualizados(contenedor, "seiscomp") is True
    claves = [c for c, _t, _a in rs._columnas_no_actualizado("seiscomp")]
    assert claves.index("publicacion_probable") == claves.index("analista") + 1
    assert claves.index("revision") == claves.index("analista") + 2
    boton = _buscar(contenedor, ttk.Button,
                    lambda w: w.cget("text") == "Criterios de clasificación")
    assert boton is not None

    llamado = []
    monkeypatch.setattr(rs.descargas, "mostrar_texto_mono",
                        lambda *a, **k: llamado.append(a))
    boton.invoke()
    assert llamado
    assert llamado[0][1] == "Clasificación de No actualizados"
    assert llamado[0][2] == rs.cruce_noact.AYUDA_REVISION_NO_ACTUALIZADOS


def test_no_actualizados_reusa_cache_si_no_cambian_los_archivos(
        cwd_tmp, monkeypatch):
    _escribir(cwd_tmp, "datos/atribucion_seiscomp.csv", _ATRIBUCION)
    leidas = []
    original = rs._leer_csv

    def contar(ruta):
        leidas.append(ruta)
        return original(ruta)

    monkeypatch.setattr(rs, "_leer_csv", contar)

    primera = rs._no_actualizados("seiscomp")
    segunda = rs._no_actualizados("seiscomp")

    assert primera is segunda
    assert len(leidas) == 1


def test_no_actualizados_invalida_cache_si_cambia_su_atribucion(
        cwd_tmp, monkeypatch):
    ruta = _escribir(cwd_tmp, "datos/atribucion_seiscomp.csv", _ATRIBUCION)
    leidas = []
    original = rs._leer_csv

    def contar(camino):
        leidas.append(camino)
        return original(camino)

    monkeypatch.setattr(rs, "_leer_csv", contar)
    rs._no_actualizados("seiscomp")

    ruta.write_text(_ATRIBUCION + _ATRIBUCION.split("\n", 1)[1],
                    encoding="utf-8")
    rs._no_actualizados("seiscomp")

    assert len(leidas) == 2


def test_no_actualizados_invalida_cache_si_cambia_la_otra_fuente(
        cwd_tmp, monkeypatch):
    _escribir(cwd_tmp, "datos/salida_collect.csv", _CATALOGO_OTRA)
    _escribir(cwd_tmp, "datos/atribucion_seiscomp.csv", _ATRIBUCION)
    _escribir_vigente(cwd_tmp, "datos/atribucion_seisan.csv", _ATRIBUCION_OTRA)
    llamadas = []
    original = rs.cruce_noact.cargar_otra

    def contar(*args, **kwargs):
        llamadas.append(1)
        return original(*args, **kwargs)

    monkeypatch.setattr(rs.cruce_noact, "cargar_otra", contar)
    rs._no_actualizados("seiscomp")
    rs._no_actualizados("seiscomp")
    assert len(llamadas) == 1

    _escribir_vigente(
        cwd_tmp, "datos/atribucion_seisan.csv",
        _ATRIBUCION_OTRA + _ATRIBUCION_OTRA.split("\n", 1)[1])
    rs._no_actualizados("seiscomp")

    assert len(llamadas) == 2


def test_no_actualizados_invalida_cache_si_cambia_el_catalogo(
        cwd_tmp, monkeypatch):
    catalogo = _escribir(cwd_tmp, "datos/salida_collect.csv", _CATALOGO_OTRA)
    _escribir(cwd_tmp, "datos/atribucion_seiscomp.csv", _ATRIBUCION)
    _escribir_vigente(cwd_tmp, "datos/atribucion_seisan.csv", _ATRIBUCION_OTRA)
    llamadas = []
    original = rs.cruce_noact.cargar_otra

    def contar(*args, **kwargs):
        llamadas.append(1)
        return original(*args, **kwargs)

    monkeypatch.setattr(rs.cruce_noact, "cargar_otra", contar)
    rs._no_actualizados("seiscomp")
    assert len(llamadas) == 1

    catalogo.write_text(_CATALOGO_OTRA + _CATALOGO_OTRA.split("\n", 1)[1],
                        encoding="utf-8")
    futuro = time.time() + 5
    os.utime(catalogo, (futuro, futuro))
    rs._no_actualizados("seiscomp")

    assert len(llamadas) == 2
