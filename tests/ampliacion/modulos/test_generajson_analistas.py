#!/usr/bin/env python3
"""
Tests de generajson.py — analistas y textos de cruce
====================================================
Cubre `_analistas_para_evento` (inferencia de analista por cruce contra la
atribución de SeisComp/Seisan) y los dos formateadores de texto que usa el CSV
de sospechosos: `_texto_posibles_analistas` y `_texto_calidad_cruce`.
"""

from generajson import (_analistas_para_evento, _texto_calidad_cruce,
                        _texto_posibles_analistas)

FECHA = "2020-01-01 00:00:00"


def _entrada(fuente, analista, dt, lat, lon):
    return {"fuente": fuente, "analista": analista, "dt_seg": dt,
            "lat_eventquery": lat, "lon_eventquery": lon}


# --------------------------------------------------------------------------
# _analistas_para_evento
# --------------------------------------------------------------------------
def test_indice_vacio_o_none():
    assert _analistas_para_evento(None, FECHA, -30.0, -71.0) is None
    assert _analistas_para_evento({}, FECHA, -30.0, -71.0) is None


def test_fecha_ausente():
    indice = {"otra": [_entrada("seisan", "jere", "3.0", "-30", "-71")]}
    assert _analistas_para_evento(indice, FECHA, -30.0, -71.0) is None


def test_una_sola_candidata():
    indice = {FECHA: [_entrada("seisan", "jere", "3.0", "-30", "-71")]}
    res = _analistas_para_evento(indice, FECHA, -30.0, -71.0)
    assert len(res) == 1
    assert res[0]["fuente"] == "seisan"
    assert res[0]["n_soluciones"] == 1
    assert res[0]["dt_seg"] == 3.0
    assert res[0]["km"] == 0.0
    assert res[0]["analistas"] == ["jere"]


def test_ordena_seiscomp_antes_que_seisan():
    indice = {FECHA: [
        _entrada("seisan", "jere", "3.0", "-30", "-71"),
        _entrada("seiscomp", "cris", "1.0", "-30", "-71"),
    ]}
    res = _analistas_para_evento(indice, FECHA, -30.0, -71.0)
    assert [e["fuente"] for e in res] == ["seiscomp", "seisan"]


def test_descarta_candidata_lejana_en_el_mismo_segundo():
    # Dos eventos en el mismo segundo: el lejano (1° de lat) se descarta.
    indice = {FECHA: [
        _entrada("seisan", "jere", "3.0", "-30", "-71"),
        _entrada("seiscomp", "cris", "1.0", "-29", "-71"),
    ]}
    res = _analistas_para_evento(indice, FECHA, -30.0, -71.0)
    assert len(res) == 1
    assert res[0]["fuente"] == "seisan"


def test_sin_candidata_cercana_conserva_todas():
    # Si ninguna candidata está cerca, no hay con qué desambiguar y se
    # conservan todas: el filtro solo recorta cuando hay una cercana.
    indice = {FECHA: [
        _entrada("seisan", "jere", "3.0", "-20", "-71"),
        _entrada("seiscomp", "cris", "1.0", "-19", "-71"),
    ]}
    res = _analistas_para_evento(indice, FECHA, -30.0, -71.0)
    assert [e["fuente"] for e in res] == ["seiscomp", "seisan"]


def test_analista_sin_nombre():
    indice = {FECHA: [_entrada("seisan", None, "3.0", "-30", "-71")]}
    res = _analistas_para_evento(indice, FECHA, -30.0, -71.0)
    assert res[0]["analistas"] == ["(sin nombre)"]


def test_dt_invalido_no_rompe():
    indice = {FECHA: [_entrada("seisan", "jere", "no_es_numero", "-30", "-71")]}
    res = _analistas_para_evento(indice, FECHA, -30.0, -71.0)
    assert res[0]["dt_seg"] is None
    assert res[0]["km"] is None


def test_mejor_cruce_de_la_misma_fuente():
    # Dos entradas de seisan: gana el menor dt y se cuentan las soluciones.
    indice = {FECHA: [
        _entrada("seisan", "jere", "5.0", "-30", "-71"),
        _entrada("seisan", "ana", "1.0", "-30", "-71"),
    ]}
    res = _analistas_para_evento(indice, FECHA, -30.0, -71.0)
    assert len(res) == 1
    assert res[0]["n_soluciones"] == 2
    assert res[0]["dt_seg"] == 1.0
    assert res[0]["analistas"] == ["ana", "jere"]  # ordenados


# --------------------------------------------------------------------------
# _texto_posibles_analistas
# --------------------------------------------------------------------------
def test_texto_posibles_analistas_con_inferencia():
    ev = {"analistas": [
        {"fuente": "seiscomp", "analistas": ["cris"]},
        {"fuente": "seisan", "analistas": ["jere", "ana"]},
    ]}
    assert _texto_posibles_analistas(ev) == "seiscomp: cris; seisan: jere, ana"


def test_texto_posibles_analistas_cae_al_analista_propio():
    assert _texto_posibles_analistas({"analista": "juan"}) == "juan"
    assert _texto_posibles_analistas({}) == ""


# --------------------------------------------------------------------------
# _texto_calidad_cruce
# --------------------------------------------------------------------------
def test_calidad_cruce_basico():
    ev = {"analistas": [
        {"fuente": "seiscomp", "dt_seg": 0.2, "km": 3.0, "n_soluciones": 1},
    ]}
    assert _texto_calidad_cruce(ev) == "seiscomp dt 0.2s 3.0km"


def test_calidad_cruce_marca_varias_soluciones():
    ev = {"analistas": [
        {"fuente": "seiscomp", "dt_seg": 0.2, "km": 3.0, "n_soluciones": 3},
    ]}
    assert _texto_calidad_cruce(ev) == "seiscomp dt 0.2s 3.0km (3 soluciones)"


def test_calidad_cruce_sin_km():
    ev = {"analistas": [
        {"fuente": "seisan", "dt_seg": 1.5, "km": None, "n_soluciones": 1},
    ]}
    assert _texto_calidad_cruce(ev) == "seisan dt 1.5s"


def test_calidad_cruce_sin_dt_se_omite():
    ev = {"analistas": [
        {"fuente": "seisan", "dt_seg": None, "km": 3.0, "n_soluciones": 1},
    ]}
    assert _texto_calidad_cruce(ev) == ""
    assert _texto_calidad_cruce({}) == ""


def test_calidad_cruce_varias_fuentes():
    ev = {"analistas": [
        {"fuente": "seiscomp", "dt_seg": 0.2, "km": 3.0, "n_soluciones": 1},
        {"fuente": "seisan", "dt_seg": 4.0, "km": 12.0, "n_soluciones": 1},
    ]}
    assert _texto_calidad_cruce(ev) == "seiscomp dt 0.2s 3.0km; seisan dt 4.0s 12.0km"
