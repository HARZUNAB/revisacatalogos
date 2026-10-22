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


def _celdas_descarga(ev):
    """Fila de descarga indexada por clave de columna."""
    return {clave: valor for (clave, _titulo, _ancho), valor
            in zip(plotear.COLUMNAS_DESCARGA_EVENTO,
                   plotear._fila_descarga(ev))}


def test_fila_descarga_formatea_las_distancias_a_un_decimal():
    ev = {"id": "x", "perfil": "P001", "along_km": 101.429, "perp_km": 5.0,
          "residuo_km": None, "dist_asoc": 8.94}
    celdas = _celdas_descarga(ev)
    assert celdas["along_km"] == "101.4"
    assert celdas["perp_km"] == "5.0"
    assert celdas["residuo_km"] == ""
    assert celdas["dist_asoc"] == "8.9"


def test_texto_parametros_evento_along_con_un_decimal():
    ev = {"id": "x", "fecha hora": "2026-01-01 00:00:00", "latitud": -33.0,
          "longitud": -70.0, "prof": 90.0, "magnitud": 3.0, "tipo": "ML",
          "perfil": "P001", "along_km": 101.429}
    texto = plotear._texto_parametros_evento(ev)
    assert "along: 101.4 km" in texto



def test_resumen_perfil_cuenta_altas():
    eventos = [{"latitud": 0, "longitud": 0, "revision": "Alta"},
               {"latitud": 0, "longitud": 0, "revision": "Baja"}]
    total, sosp, perc, altas, _a_min, _a_max = plotear._resumen_perfil(
        eventos, "seiscomp")
    assert (total, sosp, perc, altas) == (2, 0, 0, 1)


def test_columnas_descarga_noact_incluyen_clasificacion():
    claves = [c for c, _t, _a in plotear.COLUMNAS_DESCARGA_NOACT]
    assert claves.index("publicacion_probable") == claves.index("analistas") + 1
    assert claves.index("revision") == claves.index("analistas") + 2


def test_fila_descarga_noact_exporta_clasificacion():
    ev = {"id": "x", "publicacion_probable": "Esta fuente",
          "revision": "Alta"}
    celdas = {clave: valor for (clave, _t, _a), valor
              in zip(plotear.COLUMNAS_DESCARGA_NOACT,
                     plotear._fila_descarga(
                         ev, plotear.COLUMNAS_DESCARGA_NOACT))}
    assert celdas["publicacion_probable"] == "Esta fuente"
    assert celdas["revision"] == "Alta"


def test_texto_parametros_evento_muestra_clasificacion():
    ev = {"fecha hora": "2026-01-01 00:00:00", "latitud": -33.0,
          "longitud": -70.0, "prof": 90.0, "magnitud": 3.0, "tipo": "ML",
          "publicacion_probable": "Otra fuente", "revision": "Baja",
          "revision_motivo": "Seisan está más cerca"}
    texto = plotear._texto_parametros_evento(ev)
    assert "publicación probable: Otra fuente" in texto
    assert "revisión: Baja (Seisan está más cerca)" in texto
