#!/usr/bin/env python3
"""
Tests de repetidos.py
=====================
Cubre los ayudantes puros (`_normalizar_fecha_hora`, `_parsear_fecha_hora`) y
`detecta_repetidos`, que escribe su informe vía `rutas.p_informes` (por eso usa
la fixture `cwd_tmp`). La corrida completa se valida con los goldens del arnés.
"""

import os

import pytest

import repetidos

CABECERA = "fecha hora latitud longitud prof mag tipomag analista\n"


# --------------------------------------------------------------------------
# _normalizar_fecha_hora
# --------------------------------------------------------------------------
def test_normaliza_z_y_t():
    assert repetidos._normalizar_fecha_hora("2020-01-01T00:00:00Z") == \
        "2020-01-01 00:00:00"


def test_normaliza_microsegundos():
    assert repetidos._normalizar_fecha_hora("2020-01-01 00:00:00.123") == \
        "2020-01-01 00:00:00"


def test_normaliza_recorta_espacios():
    assert repetidos._normalizar_fecha_hora("  2020-01-01 00:00:00  ") == \
        "2020-01-01 00:00:00"


@pytest.mark.parametrize("valor", [None, ""])
def test_normaliza_vacio(valor):
    assert repetidos._normalizar_fecha_hora(valor) == ""


# --------------------------------------------------------------------------
# _parsear_fecha_hora
# --------------------------------------------------------------------------
def test_parsea_un_espacio():
    assert repetidos._parsear_fecha_hora("2020-01-01 00:00:00").year == 2020


def test_parsea_dos_espacios():
    assert repetidos._parsear_fecha_hora("2020-01-01  12:34:56").hour == 12


def test_parsea_segundo_60():
    assert repetidos._parsear_fecha_hora("2020-01-01 00:00:60").second == 59


def test_parsea_invalida_revienta():
    with pytest.raises(ValueError):
        repetidos._parsear_fecha_hora("no es fecha")


# --------------------------------------------------------------------------
# detecta_repetidos
# --------------------------------------------------------------------------
def _sismo(fecha, lat, lon, analista="ana"):
    return {
        "fecha_hora": fecha,
        "dt": repetidos._parsear_fecha_hora(fecha),
        "lat": lat,
        "lon": lon,
        "prof": "10.0",
        "mag": "3.0",
        "tipo_mag": "ML",
        "analista": analista,
    }


def _lineas(cwd, nombre):
    with open(os.path.join(str(cwd), "informes", nombre)) as f:
        return f.read().splitlines()


def test_detecta_par_repetido(cwd_tmp):
    lista = [
        _sismo("2020-01-01 00:00:00", "-30.000", "-71.000"),
        _sismo("2020-01-01 00:00:01", "-30.000", "-71.000"),
        _sismo("2020-01-02 00:00:00", "-40.000", "-73.000"),
    ]
    total = repetidos.detecta_repetidos(lista, 6, 2.0, 2.0, "rep_test.txt",
                                        CABECERA, repetidos.campos_seisan)
    assert total == 2
    lineas = _lineas(cwd_tmp, "rep_test.txt")
    assert lineas[0] == CABECERA.rstrip("\n")
    assert len(lineas) == 3  # encabezado + 2 repetidos


def test_evento_solo_no_es_repetido(cwd_tmp):
    lista = [_sismo("2020-01-01 00:00:00", "-30.000", "-71.000")]
    total = repetidos.detecta_repetidos(lista, 6, 2.0, 2.0, "rep_test.txt",
                                        CABECERA, repetidos.campos_seisan)
    assert total == 0
    assert len(_lineas(cwd_tmp, "rep_test.txt")) == 1  # solo encabezado


def test_ventana_de_tiempo(cwd_tmp):
    # 5 s de diferencia: repetido con el filtro amplio (6 s), no con el estricto.
    lista = [
        _sismo("2020-01-01 00:00:00", "-30.000", "-71.000"),
        _sismo("2020-01-01 00:00:05", "-30.000", "-71.000"),
    ]
    assert repetidos.detecta_repetidos(lista, 6, 2.0, 2.0, "amplio.txt",
                                       CABECERA, repetidos.campos_seisan) == 2
    assert repetidos.detecta_repetidos(lista, 3, 2.0, 2.0, "estricto.txt",
                                       CABECERA, repetidos.campos_seisan) == 0


def test_ventana_de_coordenadas(cwd_tmp):
    # Misma hora, 1.5° de latitud: repetido con max_lat 2.0, no con 1.0.
    lista = [
        _sismo("2020-01-01 00:00:00", "-30.000", "-71.000"),
        _sismo("2020-01-01 00:00:00", "-31.500", "-71.000"),
    ]
    assert repetidos.detecta_repetidos(lista, 6, 2.0, 2.0, "amplio.txt",
                                       CABECERA, repetidos.campos_seisan) == 2
    assert repetidos.detecta_repetidos(lista, 6, 1.0, 1.0, "estricto.txt",
                                       CABECERA, repetidos.campos_seisan) == 0
