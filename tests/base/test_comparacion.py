#!/usr/bin/env python3
"""
Tests de comparacion.py
=======================
El módulo es la fuente única de la comparación numérica de parámetros y de la
regla de «no actualizado». Se cubren todas las ramas de mismo_numero (que es la
base de todo lo demás), los formatos, la distancia haversine y el agrupado de
no_actualizados.
"""

import pytest

import comparacion as c


# --------------------------------------------------------------------------
# a_numero
# --------------------------------------------------------------------------
@pytest.mark.parametrize("entrada, esperado", [
    (None, None),
    ("", None),
    ("   ", None),
    ("3.5", 3.5),
    ("-31.639999999", -31.639999999),
    ("  2 ", 2.0),
    (7, 7.0),
    (7.5, 7.5),
    ("abc", None),
    ("1,5", None),
])
def test_a_numero(entrada, esperado):
    assert c.a_numero(entrada) == esperado


# --------------------------------------------------------------------------
# mismo_numero
# --------------------------------------------------------------------------
def test_mismo_numero_redondea_a_decimales():
    # Distinta cantidad de decimales, mismo valor a 1 decimal.
    assert c.mismo_numero("2.94", "2.9", 1)
    assert c.mismo_numero("-31.64", "-31.639999999", 3)
    assert not c.mismo_numero("2.94", "2.8", 1)


def test_mismo_numero_faltantes():
    # Falta uno -> distintos; faltan los dos -> iguales.
    assert not c.mismo_numero("", "5.0", 1)
    assert not c.mismo_numero("5.0", "", 1)
    assert c.mismo_numero("", "", 1)
    assert c.mismo_numero(None, None, 1)
    assert c.mismo_numero("  ", "", 1)


def test_mismo_numero_no_numerico_compara_texto():
    assert c.mismo_numero("abc", "abc", 1)
    assert not c.mismo_numero("abc", "abd", 1)
    assert not c.mismo_numero("abc", "2.0", 1)


def test_mismo_numero_ignorar_signo():
    assert c.mismo_numero("30.0", "-30.0", 1, ignorar_signo=True)
    assert not c.mismo_numero("30.0", "-30.0", 1)


def test_mismo_numero_tolerancia():
    # Diferencia dentro de la tolerancia -> iguales.
    assert c.mismo_numero("-31.640", "-31.644", 3, tolerancia=0.005)
    # Fuera de la tolerancia -> distintos.
    assert not c.mismo_numero("-31.640", "-31.646", 3, tolerancia=0.005)
    # La tolerancia se compara tras redondear a 'decimales'.
    assert c.mismo_numero("0.0", "0.0049999", 3, tolerancia=0.005)
    # 0.0051 redondea a 3 decimales a 0.005 -> entra en la tolerancia.
    assert c.mismo_numero("0.0", "0.0051", 3, tolerancia=0.005)
    # 0.006 ya supera la tolerancia.
    assert not c.mismo_numero("0.0", "0.006", 3, tolerancia=0.005)


# --------------------------------------------------------------------------
# Comparadores de parámetro
# --------------------------------------------------------------------------
def test_mismo_coordenada_tolera_media_centesima():
    assert c.mismo_coordenada("-33.000", "-33.004")     # dentro de 0.005
    assert not c.mismo_coordenada("-33.000", "-33.006")  # fuera


def test_misma_profundidad_ignora_signo():
    assert c.misma_profundidad("30.0", "-30.0")
    assert c.misma_profundidad("30.04", "30.0")  # 1 decimal
    assert not c.misma_profundidad("30.0", "30.2")


def test_mismo_magnitud():
    assert c.mismo_magnitud("5.04", "5.0")
    assert not c.mismo_magnitud("5.0", "5.2")


# --------------------------------------------------------------------------
# Formatos
# --------------------------------------------------------------------------
@pytest.mark.parametrize("texto, esperado", [
    ("-31.639999999", "-31.640"),
    ("-31.64", "-31.640"),
    ("", ""),
    (None, ""),
    ("abc", "abc"),
])
def test_formato_coordenada(texto, esperado):
    assert c.formato_coordenada(texto) == esperado


def test_formato_profundidad_y_magnitud():
    assert c.formato_profundidad("30.04") == "30.0"
    assert c.formato_profundidad("-30.06") == "-30.1"
    assert c.formato_magnitud("5.06") == "5.1"
    assert c.formato_magnitud("") == ""


# --------------------------------------------------------------------------
# parametros_discrepantes
# --------------------------------------------------------------------------
def _params(lat="1.0", lon="2.0", prof="3.0", mag="4.0"):
    return (lat, lon, prof, mag)


def test_parametros_discrepantes_coinciden():
    assert c.parametros_discrepantes(*_params(), *_params()) == []


def test_parametros_discrepantes_orden_y_simbolos():
    # lat y mag distintos -> ['lat', 'mag'] en ese orden.
    a = _params(lat="1.0", mag="4.0")
    b = _params(lat="1.5", mag="5.0")
    assert c.parametros_discrepantes(*a, *b) == ["lat", "mag"]


def test_parametros_discrepantes_es_simetrica():
    a = _params(lat="1.0", lon="2.0", prof="30.0", mag="4.0")
    b = _params(lat="1.4", lon="2.0", prof="35.0", mag="4.0")
    assert (c.parametros_discrepantes(*a, *b)
            == c.parametros_discrepantes(*b, *a))


# --------------------------------------------------------------------------
# distancia_km
# --------------------------------------------------------------------------
def test_distancia_km_mismo_punto():
    assert c.distancia_km("0", "0", "0", "0") == pytest.approx(0.0, abs=1e-6)


def test_distancia_km_un_grado_meridiano():
    # 1° de latitud ≈ 111.195 km.
    assert c.distancia_km("0", "0", "1", "0") == pytest.approx(111.195, abs=0.01)


def test_distancia_km_un_grado_latitud_media():
    # 1° de longitud en el ecuador ≈ 111.195 km.
    assert c.distancia_km("0", "0", "0", "1") == pytest.approx(111.195, abs=0.01)


def test_distancia_km_dato_faltante():
    assert c.distancia_km("", "0", "0", "0") is None
    assert c.distancia_km("0", None, "0", "0") is None


# --------------------------------------------------------------------------
# no_actualizados
# --------------------------------------------------------------------------
def _fila(**cambios):
    """Fila de atribucion_*.csv «idéntica» por defecto."""
    base = {
        "lat_eventquery": "-33.000", "lon_eventquery": "-71.000",
        "prof_eventquery": "30.0", "mag_eventquery": "5.0",
        "lat_local": "-33.000", "lon_local": "-71.000",
        "prof_local": "30.0", "mag_local": "5.0",
        "fecha_local": "2026-01-01 00:00:00", "dt_seg": "1.0",
        "dist_km": "",
    }
    base.update(cambios)
    return base


def test_no_actualizados_descarta_los_iguales():
    assert c.no_actualizados([_fila()]) == []


def test_no_actualizados_incluye_el_discrepante():
    res = c.no_actualizados([_fila(mag_local="5.5")])
    assert len(res) == 1
    assert res[0]["mag_local"] == "5.5"


def test_no_actualizados_agrupa_y_deja_el_menor_dt():
    filas = [
        _fila(mag_local="5.5", dt_seg="9.0"),
        _fila(mag_local="5.5", dt_seg="2.0"),
        _fila(mag_local="5.5", dt_seg="5.0"),
    ]
    res = c.no_actualizados(filas)
    assert len(res) == 1
    assert res[0]["dt_seg"] == "2.0"


def test_no_actualizados_eventos_locales_distintos_no_se_agrupan():
    filas = [
        _fila(mag_local="5.5", lat_local="-30.0"),
        _fila(mag_local="5.5", lat_local="-40.0"),
    ]
    assert len(c.no_actualizados(filas)) == 2


def test_no_actualizados_completa_dist_km_si_falta():
    res = c.no_actualizados([_fila(mag_local="5.5", dist_km="")])
    assert res[0]["dist_km"] != ""


def test_no_actualizados_respeta_dist_km_existente():
    res = c.no_actualizados([_fila(mag_local="5.5", dist_km="12.5")])
    assert res[0]["dist_km"] == "12.5"


def test_no_actualizados_tolera_diferencia_dentro_de_tolerancia():
    # lat difiere 0.004° (< 0.005) -> no cuenta como no actualizado.
    assert c.no_actualizados([_fila(lat_local="-33.004")]) == []
