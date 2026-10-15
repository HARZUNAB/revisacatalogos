#!/usr/bin/env python3
"""
Tests de bordes de comparacion.py
=================================
Casos borde y combinaciones raras que el test base de `comparacion` no cubre:
valores no finitos, notación científica, la combinación de ignorar_signo con
tolerancia, los extremos de la distancia (antípodas y cruce del meridiano 180)
y el agrupado de `no_actualizados` por el valor numérico de la coordenada.
"""

import math

import pytest

import comparacion as c


# --------------------------------------------------------------------------
# a_numero / formatos con no finitos
# --------------------------------------------------------------------------
def test_a_numero_nan_no_es_none():
    # "nan" se parsea como float('nan'), no cae al None de "no hay dato".
    assert math.isnan(c.a_numero("nan"))


def test_a_numero_inf():
    assert c.a_numero("inf") == float("inf")


def test_formato_coordenada_notacion_cientifica():
    # float() acepta notación científica, así que se formatea con decimales.
    assert c.formato_coordenada("1e3") == "1000.000"


def test_formato_coordenada_nan():
    assert c.formato_coordenada("nan") == "nan"


def test_mismo_numero_nan_nan_es_falso():
    # nan != nan: dos "nan" no se consideran el mismo número.
    assert not c.mismo_numero("nan", "nan", 1)


# --------------------------------------------------------------------------
# mismo_numero: signo + tolerancia combinados
# --------------------------------------------------------------------------
def test_mismo_numero_ignorar_signo_con_tolerancia():
    # La rama de tolerancia corre tras aplicar abs() por ignorar_signo.
    assert c.mismo_numero("-30.000", "30.004", 3, ignorar_signo=True,
                          tolerancia=0.005)
    assert not c.mismo_numero("-30.000", "30.006", 3, ignorar_signo=True,
                              tolerancia=0.005)


# --------------------------------------------------------------------------
# distancia_km: extremos
# --------------------------------------------------------------------------
def test_distancia_km_antipodas():
    # Medio ecuador; ejercita el min(1.0, ...) que evita el dominio de asin.
    assert c.distancia_km("0", "0", "0", "180") == pytest.approx(
        20015.114, abs=0.01)


def test_distancia_km_cruce_del_meridiano_180():
    # 179° a -179° son 2° de longitud, no 358°.
    assert c.distancia_km("0", "179", "0", "-179") == pytest.approx(
        222.390, abs=0.01)


# --------------------------------------------------------------------------
# no_actualizados: agrupado por texto crudo de lat/lon
# --------------------------------------------------------------------------
def _fila(**cambios):
    base = {
        "lat_eventquery": "-33.000", "lon_eventquery": "-71.000",
        "prof_eventquery": "30.0", "mag_eventquery": "5.0",
        "lat_local": "-33.000", "lon_local": "-71.000",
        "prof_local": "30.0", "mag_local": "5.0",
        "fecha_local": "2026-01-01 00:00:00", "dt_seg": "1.0",
        "dist_km": "10.0",
    }
    base.update(cambios)
    return base


def test_no_actualizados_agrupa_por_valor_de_coordenada():
    # Mismo evento local con la lat escrita distinto ("-33.0" vs "-33.00"):
    # la clave agrupa por el número redondeado, así que es un solo resultado.
    filas = [
        _fila(mag_local="5.5", lat_local="-33.0"),
        _fila(mag_local="5.5", lat_local="-33.00"),
    ]
    assert len(c.no_actualizados(filas)) == 1


def test_no_actualizados_dt_no_numerico_conserva_el_primero():
    # Con dt_seg no numérico, _a_float da infinito en ambos: no hay reemplazo
    # y se conserva la primera fila.
    filas = [
        _fila(mag_local="5.5", dt_seg="x"),
        _fila(mag_local="5.5", dt_seg="y"),
    ]
    res = c.no_actualizados(filas)
    assert len(res) == 1
    assert res[0]["dt_seg"] == "x"
