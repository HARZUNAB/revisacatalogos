#!/usr/bin/env python3
"""
Tests de bordes de revisa_seiscomp.py
=====================================
Casos borde de los ayudantes puros que el test base no cubre: el redondeo de la
banda de grado, el `None` buscable, fechas parciales, el desglose sin tramo
"sin usar", plurales de cero, el umbral "cercana", el contacto exacto entre
ventanas, la cobertura "por detrás", extensiones en mayúscula y resúmenes
vacíos.

El módulo no se modifica en esta tanda.
"""

from datetime import datetime

import pytest

import revisa_seiscomp as r


# --------------------------------------------------------------------------
# _banda_numero
# --------------------------------------------------------------------------
def test_banda_numero_redondeo_del_borde():
    # 26.9999 se muestra como 27.000 -> sale de la banda de 26; 26.999 entra.
    assert r._banda_numero("26.9999", "26") is False
    assert r._banda_numero("26.999", "26") is True


def test_banda_numero_token_vacio_o_no_numerico():
    assert r._banda_numero("-26.0", "") is False
    assert r._banda_numero("-26.0", "abc") is False


# --------------------------------------------------------------------------
# _texto_filtrable
# --------------------------------------------------------------------------
def test_texto_filtrable_none_es_buscable():
    # str(None) == "None" y no es VACIO, así que queda en el texto buscable.
    assert r._texto_filtrable([None]) == "none"


# --------------------------------------------------------------------------
# _partir_fecha_hora
# --------------------------------------------------------------------------
def test_partir_fecha_hora_sin_segundos():
    assert r._partir_fecha_hora("2026-09-04 06:48") == ("2026-09-04", "06:48")


def test_partir_fecha_hora_solo_hora():
    assert r._partir_fecha_hora("06:48:08") == ("06:48:08", r.VACIO)


def test_partir_fecha_hora_ignora_el_tercer_token():
    assert r._partir_fecha_hora("2026-09-04 06:48:08 extra") == \
        ("2026-09-04", "06:48:08")


# --------------------------------------------------------------------------
# _desglose_uso / plurales
# --------------------------------------------------------------------------
def test_desglose_uso_sin_no_usadas_omite_el_tramo():
    resumen = {"con_modo": True, "usadas": 2, "no_usadas": 0,
               "usadas_manual": 1, "usadas_auto": 1,
               "sin_usar_manual": 0, "sin_usar_auto": 0}
    assert r._desglose_uso(resumen) == "2 usadas (1 manual, 1 automática)"


def test_plurales_de_cero():
    assert r._n_manual(0) == "0 manuales"
    assert r._n_auto(0) == "0 automáticas"


# --------------------------------------------------------------------------
# _etiqueta_no_picada: umbral inclusivo
# --------------------------------------------------------------------------
def test_etiqueta_no_picada_umbral_inclusivo():
    assert r._etiqueta_no_picada(
        {"distancia_km": "50", "actividad_ventana": "3"}) == "indicio"
    assert r._etiqueta_no_picada(
        {"distancia_km": "50.1", "actividad_ventana": "3"}) == "indicio_lejos"
    assert r._etiqueta_no_picada(
        {"distancia_km": "0", "actividad_ventana": "3"}, umbral_cercano=0) \
        == "indicio"


# --------------------------------------------------------------------------
# _elegir_par / _cobertura
# --------------------------------------------------------------------------
def test_elegir_par_contacto_exacto_no_solapa():
    pares = [{"eventos": "seiscomp_20260801000000_20260901000000.csv"}]
    ventana = (datetime(2026, 9, 1), datetime(2026, 9, 30))
    # El par termina justo cuando empieza la ventana: solape 0 s -> None.
    assert r._elegir_par(pares, ventana) is None


def test_cobertura_fuera_por_detras():
    par = (datetime(2026, 8, 1), datetime(2026, 8, 31))
    cat = (datetime(2026, 9, 1), datetime(2026, 9, 30))
    assert r._cobertura(par, cat) == (datetime(2026, 9, 1),
                                      datetime(2026, 8, 31), 0.0)


# --------------------------------------------------------------------------
# _ventana_del_nombre
# --------------------------------------------------------------------------
def test_ventana_del_nombre_extension_mayuscula():
    assert r._ventana_del_nombre(
        "seiscomp_20260901000000_20260930235959.CSV") is None


# --------------------------------------------------------------------------
# _resumen_fases / _encabezado_estacion vacíos
# --------------------------------------------------------------------------
def test_resumen_fases_vacio():
    resumen = r._resumen_fases([])
    assert resumen["estaciones"] == 0
    assert resumen["sin_magnitud"] == 0
    assert resumen["mag_promedio"] is None


def test_encabezado_estacion_sin_llegadas():
    assert r._encabezado_estacion("IU ABC", []) == "IU ABC   (0 llegadas)"


# --------------------------------------------------------------------------
# _valores_fase / _conteo_modo
# --------------------------------------------------------------------------
def test_valores_fase_no_pega_micro_si_ya_hay_punto():
    fila = {"llegada_utc": "2026-09-04 06:48:08.5", "llegada_us": "999",
            "usada": "no"}
    valores = r._valores_fase(fila)
    assert valores[1] == "2026-09-04 06:48:08.5"
    assert valores[7] == "no"


def test_conteo_modo_normaliza_y_ignora_none():
    assert r._conteo_modo([{"modo_pick": "MANUAL"}, {"modo_pick": None}]) == (1, 0)


# --------------------------------------------------------------------------
# _colores_pick
# --------------------------------------------------------------------------
def test_colores_pick_claro_y_oscuro():
    claro = r._colores_pick(False)
    oscuro = r._colores_pick(True)
    assert claro == {"usada": "#c0392b", "sin_usar": "#b9770e"}
    assert oscuro == {"usada": "#ff8a80", "sin_usar": "#f0c674"}
