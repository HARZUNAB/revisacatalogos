#!/usr/bin/env python3
"""
Tests de asigna_perfiles.py
===========================
Cubre la geometría pura (proyección, distancia al perfil, profundidad del
slab), la lectura de archivos .tmp y la asignación de eventos a perfiles
(cobertura lateral, bordes y extremos).

Los perfiles son sintéticos y orientados E-O (latitud constante) para que el
lado norte/sur sea puramente lateral y los motivos sean predecibles.
"""

import math

import numpy as np
import pytest

import asigna_perfiles as ap


def _perfil(id_perfil, num, lat0, depths=(50.0, 60.0, 70.0)):
    """Perfil recto E-O: p 0..200 km sobre lon 0..2 a latitud constante."""
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


# --------------------------------------------------------------------------
# Conversiones y proyección
# --------------------------------------------------------------------------
def test_km_por_deg_lon():
    assert ap._km_por_deg_lon(0.0) == pytest.approx(111.0)
    assert ap._km_por_deg_lon(60.0) == pytest.approx(55.5)
    # Protección contra coseno casi nulo.
    assert ap._km_por_deg_lon(90.0) == pytest.approx(11.1)


def test_proyectar_a_plano():
    x, y = ap._proyectar_a_plano(1.0, 2.0, 1.0, 2.0)
    assert float(x) == pytest.approx(0.0)
    assert float(y) == pytest.approx(0.0)
    x, y = ap._proyectar_a_plano(2.0, 3.0, 1.0, 2.0)
    assert float(x) == pytest.approx(111.0 * math.cos(math.radians(2.0)))
    assert float(y) == pytest.approx(111.0)


# --------------------------------------------------------------------------
# Lectura de archivos .tmp
# --------------------------------------------------------------------------
def test_centrolinea_perfil_promedia_bin(tmp_path):
    f = tmp_path / "slabP001.tmp"
    f.write_text(
        "# comentario\n"
        "0 0 0.0 0.0 0 0 -50.0\n"
        "0.2 0 0.2 0.1 0 0 -60.0\n"
        "100 0 1.0 0.0 0 0 -70.0\n"
        "linea incompleta\n",
        encoding="utf-8")
    slab = ap._centrolinea_perfil(str(f))
    # Las dos primeras filas caen en el mismo bin p=0 y se promedian.
    assert len(slab["p"]) == 2
    assert slab["p"][0] == pytest.approx(0.0)
    assert slab["lon"][0] == pytest.approx(0.1)
    assert slab["lat"][0] == pytest.approx(0.05)
    assert slab["depth"][0] == pytest.approx(55.0)
    assert slab["depth"][1] == pytest.approx(70.0)


def test_centrolinea_perfil_sin_datos(tmp_path):
    f = tmp_path / "vacio.tmp"
    f.write_text("# solo comentarios\n", encoding="utf-8")
    assert ap._centrolinea_perfil(str(f)) is None


def test_leer_topo(tmp_path):
    f = tmp_path / "topoP001.tmp"
    f.write_text("0 0 0.0 0.0 0 0 100.0\n100 0 1.0 0.0 0 0 250.0\n",
                 encoding="utf-8")
    p, alt = ap._leer_topo(str(f))
    assert list(p) == [0.0, 100.0]
    assert list(alt) == [100.0, 250.0]
    # Archivo inexistente -> arrays vacíos.
    p, alt = ap._leer_topo(str(tmp_path / "no_existe.tmp"))
    assert len(p) == 0 and len(alt) == 0


def test_detectar_perfiles(tmp_path):
    (tmp_path / "slabP001.tmp").write_text(
        "0 0 0.0 0.0 0 0 -50.0\n100 0 1.0 0.0 0 0 -70.0\n", encoding="utf-8")
    (tmp_path / "topoP001.tmp").write_text(
        "0 0 0.0 0.0 0 0 100.0\n", encoding="utf-8")
    (tmp_path / "basura.txt").write_text("x", encoding="utf-8")

    perfiles = ap.detectar_perfiles(str(tmp_path))
    assert len(perfiles) == 1
    per = perfiles[0]
    assert per["id"] == "P001"
    assert per["num"] == 1
    assert per["lat_media"] == pytest.approx(0.0)
    assert len(per["topo_p"]) == 1

    # Carpeta inexistente -> lista vacía.
    assert ap.detectar_perfiles(str(tmp_path / "nope")) == []


# --------------------------------------------------------------------------
# Geometría del perfil
# --------------------------------------------------------------------------
def test_detalle_perfil_devuelve_none_si_falta_geometria():
    perfil = _perfil("P001", 1, 0.0)
    perfil["slab"] = {"p": np.array([0.0]), "lon": np.array([0.0]),
                      "lat": np.array([0.0]), "depth": np.array([50.0])}
    assert ap._detalle_perfil(1.0, 0.0, perfil) is None


def test_detalle_perfil():
    perfil = _perfil("P001", 1, 0.0)
    perp, along, lat_proj, exceso = ap._detalle_perfil(1.0, 0.1, perfil)
    assert perp == pytest.approx(11.1, abs=1e-6)
    assert along == pytest.approx(100.0, abs=1e-6)
    assert lat_proj == pytest.approx(0.0, abs=1e-9)
    assert exceso == pytest.approx(0.0, abs=1e-6)


def test_detalle_perfil_mas_alla_del_extremo():
    perfil = _perfil("P001", 1, 0.0)
    perp, along, _lat_proj, exceso = ap._detalle_perfil(5.0, 0.0, perfil)
    assert exceso == pytest.approx(333.0, abs=1e-3)
    assert along == pytest.approx(200.0, abs=1e-6)


def test_distancia_al_perfil():
    perfil = _perfil("P001", 1, 0.0)
    perp, along = ap.distancia_al_perfil(1.0, 0.1, perfil)
    assert perp == pytest.approx(11.1, abs=1e-6)
    assert along == pytest.approx(100.0, abs=1e-6)


def test_profundidad_slab_en():
    perfil = _perfil("P001", 1, 0.0)
    assert ap.profundidad_slab_en(perfil, 0.0) == pytest.approx(50.0)
    assert ap.profundidad_slab_en(perfil, 100.0) == pytest.approx(60.0)
    assert ap.profundidad_slab_en(perfil, 150.0) == pytest.approx(65.0)
    assert math.isnan(ap.profundidad_slab_en(perfil, -1.0))
    assert math.isnan(ap.profundidad_slab_en(perfil, 500.0))
    assert math.isnan(ap.profundidad_slab_en(perfil, None))


def test_cobertura_set():
    perfiles = [_perfil("P001", 1, 0.0), _perfil("P002", 2, 2.0)]
    cob = ap.cobertura_set(perfiles)
    assert cob["n_perfiles"] == 2
    assert cob["lat_min"] == pytest.approx(0.0)
    assert cob["lat_max"] == pytest.approx(2.0)
    assert cob["lon_min"] == pytest.approx(0.0)
    assert cob["lon_max"] == pytest.approx(2.0)
    assert ap.cobertura_set([]) is None


def test_espaciado_mediano():
    perfiles = [_perfil("P001", 1, 0.0), _perfil("P002", 2, 2.0)]
    assert ap._espaciado_mediano(perfiles) == pytest.approx(222.0)
    assert ap._espaciado_mediano([_perfil("P001", 1, 0.0)]) is None


# --------------------------------------------------------------------------
# Asignación de eventos
# --------------------------------------------------------------------------
def _set_dos_perfiles():
    return [_perfil("P001", 1, 0.0), _perfil("P002", 2, 2.0)]


def test_asignar_evento_sobre_el_perfil():
    r = ap.asignar_perfil_evento(1.0, 0.0, 60.0, _set_dos_perfiles())
    assert r["perfil"] == "P001"
    assert r["perp_km"] == pytest.approx(0.0, abs=1e-6)
    assert r["along_km"] == pytest.approx(100.0, abs=1e-6)
    assert r["residuo_km"] == pytest.approx(0.0, abs=1e-6)
    assert r["motivo"] is None


def test_asignar_evento_con_residuo():
    r = ap.asignar_perfil_evento(1.0, 0.0, 100.0, _set_dos_perfiles())
    assert r["perfil"] == "P001"
    assert r["residuo_km"] == pytest.approx(40.0, abs=1e-6)
    assert r["dist_asoc"] == pytest.approx(40.0, abs=1e-6)


def test_asignar_evento_fuera_cobertura_norte():
    r = ap.asignar_perfil_evento(1.0, 10.0, 60.0, _set_dos_perfiles())
    assert r["perfil"] is None
    assert r["motivo"] == "fuera_cobertura_norte"


def test_asignar_evento_fuera_cobertura_sur():
    r = ap.asignar_perfil_evento(1.0, -10.0, 60.0, _set_dos_perfiles())
    assert r["perfil"] is None
    assert r["motivo"] == "fuera_cobertura_sur"


def test_asignar_evento_fuera_de_extremo():
    r = ap.asignar_perfil_evento(5.0, 0.0, 60.0, _set_dos_perfiles())
    assert r["perfil"] is None
    assert r["motivo"] == "fuera_cobertura_extremo"


def test_asignar_evento_sin_perfiles():
    r = ap.asignar_perfil_evento(1.0, 0.0, 60.0, [])
    assert r["perfil"] is None
    assert r["motivo"] == "sin_perfiles"


def test_asignar_evento_tope_perpendicular():
    r = ap.asignar_perfil_evento(1.0, 1.0, 60.0, _set_dos_perfiles(),
                                 umbral_perp=50.0)
    assert r["perfil"] is None
    assert r["motivo"] == "fuera_umbral"


def test_asignar_evento_respaldo_por_cobertura_lateral():
    # Entre los dos perfiles, a 111 km de cada uno (supera el umbral de 110),
    # queda dentro de la cobertura y se asigna al más cercano en profundidad.
    r = ap.asignar_perfil_evento(1.0, 1.0, 60.0, _set_dos_perfiles(),
                                 umbral=50.0)
    assert r["perfil"] is not None
    assert r["motivo"] is None


def test_asignar_eventos_adorna_los_dicts():
    eventos = [
        {"lon": 1.0, "lat": 0.0, "prof": 60.0},
        {"lon": None, "lat": 0.0, "prof": 60.0},
    ]
    salida = ap.asignar_eventos(eventos, perfiles=_set_dos_perfiles())
    assert salida is eventos
    assert eventos[0]["perfil"] == "P001"
    assert eventos[1]["motivo"] == "sin_coordenadas"


def test_asignar_eventos_callback_avance():
    vistos = []
    eventos = [{"lon": 1.0, "lat": 0.0, "prof": 60.0},
               {"lon": 1.0, "lat": 0.0, "prof": 60.0}]
    ap.asignar_eventos(eventos, perfiles=_set_dos_perfiles(),
                       on_avance=vistos.append)
    assert vistos[-1] == pytest.approx(1.0)
