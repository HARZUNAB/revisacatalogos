#!/usr/bin/env python3
"""
Tests de bordes de agencias.py
==============================
Casos borde de la asociación espacio-temporal y del agrupado entre agencias que
el test base no cubre: límites exactos de la ventana y de la tolerancia, el
cruce de la medianoche, `_flags` sin la clave de magnitud, deduplicado de
nombres y el encadenado de tres agencias.

El módulo no se modifica en esta tanda: los casos que fijan un comportamiento
dudoso (cruce de medianoche, encadenado) quedan anotados para revisarlos aparte.
"""

import datetime

import pytest

import agencias as a


def _dt(texto):
    return datetime.datetime.strptime(texto, "%Y-%m-%d %H:%M:%S")


def _pub(fecha, lat, lon, prof="30.0", mag="5.0"):
    return {
        "_dt": _dt(fecha), "_lat": lat, "_lon": lon,
        "prof": prof, "magnitud": mag,
        "fecha hora": fecha, "latitud": str(lat), "longitud": str(lon),
    }


def _ag(fecha, lat, lon, prof="30.0", mag="5.0", agencia="EMSC"):
    return {
        "fecha hora": fecha, "latitud": str(lat), "longitud": str(lon),
        "prof": prof, "magnitud": mag, "agencia": agencia,
    }


# --------------------------------------------------------------------------
# _mejor_publicado: límites exactos
# --------------------------------------------------------------------------
def test_mejor_publicado_ventana_exacta():
    # Δt = 6.0 s entra (el corte es dt > 6).
    pub = _pub("2026-01-01 00:00:00", -33.0, -71.0)
    assert a._mejor_publicado([pub], _ag("2026-01-01 00:00:06", -33.0, -71.0)) is pub


def test_mejor_publicado_tolerancia_espacial_exacta():
    # Δlat = 0.25° entra (el corte es > 0.25).
    pub = _pub("2026-01-01 00:00:00", -33.0, -71.0)
    assert a._mejor_publicado([pub], _ag("2026-01-01 00:00:00", -33.25, -71.0)) is pub


def test_mejor_publicado_cruce_de_medianoche_no_asocia():
    # Dos soluciones del mismo evento a 4 s, pero en días distintos: no asocia.
    # Comportamiento actual; revisar aparte (la ventana de 6 s ya acota).
    pub = _pub("2026-01-02 00:00:02", -33.0, -71.0)
    assert a._mejor_publicado(
        [pub], _ag("2026-01-01 23:59:58", -33.0, -71.0)) is None


# --------------------------------------------------------------------------
# _flags
# --------------------------------------------------------------------------
def test_flags_sin_clave_dmag():
    # No debe romper por KeyError si falta 'dmag'.
    assert a._flags({"dt_seg": 5.0}) == "time-"


# --------------------------------------------------------------------------
# _texto_agencias
# --------------------------------------------------------------------------
def test_texto_agencias_deduplica_mismo_nombre_y_ubicacion():
    sols = [
        {"agencia": "EMSC", "latitud": "1.0", "longitud": "2.0"},
        {"agencia": "EMSC", "latitud": "1.0", "longitud": "2.0"},
    ]
    assert a._texto_agencias(sols) == "EMSC"


# --------------------------------------------------------------------------
# _asociar_entre_agencias: encadenado
# --------------------------------------------------------------------------
def test_asociar_encadenado_de_tres_no_se_une():
    # EMSC(0 s), USGS(+4 s), GFZ(+8 s): GFZ queda a 8 s del representante del
    # grupo, así que arma su propio grupo -> [2, 1].
    # Comportamiento actual; revisar aparte (solo compara contra grupo[0]).
    eventos = [
        _ag("2026-01-01 00:00:00", -33.0, -71.0, agencia="EMSC"),
        _ag("2026-01-01 00:00:04", -33.0, -71.0, agencia="USGS"),
        _ag("2026-01-01 00:00:08", -33.0, -71.0, agencia="GFZ"),
    ]
    grupos = a._asociar_entre_agencias(eventos)
    assert [len(g) for g in grupos] == [2, 1]


# --------------------------------------------------------------------------
# _max_distancia
# --------------------------------------------------------------------------
def test_max_distancia_con_coordenada_no_numerica():
    grupo = [
        {"latitud": "abc", "longitud": "-71.0"},
        {"latitud": "-33.0", "longitud": "-71.0"},
    ]
    assert a._max_distancia(grupo) == ""
