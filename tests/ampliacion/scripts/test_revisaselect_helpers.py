#!/usr/bin/env python3
"""
Tests de revisaselect.py
========================
Cubre el ayudante puro `_normalizar_excluido`, que reacomoda cada linea de
excluidos antes de escribir `informes/excluidos.txt`. La corrida completa
(parseo de `select.out`, separacion validos/excluidos) se valida con el golden
del arnes (`golden/revisaselect.txt`), que corre el script sin argumentos con
un `select.out` en la raiz del temporal.
"""

import revisaselect


def test_linea_tipica():
    assert revisaselect._normalizar_excluido(
        "2020 01 02 1300 50 -31.00 -72.00 GUC CSN 0.5 1 analista\n") == \
        "2020 102 1300 50 -31.00 -72.00 GUC CSN 0.5 1 analista "


def test_linea_sin_coordenadas():
    assert revisaselect._normalizar_excluido(
        "2020 01 04 1500 60 -33.00 GUC LGUC 0.5 1 analista\n") == \
        "2020 104 1500 60 -33.00 GUC LGUC 0.5 1 analista "


def test_campos_de_un_digito_se_rellenan():
    # El pase conserva la logica historica de relleno (y sus rarezas) intacta.
    assert revisaselect._normalizar_excluido(
        "2020 1 2 900 5 -31.0 -72.0 GUC LGUC 0.5 1 ana\n") == \
        "2020 102900 5-31.0 -72.0 GUC LGUC 0.5 1 ana "


def test_solo_analista():
    assert revisaselect._normalizar_excluido("analista\n") == "analista "


def test_linea_vacia():
    assert revisaselect._normalizar_excluido("\n") == ""
