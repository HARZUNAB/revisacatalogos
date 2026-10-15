#!/usr/bin/env python3
"""
Tests de plotear.py — apertura de figuras interactivas
======================================================
Cubre `abrir_eventos`, `abrir_evento` y `abrir_comparacion` con **figuras
reales** (backend TkAgg, `bloquear=False` → `mgr.show()`, que no bloquea) y un
perfil sintético, sin depender de las grillas del repositorio. Necesita
`DISPLAY`.
"""

import numpy as np
import pytest

pytest.importorskip("matplotlib")
pytest.importorskip("cartopy")
pytest.importorskip("PIL")
pytest.importorskip("adjustText")

import matplotlib  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402

import plotear  # noqa: E402

pytestmark = pytest.mark.gui


@pytest.fixture(autouse=True)
def _entorno():
    # TkAgg: `mgr.show()` (bloquear=False) funciona y no bloquea. Contrarresta
    # el Agg que dejan otros módulos.
    matplotlib.use("TkAgg", force=True)
    plotear._fig_ancla = None
    yield
    plotear._fig_ancla = None
    plt.close("all")


def _perfil():
    slab = {"p": np.array([0.0, 100.0, 200.0]),
            "lon": np.array([0.0, 1.0, 2.0]),
            "lat": np.array([0.0, 0.0, 0.0]),
            "depth": np.array([50.0, 60.0, 70.0])}
    return {"id": "P001", "num": 1, "archivo": "slabP001.tmp", "lat_media": 0.0,
            "slab": slab, "topo_p": np.array([]), "topo_alt": np.array([])}


def test_abrir_eventos_crea_figura_y_enriquece(raiz_tk):
    plt.close("all")
    evento = {"latitud": 0.0, "longitud": 1.0, "prof": 60.0,
              "magnitud": 4.5, "tipo": "ML", "perfil": "P001"}

    plotear.abrir_eventos([evento], "seisan", perfiles=[_perfil()])

    assert plt.get_fignums()
    assert evento["perfil"] == "P001"
    assert evento["along_km"] is not None
    assert evento["perp_km"] is not None
    assert "sospechoso" in evento


def test_abrir_eventos_sin_coordenadas():
    with pytest.raises(ValueError):
        plotear.abrir_eventos([{"latitud": None, "longitud": None}], "seisan",
                              perfiles=[_perfil()])


def test_abrir_eventos_sin_prof_usa_planta(raiz_tk, monkeypatch):
    llamadas = []
    monkeypatch.setattr(plotear, "plotear_planta",
                        lambda *a, **k: llamadas.append("planta"))
    monkeypatch.setattr(plotear, "plotear_perfil",
                        lambda *a, **k: llamadas.append("perfil"))
    evento = {"latitud": 0.0, "longitud": 1.0, "prof": None, "perfil": "P001"}

    plotear.abrir_eventos([evento], "seisan", perfiles=[_perfil()])

    assert llamadas == ["planta"]


def test_abrir_evento_delega(monkeypatch):
    llamado = {}
    monkeypatch.setattr(
        plotear, "abrir_eventos",
        lambda eventos, fuente, perfiles=None:
            llamado.update(eventos=eventos, fuente=fuente, perfiles=perfiles))
    evento = {"latitud": 0.0, "longitud": 1.0, "prof": 60.0}

    plotear.abrir_evento(evento, "seisan", perfiles=[_perfil()])

    assert llamado["eventos"] == [evento]
    assert llamado["fuente"] == "seisan"


def test_abrir_comparacion_con_perfil(raiz_tk):
    plt.close("all")
    evento = {"latitud": 0.0, "longitud": 1.0, "prof": 60.0,
              "perfil": "P001", "agencias": []}

    plotear.abrir_comparacion(evento, "eventquery", perfiles=[_perfil()])

    assert plt.get_fignums()


def test_abrir_comparacion_sin_perfil(raiz_tk):
    plt.close("all")
    evento = {"latitud": 0.0, "longitud": 1.0, "prof": 60.0, "perfil": None}

    plotear.abrir_comparacion(evento, "seisan", perfiles=[_perfil()])

    assert plt.get_fignums()


def test_abrir_eventos_comparacion_titulo(raiz_tk):
    plt.close("all")
    local = {"latitud": 0.0, "longitud": 1.0, "prof": 60.0, "perfil": "P001",
             "rol": "local", "fecha hora": "2020-01-01 00:00:00"}
    publicado = {"latitud": 0.1, "longitud": 1.1, "prof": 65.0,
                 "rol": "publicado"}

    plotear.abrir_eventos([local, publicado], "eventquery",
                          perfiles=[_perfil()])

    assert plt.gcf()._suptitle.get_text() == "Comparación local vs publicado"
