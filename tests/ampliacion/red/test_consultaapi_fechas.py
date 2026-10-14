#!/usr/bin/env python3
"""
Tests de consultaapi.py — limpieza de fechas
============================================
Cubre `_limpia_fecha_emsc` y `_limpia_fecha_usgs`, que normalizan el campo
`time` de cada agencia al formato 'YYYY-MM-DD HH:MM:SS'. Son puras: no tocan
la red ni pandas.
"""

import datetime

import pytest

pytestmark = pytest.mark.red


def test_emsc_con_microsegundos(consultaapi):
    assert consultaapi._limpia_fecha_emsc("2020-01-01T00:00:00.000Z") == \
        "2020-01-01 00:00:00"


def test_emsc_sin_microsegundos(consultaapi):
    assert consultaapi._limpia_fecha_emsc("2020-01-01T00:00:00Z") == \
        "2020-01-01 00:00:00"


def test_emsc_recorta_espacios(consultaapi):
    assert consultaapi._limpia_fecha_emsc("  2020-01-01T12:34:56Z  ") == \
        "2020-01-01 12:34:56"


def test_emsc_invalida_devuelve_none(consultaapi):
    assert consultaapi._limpia_fecha_emsc("no es una fecha") is None
    assert consultaapi._limpia_fecha_emsc(None) is None


def test_usgs_none(consultaapi):
    assert consultaapi._limpia_fecha_usgs(None) is None


def test_usgs_epoch_ms(consultaapi):
    # 1577836800000 ms = 2020-01-01 00:00:00 UTC.
    assert consultaapi._limpia_fecha_usgs(1577836800000) == \
        "2020-01-01 00:00:00"


def test_usgs_epoch_cero(consultaapi):
    esperado = datetime.datetime.fromtimestamp(0, datetime.timezone.utc).strftime(
        "%Y-%m-%d %H:%M:%S")
    assert consultaapi._limpia_fecha_usgs(0) == esperado


def test_usgs_iso_string(consultaapi):
    assert consultaapi._limpia_fecha_usgs("2020-01-01T00:00:00.000Z") == \
        "2020-01-01 00:00:00"


def test_usgs_string_invalido(consultaapi):
    assert consultaapi._limpia_fecha_usgs("nada") is None
