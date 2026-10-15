#!/usr/bin/env python3
"""
Tests de bordes de agencias.py
==============================
Casos borde de la asociación espacio-temporal y del agrupado entre agencias que
el test base no cubre: límites exactos de la ventana y de la tolerancia, el
cruce de la medianoche, `_flags` sin la clave de magnitud, deduplicado de
nombres y el encadenado de tres agencias.
"""

import datetime
import json
import os
import sys

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


def test_mejor_publicado_cruce_de_medianoche_asocia():
    # Dos soluciones del mismo evento a 4 s, en días distintos: la ventana de
    # 6 s basta, no hace falta exigir el mismo día.
    pub = _pub("2026-01-02 00:00:02", -33.0, -71.0)
    assert a._mejor_publicado(
        [pub], _ag("2026-01-01 23:59:58", -33.0, -71.0)) is pub


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
def test_asociar_encadenado_de_tres_se_une():
    # EMSC(0 s), USGS(+4 s), GFZ(+8 s): GFZ está a 8 s de EMSC pero a 4 s de
    # USGS, así que se une al grupo -> [3].
    eventos = [
        _ag("2026-01-01 00:00:00", -33.0, -71.0, agencia="EMSC"),
        _ag("2026-01-01 00:00:04", -33.0, -71.0, agencia="USGS"),
        _ag("2026-01-01 00:00:08", -33.0, -71.0, agencia="GFZ"),
    ]
    grupos = a._asociar_entre_agencias(eventos)
    assert [len(g) for g in grupos] == [3]


# --------------------------------------------------------------------------
# _max_distancia
# --------------------------------------------------------------------------
def test_max_distancia_con_coordenada_no_numerica():
    grupo = [
        {"latitud": "abc", "longitud": "-71.0"},
        {"latitud": "-33.0", "longitud": "-71.0"},
    ]
    assert a._max_distancia(grupo) == ""


# --------------------------------------------------------------------------
# main(): ventana sin datos en el publicado o en las agencias
# --------------------------------------------------------------------------
def _escribir_json(cwd, nombre, datos):
    carpeta = os.path.join(str(cwd), "datos")
    os.makedirs(carpeta, exist_ok=True)
    with open(os.path.join(carpeta, nombre), "w") as f:
        json.dump(datos, f)


def _leer_json(cwd, nombre):
    with open(os.path.join(str(cwd), "datos", nombre)) as f:
        return json.load(f)


def _pub_json(fecha="2026-01-01 00:00:00", lat=-33.0, lon=-71.0, mag="5.0"):
    return {"fecha hora": fecha, "latitud": str(lat), "longitud": str(lon),
            "prof": "30.0", "magnitud": mag}


def _ag_json(fecha="2026-01-01 00:00:04", lat=-33.0, lon=-71.0, mag="5.2"):
    return {"fecha hora": fecha, "latitud": str(lat), "longitud": str(lon),
            "prof": "30.0", "magnitud": mag}


def test_mejor_publicado_sin_publicados():
    assert a._mejor_publicado([], _ag("2026-01-01 00:00:00", -33.0, -71.0)) is None


def test_main_publicado_faltante_sale(cwd_tmp, monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["agencias.py", "3.0", "EMSC"])
    with pytest.raises(SystemExit) as exc:
        a.main()
    assert exc.value.code == 1
    assert "procese ese catálogo" in capsys.readouterr().out


def test_main_publicado_vacio_todo_sin_par(cwd_tmp, monkeypatch):
    _escribir_json(cwd_tmp, "eventos_eventquery.json", [])
    _escribir_json(cwd_tmp, "eventos_agencia_EMSC.json", [_ag_json()])
    monkeypatch.setattr(sys, "argv", ["agencias.py", "3.0", "EMSC"])
    a.main()
    assert _leer_json(cwd_tmp, "comparacion_agencias.json") == []
    assert len(_leer_json(cwd_tmp, "agencias_sin_par.json")) == 1


def test_main_agencia_faltante_se_omite(cwd_tmp, monkeypatch, capsys):
    _escribir_json(cwd_tmp, "eventos_eventquery.json", [_pub_json()])
    monkeypatch.setattr(sys, "argv", ["agencias.py", "3.0", "EMSC"])
    a.main()
    assert "se omite EMSC" in capsys.readouterr().out
    comparacion = _leer_json(cwd_tmp, "comparacion_agencias.json")
    assert len(comparacion) == 1 and comparacion[0]["agencias"] == []


def test_main_agencia_vacia_sin_asociaciones(cwd_tmp, monkeypatch):
    _escribir_json(cwd_tmp, "eventos_eventquery.json", [_pub_json()])
    _escribir_json(cwd_tmp, "eventos_agencia_EMSC.json", [])
    monkeypatch.setattr(sys, "argv", ["agencias.py", "3.0", "EMSC"])
    a.main()
    comparacion = _leer_json(cwd_tmp, "comparacion_agencias.json")
    assert len(comparacion) == 1 and comparacion[0]["agencias"] == []
    assert _leer_json(cwd_tmp, "agencias_sin_par.json") == []


def test_main_todas_las_agencias_faltantes(cwd_tmp, monkeypatch):
    _escribir_json(cwd_tmp, "eventos_eventquery.json", [_pub_json()])
    monkeypatch.setattr(sys, "argv", ["agencias.py", "3.0", "EMSC", "USGS"])
    a.main()
    comparacion = _leer_json(cwd_tmp, "comparacion_agencias.json")
    assert len(comparacion) == 1 and comparacion[0]["agencias"] == []
    assert _leer_json(cwd_tmp, "agencias_sin_par.json") == []
