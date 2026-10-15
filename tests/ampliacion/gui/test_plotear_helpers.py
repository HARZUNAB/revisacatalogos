#!/usr/bin/env python3
"""
Tests de plotear.py — helpers puros
===================================
Cubre los ayudantes puros de `plotear.py`: agrupado por perfil (con huérfanos),
conversión a número, dirección cardinal, distancia a una caja, categorización
por territorio, formateo de valores y de números.

Marcador `gui`: importar `plotear` arrastra matplotlib/cartopy/PIL/adjustText,
que el CI no instala, así que el módulo se saltea en CI con `importorskip`
(aunque estos tests no necesiten pantalla).
"""

import pytest

pytest.importorskip("matplotlib")
pytest.importorskip("cartopy")
pytest.importorskip("PIL")
pytest.importorskip("adjustText")

import plotear  # noqa: E402

pytestmark = pytest.mark.gui


# --------------------------------------------------------------------------
# _agrupar_por_perfil
# --------------------------------------------------------------------------
def test_agrupar_por_perfil():
    perfiles = {"P001": {"id": "P001"}}
    eventos = [
        {"id": "a", "perfil": "P001"},
        {"id": "b", "perfil": None},
        {"id": "c", "perfil": "P999"},
    ]
    grupos, sin_perfil, huerfanos = plotear._agrupar_por_perfil(eventos, perfiles)
    assert [e["id"] for e in grupos["P001"]] == ["a"]
    assert [e["id"] for e in sin_perfil] == ["b"]
    assert [e["id"] for e in huerfanos["P999"]] == ["c"]


def test_agrupar_por_perfil_avisa_huerfanos(capsys):
    eventos = [{"id": "c", "perfil": "P999"}]
    plotear._agrupar_por_perfil(eventos, {})
    assert "otro conjunto de grillas" in capsys.readouterr().out


# --------------------------------------------------------------------------
# _a_numero_o_none
# --------------------------------------------------------------------------
@pytest.mark.parametrize("valor, esperado", [
    (3.5, 3.5), ("-31.5", -31.5), (" 2 ", 2.0),
    (None, None), ("", None), ("abc", None),
])
def test_a_numero_o_none(valor, esperado):
    assert plotear._a_numero_o_none(valor) == esperado


# --------------------------------------------------------------------------
# _direccion_cardinal
# --------------------------------------------------------------------------
@pytest.mark.parametrize("lon2, lat2, esperado", [
    (0, 1, "N"), (0, -1, "S"), (1, 0, "E"), (-1, 0, "O"),
    (1, 1, "NE"), (1, -1, "SE"),
])
def test_direccion_cardinal(lon2, lat2, esperado):
    assert plotear._direccion_cardinal(0, 0, lon2, lat2) == esperado


def test_direccion_cardinal_mismo_punto_y_basura():
    assert plotear._direccion_cardinal(0, 0, 0, 0) == ""
    assert plotear._direccion_cardinal(None, 0, 0, 0) == ""


# --------------------------------------------------------------------------
# _distancia_a_rectangulo
# --------------------------------------------------------------------------
def test_distancia_a_rectangulo():
    limites = ((-77.0, -66.0), (-56.0, -17.5))
    assert plotear._distancia_a_rectangulo(-70.0, -33.0, limites) == 0.0
    # Fuera por el este: solo el desvío en longitud.
    assert plotear._distancia_a_rectangulo(0.0, -33.0, limites) == \
        pytest.approx(66.0)


# --------------------------------------------------------------------------
# _categorizar_por_territorio
# --------------------------------------------------------------------------
def test_categorizar_por_territorio():
    eventos = [
        {"id": "nac", "longitud": "-70.0", "latitud": "-33.0"},
        {"id": "ins", "longitud": "-100.0", "latitud": "-40.0"},
        {"id": "ant", "longitud": "-70.0", "latitud": "-60.0"},
        {"id": "sin", "latitud": "x"},
    ]
    nacional, insular, antartico = plotear._categorizar_por_territorio(eventos)
    assert [e["id"] for e in nacional] == ["nac"]
    assert [e["id"] for e in insular] == ["ins"]
    assert [e["id"] for e in antartico] == ["ant"]


def test_categorizar_fuera_de_todos_va_al_mas_cercano(capsys):
    eventos = [{"id": "x", "longitud": "0.0", "latitud": "0.0"}]
    nacional, insular, antartico = plotear._categorizar_por_territorio(eventos)
    assert [e["id"] for e in nacional] == ["x"]
    assert "fuera de los límites" in capsys.readouterr().out


# --------------------------------------------------------------------------
# _valor_descarga / _numero_evento
# --------------------------------------------------------------------------
@pytest.mark.parametrize("valor, esperado", [
    (None, ""), (True, "sí"), (False, "no"), ([1, 2], "1, 2"),
    (3.5, "3.5"), ("txt", "txt"),
])
def test_valor_descarga(valor, esperado):
    assert plotear._valor_descarga(valor) == esperado


@pytest.mark.parametrize("valor, decimales, esperado", [
    (3.14159, 2, "3.14"), ("-31.639999999", 3, "-31.640"),
    (None, 1, ""), ("", 1, ""), ("abc", 1, "abc"),
])
def test_numero_evento(valor, decimales, esperado):
    assert plotear._numero_evento(valor, decimales) == esperado
