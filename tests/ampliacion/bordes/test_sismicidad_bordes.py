#!/usr/bin/env python3
"""
Tests de bordes de sismicidad.py
================================
Casos borde que el test base no cubre: carga del catálogo desde archivo (con
líneas inválidas, vacío y caché), límites exactos de `residuo`/`perp`, `k=0`,
el umbral de self de la ventana (0.5 km) y combinaciones de `evaluar`.

El módulo no se modifica en esta tanda.
"""

import math
import os
import warnings

import numpy as np
import pytest

import sismicidad as s


def _ev(lat=0.0, lon=0.0, prof=0.0, perfil="P01", perp=10.0, residuo=0.0,
        dist_asoc=0.0, id_ev=1):
    return {
        "id": id_ev, "latitud": lat, "longitud": lon, "prof": prof,
        "perfil": perfil, "perp_km": perp, "residuo_km": residuo,
        "dist_asoc": dist_asoc,
    }


def _catalogo(puntos):
    lat = np.array([p[0] for p in puntos], dtype=float)
    lon = np.array([p[1] for p in puntos], dtype=float)
    prof = np.array([p[2] for p in puntos], dtype=float)
    lat_ref = float(np.mean(lat))
    lon_ref = float(np.mean(lon))
    k_lon = s.GRADO_KM_LAT * max(0.1, float(math.cos(math.radians(lat_ref))))
    return {
        "lat": lat, "lon": lon, "prof": prof,
        "lat_ref": lat_ref, "lon_ref": lon_ref,
        "x": (lon - lon_ref) * k_lon,
        "y": (lat - lat_ref) * s.GRADO_KM_LAT,
    }


# --------------------------------------------------------------------------
# cargar_catalogo
# --------------------------------------------------------------------------
def test_cargar_catalogo_inexistente(monkeypatch, tmp_path):
    monkeypatch.setattr(s, "_cache_catalogo", None)
    assert s.cargar_catalogo(str(tmp_path / "no_existe.dat")) is None


def test_cargar_catalogo_mixto_descarta_invalidas(monkeypatch, tmp_path):
    monkeypatch.setattr(s, "_cache_catalogo", None)
    p = tmp_path / "cat.dat"
    p.write_text(
        "a\t-33.5\t-71.0\t30.0\tx\ty\tz\n"       # válida
        "corta\t-1\n"                             # < 7 campos -> descartada
        "a\tno-num\t-71.0\t30.0\tx\ty\tz\n"      # lat no numérica -> descartada
        "a\t-34.5\t-72.0\t40.0\tx\ty\tz\n",      # válida
        encoding="utf-8")
    cat = s.cargar_catalogo(str(p))
    assert len(cat["lat"]) == 2
    assert cat["lat_ref"] == pytest.approx(-34.0)


def test_cargar_catalogo_vacio(monkeypatch, tmp_path):
    monkeypatch.setattr(s, "_cache_catalogo", None)
    p = tmp_path / "vacio.dat"
    p.write_text("", encoding="utf-8")
    assert s.cargar_catalogo(str(p)) is None


def test_cargar_catalogo_cachea(monkeypatch, tmp_path):
    monkeypatch.setattr(s, "_cache_catalogo", None)
    p = tmp_path / "cat.dat"
    p.write_text("a\t-33.5\t-71.0\t30.0\tx\ty\tz\n", encoding="utf-8")
    primera = s.cargar_catalogo(str(p))
    os.remove(str(p))
    # La segunda devuelve el mismo objeto cacheado aunque el archivo ya no esté.
    assert s.cargar_catalogo(str(p)) is primera


# --------------------------------------------------------------------------
# límites exactos de las pruebas
# --------------------------------------------------------------------------
def test_test_residuo_en_el_limite():
    # El corte es >=: residuo igual al valor dispara.
    assert s._test_residuo(_ev(residuo=30.0), {"valor": 30.0}, None) is True
    assert s._test_residuo(_ev(residuo="x"), {"valor": 30.0}, None) is False


def test_test_perp_en_el_limite():
    # El corte es >: perp igual al valor no dispara.
    assert s._test_perp(_ev(perp=55.0), {"valor": 55.0}, None) is False
    assert s._test_perp(_ev(perp="x"), {"valor": 55.0}, None) is False


def test_test_knn_con_k_cero_no_marca():
    cat = _catalogo([(0.0, 0.0, 0.0), (0.0, 0.0, 30.0)])
    # k=0: la distancia es nan y la comparación nan > umbral da False.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        assert s._test_knn(_ev(), {"k": 0, "umbral_km": 1.0}, cat) is False


def test_dist_kkn_con_k_cero_es_nan():
    cat = _catalogo([(0.0, 0.0, 0.0), (0.0, 0.0, 30.0)])
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        assert math.isnan(s._dist_kkn(_ev(), cat, 0))


# --------------------------------------------------------------------------
# _vecinos_ventana: umbral de self (0.5 km)
# --------------------------------------------------------------------------
def test_vecinos_ventana_umbral_self():
    # Catálogo con x explícito: puntos a 0.4 km (excluido, d3_2 <= 0.25) y
    # 0.6 km (incluido). El evento está en el origen.
    cat = {
        "lat": np.array([0.0, 0.0, 0.0]), "lon": np.array([0.0, 0.0, 0.0]),
        "prof": np.array([0.0, 0.0, 0.0]), "lat_ref": 0.0, "lon_ref": 0.0,
        "x": np.array([0.0, 0.4, 0.6]), "y": np.array([0.0, 0.0, 0.0]),
    }
    mask, motivo = s._vecinos_ventana(_ev(), cat, radio_km=10.0,
                                      banda_prof_km=10.0)
    assert motivo is None
    assert int(mask.sum()) == 1


# --------------------------------------------------------------------------
# evaluar: regla distinta y prueba fuera de los grupos
# --------------------------------------------------------------------------
def test_evaluar_regla_distinta_se_comporta_como_or():
    cat = _catalogo([(0.0, 0.0, 0.0)])
    criterios = {
        "regla": "otra", "grupos": {"slab": ["residuo_max_km"]},
        "min_por_grupo": {"slab": 1},
        "pruebas": {"residuo_max_km": {"activo": True, "valor": 30.0}},
    }
    r = s.evaluar(_ev(residuo=50.0), catalogo=cat, criterios=criterios)
    assert r["sospechoso"] is True


def test_evaluar_prueba_fuera_de_los_grupos_se_ignora():
    cat = _catalogo([(0.0, 0.0, 0.0)])
    criterios = {
        "regla": "ambos_grupos",
        "grupos": {"slab": ["residuo_max_km"], "historica": ["knn"]},
        "min_por_grupo": {"slab": 1, "historica": 1},
        "pruebas": {"densidad_local": {"activo": True, "radio_km": 20.0,
                                       "banda_prof_km": 20.0, "max_vecinos": 40}},
    }
    r = s.evaluar(_ev(), catalogo=cat, criterios=criterios)
    assert r["pruebas"] == {"densidad_local": True}
    assert r["sospechoso"] is False


# --------------------------------------------------------------------------
# explicar_sospechoso: sin grupos ni pruebas
# --------------------------------------------------------------------------
def test_explicar_sospechoso_sin_grupos_ni_pruebas():
    cat = _catalogo([(0.0, 0.0, 0.0)])
    criterios = {"regla": "ambos_grupos", "pruebas": {}}
    texto = s.explicar_sospechoso(_ev(), catalogo=cat, criterios=criterios)
    assert "no marcado" in texto
    assert texto.endswith("grupos: ")
