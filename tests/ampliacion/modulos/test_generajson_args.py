#!/usr/bin/env python3
"""
Tests de generajson.py — parseo de argumentos
=============================================
Cubre `parsear_extra_args`, que traduce los flags --clave=valor de la línea de
comandos a la tupla que consumen `procesar_csv` y `procesar_pares`.
"""

import generajson


def test_sin_flags_todo_none():
    assert generajson.parsear_extra_args([]) == (None,) * 7


def test_cada_flag_por_separado():
    umbral, k, perp, margen, salida, pares, agencia = generajson.parsear_extra_args(
        ["--umbral=50", "--k=2", "--umbral-perp=10", "--margen-borde=5",
         "--salida=mi_vista", "--pares=seisan", "--agencia=EMSC"])
    assert umbral == 50.0
    assert k == 2.0
    assert perp == 10.0
    assert margen == 5.0
    assert salida == "mi_vista"
    assert pares == "seisan"
    assert agencia == "EMSC"


def test_floats_con_decimales():
    umbral, k, perp, margen, _, _, _ = generajson.parsear_extra_args(
        ["--umbral=12.5", "--k=0.75", "--umbral-perp=3.25",
         "--margen-borde=1.5"])
    assert umbral == 12.5
    assert k == 0.75
    assert perp == 3.25
    assert margen == 1.5


def test_salida_con_igual_en_el_valor():
    # split("=", 1) conserva el resto del valor.
    _, _, _, _, salida, _, _ = generajson.parsear_extra_args(["--salida=a=b=c"])
    assert salida == "a=b=c"


def test_args_desconocidos_se_ignoran():
    umbral, _, _, _, _, _, _ = generajson.parsear_extra_args(
        ["archivo.csv", "seisan", "--otro=1", "--umbral=30", "-x"])
    assert umbral == 30.0


def test_orden_no_importa_ni_repite():
    # El último gana cuando el flag se repite.
    umbral = generajson.parsear_extra_args(["--umbral=10", "--umbral=20"])[0]
    assert umbral == 20.0
