#!/usr/bin/env python3
"""
Tests de generajson.py — distancia aproximada
=============================================
Cubre `_distancia_aprox_km` (fórmula equirectangular): mismo punto, distancias
conocidas, entradas no numéricas y strings numéricos.
"""

import pytest

import generajson


def test_mismo_punto_es_cero():
    assert generajson._distancia_aprox_km(-30.0, -71.0, -30.0, -71.0) == 0.0


def test_un_grado_de_latitud():
    # 1° de latitud ~ 110.57 km según la constante del módulo.
    assert generajson._distancia_aprox_km(0.0, 0.0, 1.0, 0.0) == pytest.approx(
        110.57, abs=0.01)


def test_un_grado_de_longitud_en_el_ecuador():
    # En el ecuador 1° de longitud ~ 111.32 km.
    assert generajson._distancia_aprox_km(0.0, 0.0, 0.0, 1.0) == pytest.approx(
        111.32, abs=0.05)


def test_longitud_encoge_con_la_latitud():
    en_ecuador = generajson._distancia_aprox_km(0.0, 0.0, 0.0, 1.0)
    en_lat_60 = generajson._distancia_aprox_km(60.0, 0.0, 60.0, 1.0)
    assert en_lat_60 < en_ecuador
    assert en_lat_60 == pytest.approx(55.66, abs=0.05)


def test_acepta_strings_numericos():
    assert generajson._distancia_aprox_km("-30", "-71", "-30", "-71") == 0.0


@pytest.mark.parametrize("valor", [None, "x", "no_numerico", object()])
def test_no_numerico_devuelve_none(valor):
    assert generajson._distancia_aprox_km(valor, 0.0, 0.0, 0.0) is None
