#!/usr/bin/env python3
"""
Tests de revisaexcluidos.py
===========================
Cubre los ayudantes puros extraidos de `revisaexcluidos.py`. La corrida
completa (normalizacion de `informes/excluidos.txt` a `datos/excluidos.csv`) se
valida con el golden del arnes (`golden/revisaexcluidos.txt`), que corre el
script sin argumentos con un `informes/excluidos.txt` en el temporal.
"""


def test_agregar_ceros_separa_ddmm(revisaexcluidos):
    assert revisaexcluidos._agregar_ceros_excluido(
        "2026 1002 1247 29.0L -23.826 -67.266219.7 3.9L 1 TASK \n"
    ) == "2026 10 02 1247 29.0L -23.826 -67.266219.7 3.9L 1 TASK "


def test_agregar_ceros_rellena_a_dos_digitos(revisaexcluidos):
    assert revisaexcluidos._agregar_ceros_excluido(
        "2026 1 2 9 5 -23.8 -67.2 3.9L 1 TASK\n"
    ) == "2026 01 02 0905 -23.8 -67.2 3.9L 1 TASK "


def test_hora_valida(revisaexcluidos):
    assert revisaexcluidos._hora_invalida(
        "2026 1002 1247 29.0L -23.8 -67.2 3.9L 1 TASK\n") is False


def test_hora_invalida(revisaexcluidos):
    assert revisaexcluidos._hora_invalida(
        "2026 1002 2400 29.0L -23.8 -67.2 3.9L 1 TASK\n") is True


def test_fecha_hora(revisaexcluidos):
    sismo = "2026 10 02 1247 29.0L -23.826 -67.266219.7 3.9L 1 TASK".split()
    assert revisaexcluidos._fecha_hora_desde_excluido(sismo) == \
        "2026-10-02  12:47:29"


def test_fecha_hora_segundos_menores_a_diez(revisaexcluidos):
    sismo = "2026 10 05 0825 2.0L -24.212 -68.868112.2 3.8L 1 TASK".split()
    assert revisaexcluidos._fecha_hora_desde_excluido(sismo) == \
        "2026-10-05  08:25:02"
