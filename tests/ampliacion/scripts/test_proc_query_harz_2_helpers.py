#!/usr/bin/env python3
"""
Tests de proc_query_harz_2.py
=============================
Cubre el ayudante puro `_parsear_tiempo`. La corrida completa (lectura del CSV,
orden por fecha, .dat y `new_2_*.csv`) se valida con el golden del arnés
(`golden/proc_query_harz_2.txt`), que corre localmente porque necesita pandas.
"""

import datetime

import pytest


# --------------------------------------------------------------------------
# _parsear_tiempo
# --------------------------------------------------------------------------
def test_formato_viejo_z(proc_query_harz_2):
    assert proc_query_harz_2._parsear_tiempo("2026-08-01T01:36:26Z") == \
        datetime.datetime(2026, 8, 1, 1, 36, 26)


def test_formato_nuevo_con_offset(proc_query_harz_2):
    # 2026-09-04 23:58:48 -04:00 equivale a 2026-09-05 03:58:48 UTC.
    assert proc_query_harz_2._parsear_tiempo(
        "2026-09-04 23:58:48.654902-04:00") == \
        datetime.datetime(2026, 9, 5, 3, 58, 48)


def test_sin_zona(proc_query_harz_2):
    assert proc_query_harz_2._parsear_tiempo("2026-07-01 12:00:00") == \
        datetime.datetime(2026, 7, 1, 12, 0, 0)


def test_descarta_microsegundos(proc_query_harz_2):
    fecha = proc_query_harz_2._parsear_tiempo("2026-07-01 12:00:00.999999")
    assert fecha.microsecond == 0


def test_recorta_espacios(proc_query_harz_2):
    assert proc_query_harz_2._parsear_tiempo("  2026-07-01 12:00:00  ") == \
        datetime.datetime(2026, 7, 1, 12, 0, 0)


@pytest.mark.parametrize("valor", [None, "", "no es fecha",
                                   "2026-13-40 00:00:00"])
def test_invalida_revienta(proc_query_harz_2, valor):
    with pytest.raises(ValueError):
        proc_query_harz_2._parsear_tiempo(valor)
