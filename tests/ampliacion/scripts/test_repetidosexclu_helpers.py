#!/usr/bin/env python3
"""
Tests de repetidosexclu.py
==========================
Cubre el ayudante puro `_parsear_fecha_hora` y `detecta_excluidos`, que escribe
su informe en el archivo abierto que recibe (aquí un `io.StringIO`). La corrida
completa se valida con el golden del arnés (`golden/repetidosexclu.txt`).
"""

import io

import pytest

import repetidosexclu

MAX_SEG = 6


# --------------------------------------------------------------------------
# _parsear_fecha_hora
# --------------------------------------------------------------------------
def test_parsea_dos_espacios():
    assert repetidosexclu._parsear_fecha_hora("2020-01-01  12:34:56") == \
        repetidosexclu.datetime.datetime(2020, 1, 1, 12, 34, 56)


def test_parsea_un_espacio():
    assert repetidosexclu._parsear_fecha_hora("2020-01-01 00:00:00").year == 2020


def test_parsea_segundo_60():
    # El módulo conserva la variante vieja ([0:18]+'59'), que asume el formato
    # de dos espacios de _FORMATO.
    assert repetidosexclu._parsear_fecha_hora("2020-01-01  00:00:60") == \
        repetidosexclu.datetime.datetime(2020, 1, 1, 0, 0, 59)


def test_parsea_invalida_revienta():
    with pytest.raises(ValueError):
        repetidosexclu._parsear_fecha_hora("no es fecha")


# --------------------------------------------------------------------------
# detecta_excluidos
# --------------------------------------------------------------------------
def _sismo(fecha, analista):
    return {
        "fecha_hora": fecha,
        "dt": repetidosexclu._parsear_fecha_hora(fecha),
        "analista": analista,
    }


def test_un_cruce_escribe_una_linea():
    excluidos = [_sismo("2020-01-01 00:00:00", "ana")]
    select = [_sismo("2020-01-01 00:00:02", "jere")]
    archivo = io.StringIO()

    total = repetidosexclu.detecta_excluidos(excluidos, select, MAX_SEG, archivo)

    assert total == 1
    assert archivo.getvalue() == "2020-01-01 00:00:00\tana\n"


def test_cruce_multiple_cuenta_por_par():
    # Un excluido que cruza con tres del select suma tres, no uno.
    excluidos = [_sismo("2020-01-01 00:00:00", "ana")]
    select = [
        _sismo("2020-01-01 00:00:01", "jere"),
        _sismo("2020-01-01 00:00:02", "jere"),
        _sismo("2020-01-01 00:00:05", "ana"),
    ]
    archivo = io.StringIO()

    total = repetidosexclu.detecta_excluidos(excluidos, select, MAX_SEG, archivo)

    assert total == 3
    assert archivo.getvalue().splitlines() == ["2020-01-01 00:00:00\tana"] * 3


def test_ventana_de_tiempo():
    # 6 s entra justo; 7 s queda afuera.
    select = [_sismo("2020-01-01 00:00:06", "jere")]
    assert repetidosexclu.detecta_excluidos(
        [_sismo("2020-01-01 00:00:00", "ana")], select, MAX_SEG,
        io.StringIO()) == 1
    assert repetidosexclu.detecta_excluidos(
        [_sismo("2020-01-01 00:00:00", "ana")],
        [_sismo("2020-01-01 00:00:07", "jere")], MAX_SEG, io.StringIO()) == 0


def test_distinto_dia_no_cruza():
    archivo = io.StringIO()
    total = repetidosexclu.detecta_excluidos(
        [_sismo("2020-01-01 00:00:00", "ana")],
        [_sismo("2020-01-02 00:00:00", "jere")], MAX_SEG, archivo)
    assert total == 0
    assert archivo.getvalue() == ""


def test_lista_select_vacia_no_cruza():
    archivo = io.StringIO()
    total = repetidosexclu.detecta_excluidos(
        [_sismo("2020-01-01 00:00:00", "ana")], [], MAX_SEG, archivo)
    assert total == 0
    assert archivo.getvalue() == ""
