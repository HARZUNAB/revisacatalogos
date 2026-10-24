#!/usr/bin/env python3
"""
Tests de fronteras.py
=====================
Cubre el cálculo con geometrías sintéticas, sin depender de Natural Earth.
"""

import pytest

pytest.importorskip("shapely")
pytest.importorskip("pyproj")

from shapely.geometry import LineString, Point, box  # noqa: E402
from shapely.prepared import prep  # noqa: E402

import fronteras as f  # noqa: E402


@pytest.fixture(autouse=True)
def _cache_limpia():
    f.limpiar_cache()
    yield
    f.limpiar_cache()


def _paises_sinteticos(peru_oeste=-69.5):
    chile = box(-75.0, -30.0, -69.5, -20.0)
    peru = box(peru_oeste, -30.0, -65.0, -20.0)
    bolivia = box(-65.0, -30.0, -60.0, -20.0)
    argentina = box(-60.0, -30.0, -55.0, -20.0)
    paises = {"CHL": chile, "PER": peru,
              "BOL": bolivia, "ARG": argentina}
    prep_paises = {codigo: prep(geom)
                   for codigo, geom in paises.items()}
    return paises, prep_paises


def _datos_sinteticos():
    # Chile al oeste de -69.5; Perú al este. La frontera es la línea vertical.
    paises, prep_paises = _paises_sinteticos()
    frontera = LineString([(-69.5, -30.0), (-69.5, -20.0)])
    return ({"PER": [frontera]}, paises, prep_paises)


def test_frontera_fuera_de_chile():
    pais, km = f._frontera_en_datos(-25.0, -69.0, _datos_sinteticos())

    assert pais == "Perú"
    assert km == pytest.approx(50.5, abs=1.0)


def test_frontera_dentro_de_chile():
    assert f._frontera_en_datos(-25.0, -70.0, _datos_sinteticos()) is None


def test_mar_chileno_cerca_de_la_costa_no_muestra_frontera():
    assert f._frontera_en_datos(-25.0, -76.0, _datos_sinteticos()) is None


def test_mar_mas_cercano_a_peru_si_muestra_frontera():
    # Chile termina en -69.5 y Perú empieza en -68; el punto -68.2 está en
    # el mar, pero más cerca de Perú que de Chile.
    paises, prep_paises = _paises_sinteticos(peru_oeste=-68.0)
    punto = Point(-68.2, -25.0)

    assert f._es_mar_chileno(
        -68.2, -25.0, punto, paises, prep_paises) is False


def test_formatear_frontera():
    assert f.formatear_frontera(("Perú", 34.9)) == "Perú — 34.9 km"
    assert f.formatear_frontera(None) == "—"


def test_anotar_fila(monkeypatch):
    monkeypatch.setattr(f, "frontera_mas_cercana",
                        lambda lat, lon: ("Bolivia", 182.7))
    fila = {"latitud": "-16.5", "longitud": "-68.15"}

    f.anotar_fila(fila)

    assert fila["Frontera_pais"] == "Bolivia"
    assert fila["Frontera_km"] == 182.7
    assert f.texto_frontera(fila) == "Bolivia — 182.7 km"


def test_anotar_fila_sin_dato(monkeypatch):
    monkeypatch.setattr(f, "frontera_mas_cercana",
                        lambda lat, lon: None)
    fila = {"latitud": "-33.45", "longitud": "-70.67"}

    f.anotar_fila(fila)

    assert fila["Frontera_pais"] == ""
    assert fila["Frontera_km"] is None
    assert f.texto_frontera(fila) == "—"


def test_frontera_sin_datos(monkeypatch):
    f.limpiar_cache()
    monkeypatch.setattr(f, "_cargar_datos", lambda: None)

    assert f.frontera_mas_cercana(-20.0, -70.0) is None
