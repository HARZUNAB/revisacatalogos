#!/usr/bin/env python3
"""
Tests de consultaapi.py — consulta por cuadrante
===============================================
Cubre `_emsc_cuadrante`, `_usgs_cuadrante` y `_gfz_cuadrante` (y el aviso de
`_guardar` sin filas) con un `requests.get` falso: se verifica el parseo de la
respuesta, los casos de "sin datos" y el manejo de errores. Nunca se toca la
red real ni pandas.
"""

import pytest

pytestmark = pytest.mark.red


class _Respuesta:
    """Respuesta HTTP falsa con lo justo que consultan los cuadrantes."""

    def __init__(self, *, json_data=None, text="", status_code=200, error=None):
        self._json = json_data
        self.text = text
        self.status_code = status_code
        self._error = error

    def raise_for_status(self):
        if self._error is not None:
            raise self._error

    def json(self):
        return self._json


class _Get:
    """Reemplazo de `requests.get` que devuelve siempre la misma respuesta."""

    def __init__(self, respuesta):
        self.respuesta = respuesta
        self.llamadas = []

    def __call__(self, url, params=None, timeout=None):
        self.llamadas.append({"url": url, "params": params, "timeout": timeout})
        return self.respuesta


@pytest.fixture
def cuadrante(consultaapi):
    return consultaapi.CUADRANTES_CHILE[0]


def _con_get(monkeypatch, consultaapi, respuesta):
    get = _Get(respuesta)
    monkeypatch.setattr(consultaapi.requests, "get", get)
    return get


# --------------------------------------------------------------------------
# EMSC
# --------------------------------------------------------------------------
def test_emsc_parsea_evento(monkeypatch, consultaapi, cuadrante):
    respuesta = _Respuesta(text="{}", json_data={"features": [
        {"properties": {"time": "2020-01-01T00:00:00.000Z", "lat": -30.0,
                        "lon": -71.0, "depth": 50.0, "mag": 4.5,
                        "magtype": "ML", "flynn_region": "CHILE",
                        "auth": "EMSC"}},
    ]})
    get = _con_get(monkeypatch, consultaapi, respuesta)

    filas = consultaapi._emsc_cuadrante(cuadrante, "2020-01-01", "2020-01-02", 3.0)

    assert filas == [("2020-01-01 00:00:00", -30.0, -71.0, 50.0, 4.5,
                      "ML", "CHILE", "EMSC")]
    assert get.llamadas[0]["params"]["format"] == "json"


def test_emsc_204_devuelve_vacio(monkeypatch, consultaapi, cuadrante):
    _con_get(monkeypatch, consultaapi, _Respuesta(status_code=204))
    assert consultaapi._emsc_cuadrante(cuadrante, "a", "b", 3.0) == []


def test_emsc_html_no_es_dato(monkeypatch, consultaapi, cuadrante, capsys):
    _con_get(monkeypatch, consultaapi, _Respuesta(text="<html>error</html>"))
    assert consultaapi._emsc_cuadrante(cuadrante, "a", "b", 3.0) == []
    assert "no son datos" in capsys.readouterr().out


def test_emsc_error_de_red_lo_atrapa(monkeypatch, consultaapi, cuadrante, capsys):
    _con_get(monkeypatch, consultaapi,
             _Respuesta(error=RuntimeError("boom")))
    assert consultaapi._emsc_cuadrante(cuadrante, "a", "b", 3.0) == []
    assert "error en la solicitud" in capsys.readouterr().out


def test_emsc_descarta_evento_sin_coordenadas(monkeypatch, consultaapi, cuadrante):
    respuesta = _Respuesta(text="{}", json_data={"features": [
        {"properties": {"time": "2020-01-01T00:00:00.000Z", "lat": None,
                        "lon": -71.0, "mag": 4.5}},
        {"properties": {"time": "2020-01-01T00:00:00.000Z", "lat": -30.0,
                        "lon": -71.0, "mag": 4.5, "magtype": "ML"}},
    ]})
    _con_get(monkeypatch, consultaapi, respuesta)
    filas = consultaapi._emsc_cuadrante(cuadrante, "a", "b", 3.0)
    assert len(filas) == 1


# --------------------------------------------------------------------------
# USGS
# --------------------------------------------------------------------------
def test_usgs_parsea_evento(monkeypatch, consultaapi, cuadrante):
    respuesta = _Respuesta(json_data={"features": [
        {"properties": {"time": 1577836800000, "mag": 4.5, "magType": "Mww",
                        "place": "CHILE", "auth": "NEIC"},
         "geometry": {"coordinates": [-71.0, -30.0, 50.0]}},
    ]})
    get = _con_get(monkeypatch, consultaapi, respuesta)

    filas = consultaapi._usgs_cuadrante(cuadrante, "2020-01-01T00:00:00",
                                        "2020-01-02T00:00:00", 3.0)

    assert filas == [("2020-01-01 00:00:00", -30.0, -71.0, 50.0, 4.5,
                      "Mww", "CHILE", "NEIC")]
    assert get.llamadas[0]["params"]["format"] == "geojson"


def test_usgs_descarta_coordenadas_incompletas(monkeypatch, consultaapi, cuadrante):
    respuesta = _Respuesta(json_data={"features": [
        {"properties": {"time": 1577836800000, "mag": 4.5},
         "geometry": {"coordinates": [-71.0, -30.0]}},  # faltan la prof.
        {"properties": {"time": 1577836800000, "mag": 4.5},
         "geometry": {"coordinates": [None, -30.0, 50.0]}},
    ]})
    _con_get(monkeypatch, consultaapi, respuesta)
    assert consultaapi._usgs_cuadrante(cuadrante, "a", "b", 3.0) == []


# --------------------------------------------------------------------------
# GFZ (solo las ramas previas a pandas)
# --------------------------------------------------------------------------
def test_gfz_texto_vacio(monkeypatch, consultaapi, cuadrante):
    get = _con_get(monkeypatch, consultaapi, _Respuesta(text="   "))
    assert consultaapi._gfz_cuadrante(cuadrante, "2020-01-01", "2020-01-02", 3.0) == []
    assert get.llamadas[0]["params"]["format"] == "text"


def test_gfz_solo_comentarios(monkeypatch, consultaapi, cuadrante):
    _con_get(monkeypatch, consultaapi, _Respuesta(text="# solo\n# comentarios\n"))
    assert consultaapi._gfz_cuadrante(cuadrante, "a", "b", 3.0) == []


def test_gfz_prepara_csv_sin_perder_el_primer_evento(consultaapi):
    texto = (
        "#EventID|Time|Latitude|Longitude|Depth/km|Author|Catalog|"
        "Contributor|ContributorID|MagType|Magnitude|MagAuthor|"
        "EventLocationName|EventType\n"
        "gfz1|2026-10-10T21:34:02.36|-37.071|-95.204|10.0|||GFZ|gfz1|"
        "Mw|5.27||Southeast of Easter Island|earthquake\n"
        "gfz2|2026-10-10T21:59:00.00|-24.4|-69.2|78.0|||GFZ|gfz2|"
        "mb|4.0||Chile|earthquake\n")

    preparado = consultaapi._texto_gfz_para_csv(texto)

    assert preparado is not None
    lineas = preparado.splitlines()
    assert lineas[0].startswith("EventID|Time|")
    assert lineas[1].startswith("gfz1|")
    assert lineas[2].startswith("gfz2|")
    assert len(lineas) == 3


# --------------------------------------------------------------------------
# _guardar sin filas
# --------------------------------------------------------------------------
def test_guardar_sin_filas_no_escribe(consultaapi, cwd_tmp, capsys):
    consultaapi._guardar([], "EMSC", "consultaapi_EMSC.csv")
    assert "No se encontraron eventos" in capsys.readouterr().out
    assert not (cwd_tmp / "datos").exists()


# --------------------------------------------------------------------------
# Constantes
# --------------------------------------------------------------------------
def test_cuadrantes_cubren_chile(consultaapi):
    assert len(consultaapi.CUADRANTES_CHILE) == 3
    for c in consultaapi.CUADRANTES_CHILE:
        assert {"name", "minlat", "maxlat", "minlon", "maxlon"} <= set(c)


def test_cuadrantes_cubren_evento_y_franja_subantartica(consultaapi):
    def nombres(lat, lon):
        return [c["name"] for c in consultaapi.CUADRANTES_CHILE
                if c["minlat"] <= lat <= c["maxlat"]
                and c["minlon"] <= lon <= c["maxlon"]]

    # Evento real del 2026-10-10, al sureste de Isla de Pascua.
    assert "Pacífico Sur Oriental" in nombres(-37.21, -95.62)
    # Rapa Nui queda dentro del mismo cuadrante.
    assert "Pacífico Sur Oriental" in nombres(-27.1, -109.4)
    # La franja -60..-56 queda cubierta por Pacífico y/o Antártico.
    assert "Territorio Antártico Chileno" in nombres(-58.0, -70.0)
    assert "Pacífico Sur Oriental" in nombres(-58.0, -95.0)
    for lon in (-110.0, -100.0, -90.0, -80.0, -70.0, -60.0, -53.0):
        assert nombres(-58.0, lon), lon
