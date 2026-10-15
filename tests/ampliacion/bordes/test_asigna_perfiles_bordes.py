#!/usr/bin/env python3
"""
Tests de bordes de asigna_perfiles.py
=====================================
Casos borde que el test base no cubre: `prof=None` y `k_peso=0`, la tolerancia
de `umbral_perp`, el borde por `margen_borde`, la detección con ids duplicados
y el fallback de topografía, perfiles sin geometría y eventos raros en
`asignar_eventos`.

El módulo no se modifica en esta tanda.
"""

import numpy as np
import pytest

import asigna_perfiles as ap


def _perfil(id_perfil, num, lat0, depths=(50.0, 60.0, 70.0)):
    slab = {
        "p": np.array([0.0, 100.0, 200.0]),
        "lon": np.array([0.0, 1.0, 2.0]),
        "lat": np.array([lat0, lat0, lat0], dtype=float),
        "depth": np.array(depths, dtype=float),
    }
    return {
        "id": id_perfil, "num": num,
        "archivo": "slabP%03d.tmp" % num,
        "lat_media": float(lat0),
        "slab": slab,
        "topo_p": np.array([]), "topo_alt": np.array([]),
    }


def _set_dos_perfiles():
    return [_perfil("P001", 1, 0.0), _perfil("P002", 2, 2.0)]


# --------------------------------------------------------------------------
# asignar_perfil_evento: prof None / k_peso 0
# --------------------------------------------------------------------------
def test_asignar_con_profundidad_none():
    r = ap.asignar_perfil_evento(1.0, 0.0, None, _set_dos_perfiles())
    assert r["perfil"] == "P001"
    assert r["residuo_km"] is None
    assert r["dist_asoc"] == pytest.approx(0.0, abs=1e-6)
    assert r["motivo"] is None


def test_asignar_con_k_peso_cero_ignora_profundidad():
    r = ap.asignar_perfil_evento(1.0, 0.0, 300.0, _set_dos_perfiles(),
                                 k_peso=0.0)
    assert r["perfil"] == "P001"
    assert r["residuo_km"] == pytest.approx(240.0, abs=1e-6)
    assert r["dist_asoc"] == pytest.approx(0.0, abs=1e-6)


# --------------------------------------------------------------------------
# umbral_perp con tolerancia _TOL_KM
# --------------------------------------------------------------------------
def test_asignar_umbral_perp_tolerancia():
    # perp ~111 km: con umbral 109.5 queda fuera; con 110.0 entra por la
    # tolerancia _TOL_KM = 1.0.
    fuera = ap.asignar_perfil_evento(1.0, 1.0, 60.0, _set_dos_perfiles(),
                                     umbral_perp=109.5)
    assert fuera["motivo"] == "fuera_umbral"
    dentro = ap.asignar_perfil_evento(1.0, 1.0, 60.0, _set_dos_perfiles(),
                                      umbral_perp=110.0)
    assert dentro["motivo"] is None


# --------------------------------------------------------------------------
# margen_borde
# --------------------------------------------------------------------------
def test_asignar_margen_borde_justo():
    perfil = [_perfil("P001", 1, 0.0)]
    dentro = ap.asignar_perfil_evento(1.0, 0.15, 60.0, perfil,
                                      margen_borde=20.0, umbral_perp=None)
    assert dentro["perfil"] == "P001"
    fuera = ap.asignar_perfil_evento(1.0, 0.25, 60.0, perfil,
                                     margen_borde=20.0, umbral_perp=None)
    assert fuera["perfil"] is None
    assert fuera["motivo"] == "fuera_cobertura_norte"


# --------------------------------------------------------------------------
# detectar_perfiles
# --------------------------------------------------------------------------
_SLAB = "0 0 0.0 0.0 0 0 -50.0\n100 0 1.0 0.0 0 0 -70.0\n"


def test_detectar_perfiles_ids_duplicados(tmp_path, capsys):
    (tmp_path / "slabP01.tmp").write_text(_SLAB, encoding="utf-8")
    (tmp_path / "slabP001.tmp").write_text(_SLAB, encoding="utf-8")
    (tmp_path / "slabP002.tmp").write_text("# solo comentarios\n",
                                           encoding="utf-8")
    perfiles = ap.detectar_perfiles(str(tmp_path))
    # P01 y P001 -> mismo id "P001"; P002 sin filas se omite.
    assert [p["id"] for p in perfiles] == ["P001", "P001"]
    salida = capsys.readouterr().out
    assert "Aviso" in salida and "P001" in salida


def test_detectar_perfiles_fallback_topo_tres_digitos(tmp_path):
    (tmp_path / "slabP1.tmp").write_text(_SLAB, encoding="utf-8")
    (tmp_path / "topoP001.tmp").write_text(
        "0 0 0.0 0.0 0 0 100.0\n100 0 1.0 0.0 0 0 250.0\n", encoding="utf-8")
    perfiles = ap.detectar_perfiles(str(tmp_path))
    assert len(perfiles) == 1
    assert perfiles[0]["num"] == 1
    assert perfiles[0]["archivo"] == "slabP1.tmp"
    assert len(perfiles[0]["topo_p"]) == 2


# --------------------------------------------------------------------------
# distancia_al_perfil con geometría insuficiente
# --------------------------------------------------------------------------
def test_distancia_al_perfil_slab_de_un_punto():
    perfil = _perfil("P001", 1, 0.0)
    perfil["slab"] = {"p": np.array([0.0]), "lon": np.array([0.0]),
                      "lat": np.array([0.0]), "depth": np.array([50.0])}
    assert ap.distancia_al_perfil(1.0, 0.0, perfil) == (None, None)


# --------------------------------------------------------------------------
# asignar_eventos
# --------------------------------------------------------------------------
def test_asignar_eventos_vacio_no_llama_callback():
    vistos = []
    salida = ap.asignar_eventos([], perfiles=[], on_avance=vistos.append)
    assert salida == []
    assert vistos == []


def test_asignar_eventos_lat_no_numerica():
    eventos = [{"lon": 1.0, "lat": "abc", "prof": 60.0}]
    ap.asignar_eventos(eventos, perfiles=_set_dos_perfiles())
    assert eventos[0]["motivo"] == "sin_coordenadas"


def test_asignar_eventos_sin_perfiles():
    eventos = [{"lon": 1.0, "lat": 0.0, "prof": 60.0}]
    ap.asignar_eventos(eventos, perfiles=[])
    assert eventos[0]["motivo"] == "sin_perfiles"


def test_asignar_eventos_profundidad_negativa_avisa(capsys):
    eventos = [{"lon": 1.0, "lat": 0.0, "prof": -10.0}]
    ap.asignar_eventos(eventos, perfiles=_set_dos_perfiles())
    assert eventos[0]["perfil"] == "P001"
    assert "profundidad negativa" in capsys.readouterr().out
