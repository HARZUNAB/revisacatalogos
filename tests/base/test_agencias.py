#!/usr/bin/env python3
"""
Tests de agencias.py
====================
Cubre la asociación espacio-temporal entre el catálogo publicado y los de las
agencias, los deltas, las banderas de fuera de rango y los textos/agrupaciones
con que se presentan las soluciones superpuestas.
"""

import datetime

import pytest

import agencias as a


def _dt(texto):
    return datetime.datetime.strptime(texto, "%Y-%m-%d %H:%M:%S")


def _pub(fecha, lat, lon, prof="30.0", mag="5.0"):
    """Evento publicado 'interno': con las claves _dt/_lat/_lon ya indexadas."""
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
# _instante
# --------------------------------------------------------------------------
@pytest.mark.parametrize("texto", [
    "2026-01-01 00:00:00",
    "2026-01-01T00:00:00",
    "2026-01-01T00:00:00.123",
])
def test_instante_formatos(texto):
    assert a._instante(texto) == _dt("2026-01-01 00:00:00")


def test_instante_invalido():
    assert a._instante("") is None
    assert a._instante(None) is None
    assert a._instante("no es fecha") is None


# --------------------------------------------------------------------------
# _mejor_publicado
# --------------------------------------------------------------------------
def test_mejor_publicado_encuentra_el_mismo_evento():
    pub = _pub("2026-01-01 00:00:00", -33.0, -71.0)
    assert a._mejor_publicado([pub], _ag("2026-01-01 00:00:04", -33.0, -71.0)) is pub


def test_mejor_publicado_distinto_dia():
    pub = _pub("2026-01-02 00:00:00", -33.0, -71.0)
    assert a._mejor_publicado([pub], _ag("2026-01-01 00:00:00", -33.0, -71.0)) is None


def test_mejor_publicado_fuera_de_ventana_temporal():
    pub = _pub("2026-01-01 00:00:00", -33.0, -71.0)
    assert a._mejor_publicado([pub], _ag("2026-01-01 00:00:07", -33.0, -71.0)) is None


def test_mejor_publicado_fuera_de_tolerancia_espacial():
    pub = _pub("2026-01-01 00:00:00", -33.0, -71.0)
    assert a._mejor_publicado([pub], _ag("2026-01-01 00:00:00", -34.0, -71.0)) is None
    assert a._mejor_publicado([pub], _ag("2026-01-01 00:00:00", -33.0, -72.0)) is None


def test_mejor_publicado_asocia_dispersion_evento_pacifico_sur():
    pub = _pub("2026-10-10 21:33:58", -37.21, -95.62, mag="5.1")
    agencias = [
        ("EMSC", "2026-10-10 21:34:01", -37.079, -95.381),
        ("USGS", "2026-10-10 21:34:02", -37.117, -95.267),
        ("GFZ", "2026-10-10 21:34:02", -37.071, -95.204),
    ]
    for agencia, fecha, lat, lon in agencias:
        assert a._mejor_publicado(
            [pub], _ag(fecha, lat, lon, agencia=agencia)) is pub


def test_mejor_publicado_elige_menor_dt():
    lejano = _pub("2026-01-01 00:00:00", -33.0, -71.0)
    cercano = _pub("2026-01-01 00:00:05", -33.0, -71.0)
    mejor = a._mejor_publicado([lejano, cercano],
                               _ag("2026-01-01 00:00:04", -33.0, -71.0))
    assert mejor is cercano


def test_mejor_publicado_datos_incompletos():
    pub = _pub("2026-01-01 00:00:00", -33.0, -71.0)
    assert a._mejor_publicado([pub], {"fecha hora": "", "latitud": "-33", "longitud": "-71"}) is None
    assert a._mejor_publicado([pub], {"fecha hora": "2026-01-01 00:00:00", "latitud": "", "longitud": "-71"}) is None


# --------------------------------------------------------------------------
# _deltas
# --------------------------------------------------------------------------
def test_deltas_completos():
    pub = _pub("2026-01-01 00:00:00", 0.0, 0.0, prof="30.0", mag="5.0")
    d = a._deltas(pub, _ag("2026-01-01 00:00:05", 0.0, 1.0, prof="35.0", mag="5.6"))
    assert d["dt_seg"] == 5.0
    assert d["dist_km"] == pytest.approx(111.2, abs=0.2)
    assert d["dprof"] == 5.0
    assert d["dmag"] == 0.6


def test_deltas_datos_faltantes():
    pub = _pub("2026-01-01 00:00:00", 0.0, 0.0, prof="", mag="")
    d = a._deltas(pub, {"fecha hora": "", "latitud": "", "longitud": "",
                        "prof": "", "magnitud": ""})
    assert d["dt_seg"] is None
    assert d["dist_km"] is None
    assert d["dprof"] is None
    assert d["dmag"] is None


# --------------------------------------------------------------------------
# _flags
# --------------------------------------------------------------------------
def test_flags():
    assert a._flags({"dt_seg": 5.0, "dmag": None}) == "time-"
    assert a._flags({"dt_seg": 1.0, "dmag": 0.5}) == "mag-"
    assert a._flags({"dt_seg": 5.0, "dmag": 0.5}) == "time-mag-"
    assert a._flags({"dt_seg": None, "dmag": None}) == ""
    # En el límite no se marca (se exige > 3 y > 0.2).
    assert a._flags({"dt_seg": 3.0, "dmag": 0.2}) == ""


# --------------------------------------------------------------------------
# _asociar_entre_agencias
# --------------------------------------------------------------------------
def test_asociar_agrupa_agencias_distintas():
    eventos = [
        _ag("2026-01-01 00:00:00", -33.0, -71.0, agencia="EMSC"),
        _ag("2026-01-01 00:00:03", -33.0, -71.0, agencia="USGS"),
    ]
    grupos = a._asociar_entre_agencias(eventos)
    assert len(grupos) == 1
    assert len(grupos[0]) == 2


def test_asociar_no_agrupa_la_misma_agencia():
    eventos = [
        _ag("2026-01-01 00:00:00", -33.0, -71.0, agencia="EMSC"),
        _ag("2026-01-01 00:00:03", -33.0, -71.0, agencia="EMSC"),
    ]
    grupos = a._asociar_entre_agencias(eventos)
    assert len(grupos) == 2


def test_asociar_separa_por_dia_y_distancia():
    eventos = [
        _ag("2026-01-01 00:00:00", -33.0, -71.0, agencia="EMSC"),
        _ag("2026-01-02 00:00:00", -33.0, -71.0, agencia="USGS"),
        _ag("2026-01-01 00:00:00", -50.0, -71.0, agencia="GFZ"),
    ]
    grupos = a._asociar_entre_agencias(eventos)
    assert len(grupos) == 3


# --------------------------------------------------------------------------
# _max_distancia
# --------------------------------------------------------------------------
def test_max_distancia_grupo_de_dos():
    grupo = [_ag("2026-01-01 00:00:00", 0.0, 0.0),
             _ag("2026-01-01 00:00:00", 0.0, 1.0)]
    assert a._max_distancia(grupo) == pytest.approx(111.2, abs=0.2)


def test_max_distancia_grupo_de_uno():
    assert a._max_distancia([_ag("2026-01-01 00:00:00", 0.0, 0.0)]) == ""


# --------------------------------------------------------------------------
# _texto_agencias
# --------------------------------------------------------------------------
def test_texto_agencias_misma_ubicacion():
    sols = [
        {"agencia": "EMSC", "latitud": "1.0", "longitud": "2.0"},
        {"agencia": "USGS", "latitud": "1.0", "longitud": "2.0"},
    ]
    assert a._texto_agencias(sols) == "EMSC≡USGS"


def test_texto_agencias_ubicaciones_distintas():
    sols = [
        {"agencia": "EMSC", "latitud": "1.0", "longitud": "2.0"},
        {"agencia": "USGS", "latitud": "1.0", "longitud": "2.5"},
    ]
    assert a._texto_agencias(sols) == "EMSC + USGS"


def test_texto_agencias_sin_agencia_es_csn():
    sols = [{"latitud": "1.0", "longitud": "2.0"}]
    assert a._texto_agencias(sols) == "CSN"


def test_texto_agencias_sin_coordenadas():
    sols = [
        {"agencia": "EMSC", "latitud": "", "longitud": ""},
        {"agencia": "USGS", "latitud": "", "longitud": ""},
    ]
    assert a._texto_agencias(sols) == "EMSC + USGS"
