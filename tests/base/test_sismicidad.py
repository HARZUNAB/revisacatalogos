#!/usr/bin/env python3
"""
Tests de sismicidad.py
======================
Cubre la clasificación de un evento como «posible mal localizado»: las pruebas
individuales (residuo, knn, densidad, aislamiento, mediana), las consultas
espaciales sobre el catálogo y la combinación de reglas de ``evaluar``.

Se usa un catálogo sintético; el real (``base_2020_2026.dat``) nunca se toca.
"""

import math

import numpy as np
import pytest

import sismicidad as s


def _catalogo(puntos):
    """Catálogo con la misma estructura que devuelve cargar_catalogo()."""
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


def _ev(lat=0.0, lon=0.0, prof=0.0, perfil="P01", perp=10.0, residuo=0.0,
        dist_asoc=0.0, id_ev=1):
    return {
        "id": id_ev, "latitud": lat, "longitud": lon, "prof": prof,
        "perfil": perfil, "perp_km": perp, "residuo_km": residuo,
        "dist_asoc": dist_asoc,
    }


# --------------------------------------------------------------------------
# _coord_evento_en_km
# --------------------------------------------------------------------------
def test_coord_evento_en_el_centro_es_cero():
    cat = _catalogo([(0.0, 0.0, 0.0), (0.0, 0.0, 0.0)])
    x, y = s._coord_evento_en_km(_ev(lat=0.0, lon=0.0), cat)
    assert x == pytest.approx(0.0, abs=1e-9)
    assert y == pytest.approx(0.0, abs=1e-9)


# --------------------------------------------------------------------------
# _dist_kkn
# --------------------------------------------------------------------------
def test_dist_kkn_excluye_el_propio_evento():
    # El evento coincide con el primer punto: ese se descarta, queda el de 10 km.
    cat = _catalogo([(0.0, 0.0, 0.0), (0.0, 0.0, 10.0)])
    assert s._dist_kkn(_ev(0.0, 0.0, 0.0), cat, 1) == pytest.approx(10.0, abs=1e-6)


def test_dist_kkn_sin_vecinos_utiles():
    # Todos los puntos coinciden con el evento -> no hay con qué comparar.
    cat = _catalogo([(0.0, 0.0, 0.0), (0.0, 0.0, 0.0)])
    assert s._dist_kkn(_ev(0.0, 0.0, 0.0), cat, 5) is None


def test_dist_kkn_dato_invalido():
    cat = _catalogo([(0.0, 0.0, 0.0), (1.0, 1.0, 10.0)])
    assert s._dist_kkn(_ev(prof="x"), cat, 1) is None


# --------------------------------------------------------------------------
# _vecinos_ventana
# --------------------------------------------------------------------------
def test_vecinos_ventana_cuenta_y_excluye_self():
    cat = _catalogo([
        (0.0, 0.0, 0.0),     # self -> excluido
        (0.0, 0.0, 10.0),    # dentro (banda prof 10)
        (0.0, 0.0, 100.0),   # fuera (prof)
        (1.0, 0.0, 0.0),     # fuera (radio horizontal ~111 km)
    ])
    mask, motivo = s._vecinos_ventana(_ev(0.0, 0.0, 0.0), cat,
                                      radio_km=20.0, banda_prof_km=20.0)
    assert motivo is None
    assert int(mask.sum()) == 1


def test_vecinos_ventana_datos_invalidos():
    cat = _catalogo([(0.0, 0.0, 0.0)])
    mask, motivo = s._vecinos_ventana(_ev(prof="x"), cat, 10.0, 10.0)
    assert mask is None
    assert motivo


# --------------------------------------------------------------------------
# Pruebas individuales
# --------------------------------------------------------------------------
def test_test_perp():
    cfg = {"valor": 55.0}
    assert s._test_perp(_ev(perp=60.0), cfg, None) is True
    assert s._test_perp(_ev(perp=10.0), cfg, None) is False
    assert s._test_perp(_ev(perp=60.0, perfil=None), cfg, None) is False
    assert s._test_perp(_ev(perp=None), cfg, None) is False


def test_test_residuo():
    cfg = {"valor": 30.0}
    assert s._test_residuo(_ev(residuo=50.0), cfg, None) is True
    assert s._test_residuo(_ev(residuo=10.0), cfg, None) is False
    # residuo None -> se asume lejos del slab (prueba positiva).
    assert s._test_residuo(_ev(residuo=None), cfg, None) is True


def test_test_densidad_local():
    cat = _catalogo([(0.0, 0.0, 10.0)])
    ev = _ev(0.0, 0.0, 0.0)
    assert s._test_densidad_local(ev, {"radio_km": 20.0, "banda_prof_km": 20.0,
                                       "max_vecinos": 1}, cat) is True
    assert s._test_densidad_local(ev, {"radio_km": 20.0, "banda_prof_km": 20.0,
                                       "max_vecinos": 0}, cat) is False
    assert s._test_densidad_local(ev, {"radio_km": 20.0, "banda_prof_km": 20.0,
                                       "max_vecinos": 1}, None) is False


def test_test_knn():
    cat = _catalogo([(0.0, 0.0, 0.0), (0.0, 0.0, 30.0)])
    ev = _ev(0.0, 0.0, 0.0)
    assert s._test_knn(ev, {"k": 1, "umbral_km": 15.0}, cat) is True
    assert s._test_knn(ev, {"k": 1, "umbral_km": 50.0}, cat) is False
    assert s._test_knn(ev, {"k": 1, "umbral_km": 15.0}, None) is False


def test_test_aislamiento():
    cat = _catalogo([(0.0, 0.0, 10.0)])
    ev = _ev(0.0, 0.0, 0.0)
    cfg = {"radio_km": 20.0, "banda_prof_km": 20.0}
    assert s._test_aislamiento(ev, dict(cfg, min_vecinos=2), cat) is True
    assert s._test_aislamiento(ev, dict(cfg, min_vecinos=1), cat) is False


def test_test_mediana_prof():
    cat = _catalogo([(0.0, 0.0, 10.0), (0.0, 0.0, 20.0), (0.0, 0.0, 30.0)])
    ev = _ev(0.0, 0.0, 0.0)
    base = {"radio_km": 50.0, "banda_prof_km": 50.0, "min_vecinos": 2}
    # mediana = 20, evento a 0 -> desvío 20 > 15.
    assert s._test_mediana_prof(ev, dict(base, umbral_km=15.0), cat) is True
    assert s._test_mediana_prof(ev, dict(base, umbral_km=25.0), cat) is False
    # Pocos vecinos -> no evalúa.
    assert s._test_mediana_prof(ev, dict(base, min_vecinos=9), cat) is False


# --------------------------------------------------------------------------
# evaluar
# --------------------------------------------------------------------------
def _criterios(pruebas, regla="ambos_grupos", sin_catalogo="ninguno"):
    return {
        "regla": regla,
        "grupos": {"slab": ["residuo_max_km"], "historica": ["knn"]},
        "min_por_grupo": {"slab": 1, "historica": 1},
        "sin_catalogo": sin_catalogo,
        "pruebas": pruebas,
    }


def test_evaluar_sin_perfil_es_sospechoso():
    r = s.evaluar(_ev(perfil=None), catalogo=None)
    assert r["sospechoso"] is True
    assert r["sin_perfil"] is True


def test_evaluar_sin_pruebas_activas_no_marca():
    criterios = _criterios({"residuo_max_km": {"activo": False},
                            "knn": {"activo": False}})
    r = s.evaluar(_ev(), catalogo=None, criterios=criterios)
    assert r["sospechoso"] is False
    assert r["pruebas"] == {}


def test_evaluar_ambos_grupos_marcan():
    cat = _catalogo([(0.0, 0.0, 0.0)])  # lejano al evento (10°)
    criterios = _criterios({
        "residuo_max_km": {"activo": True, "valor": 30.0},
        "knn": {"activo": True, "k": 1, "umbral_km": 15.0},
    })
    r = s.evaluar(_ev(lat=10.0, residuo=50.0), catalogo=cat, criterios=criterios)
    assert r["sospechoso"] is True
    assert r["grupos"]["slab"]["cumplido"] is True
    assert r["grupos"]["historica"]["cumplido"] is True


def test_evaluar_ambos_grupos_requiere_los_dos():
    # Cerca del slab no, pero históricamente cerca -> no sospechoso.
    cat = _catalogo([(0.0, 0.0, 0.0), (0.001, 0.001, 0.0)])
    criterios = _criterios({
        "residuo_max_km": {"activo": True, "valor": 30.0},
        "knn": {"activo": True, "k": 1, "umbral_km": 15.0},
    })
    r = s.evaluar(_ev(0.0, 0.0, 0.0, residuo=50.0),
                  catalogo=cat, criterios=criterios)
    assert r["grupos"]["slab"]["cumplido"] is True
    assert r["grupos"]["historica"]["cumplido"] is False
    assert r["sospechoso"] is False


def test_evaluar_cualquier_grupo_basta():
    cat = _catalogo([(0.0, 0.0, 0.0), (0.001, 0.001, 0.0)])
    criterios = _criterios({
        "residuo_max_km": {"activo": True, "valor": 30.0},
        "knn": {"activo": True, "k": 1, "umbral_km": 15.0},
    }, regla="cualquier_grupo")
    r = s.evaluar(_ev(0.0, 0.0, 0.0, residuo=50.0),
                  catalogo=cat, criterios=criterios)
    assert r["sospechoso"] is True


def test_evaluar_sin_catalogo_ninguno():
    # knn inactiva -> el grupo "historica" no es evaluable.
    criterios = _criterios({"residuo_max_km": {"activo": True, "valor": 30.0},
                            "knn": {"activo": False}}, sin_catalogo="ninguno")
    r = s.evaluar(_ev(residuo=50.0), catalogo=None, criterios=criterios)
    assert r["sospechoso"] is False


def test_evaluar_sin_catalogo_solo_slab():
    criterios = _criterios({"residuo_max_km": {"activo": True, "valor": 30.0},
                            "knn": {"activo": False}}, sin_catalogo="solo_slab")
    r = s.evaluar(_ev(residuo=50.0), catalogo=None, criterios=criterios)
    assert r["sospechoso"] is True


# --------------------------------------------------------------------------
# es_sospechoso / explicar_sospechoso
# --------------------------------------------------------------------------
def test_es_sospechoso_delega_en_evaluar():
    assert s.es_sospechoso(_ev(perfil=None), catalogo=None) is True


def test_explicar_sospechoso_sin_perfil():
    texto = s.explicar_sospechoso(_ev(perfil=None), catalogo=None)
    assert "sin perfil" in texto


def test_explicar_sospechoso_con_pruebas():
    cat = _catalogo([(10.0, 10.0, 0.0)])
    criterios = _criterios({
        "residuo_max_km": {"activo": True, "valor": 30.0},
        "knn": {"activo": True, "k": 1, "umbral_km": 15.0},
    })
    texto = s.explicar_sospechoso(_ev(lat=0.0, lon=0.0, residuo=50.0),
                                  catalogo=cat, criterios=criterios)
    assert "SOSPECHOSO" in texto
    assert "slab:" in texto and "historica:" in texto
