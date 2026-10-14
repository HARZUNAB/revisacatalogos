#!/usr/bin/env python3
"""
Tests de compara.py — funciones puras
=====================================
Cubre los ayudantes puros de `compara.py` (`_parsear_fecha_hora`, `_magnitud`,
`_borrar`) que quedan accesibles una vez que el script deja de ejecutarse al
importarse. La lógica completa de `comparar` se valida con el golden del arnés
(`arnes_refactor.py`).
"""

import datetime

import pytest


# --------------------------------------------------------------------------
# _parsear_fecha_hora
# --------------------------------------------------------------------------
def test_fecha_un_espacio(compara):
    assert compara._parsear_fecha_hora("2020-01-01 00:00:00") == \
        datetime.datetime(2020, 1, 1, 0, 0, 0)


def test_fecha_dos_espacios(compara):
    assert compara._parsear_fecha_hora("2020-01-01  12:34:56") == \
        datetime.datetime(2020, 1, 1, 12, 34, 56)


def test_normaliza_el_segundo_60(compara):
    # eventquery llega con segundos inválidos; 60 se lleva a 59.
    assert compara._parsear_fecha_hora("2020-01-01 00:00:60") == \
        datetime.datetime(2020, 1, 1, 0, 0, 59)


def test_fecha_invalida_revienta(compara):
    with pytest.raises(ValueError):
        compara._parsear_fecha_hora("no es una fecha")


# --------------------------------------------------------------------------
# _magnitud
# --------------------------------------------------------------------------
def test_magnitud_numerica(compara):
    assert compara._magnitud("4.5") == 4.5
    assert compara._magnitud(" 3.0 ") == 3.0


@pytest.mark.parametrize("valor", ["", "   ", None, "abc", "M4.5"])
def test_magnitud_sin_dato_o_invalida(compara, valor):
    assert compara._magnitud(valor) is None


# --------------------------------------------------------------------------
# _borrar
# --------------------------------------------------------------------------
def test_borrar_archivo_existente(compara, tmp_path):
    f = tmp_path / "x.csv"
    f.write_text("hola")
    compara._borrar(str(f))
    assert not f.exists()


def test_borrar_inexistente_no_revienta(compara, tmp_path):
    compara._borrar(str(tmp_path / "no_existe.csv"))  # no debe levantar
