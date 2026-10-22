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

import cartopy.crs as ccrs  # noqa: E402
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

    plotear.abrir_eventos([local, publicado], "seisan",
                          perfiles=[_perfil()])

    assert plt.gcf()._suptitle.get_text() == "Comparación Seisan vs publicado"


def _figura_embebida(raiz):
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from tkinter import ttk as _ttk

    marco = _ttk.Frame(raiz)
    fig = Figure(figsize=(4.2, 3.4), dpi=82)
    FigureCanvasTkAgg(fig, master=marco)
    return fig


def test_dibujar_mini_evento_con_perfil(raiz_tk, monkeypatch):
    monkeypatch.setattr(plotear, "_perfiles_cacheados", lambda: [_perfil()])
    fig = _figura_embebida(raiz_tk)
    evento = {"latitud": 0.0, "longitud": 1.0, "prof": 60.0,
              "perfil": "P001"}

    assert plotear.dibujar_mini_evento(fig, evento, "seisan") is True
    assert evento["along_km"] is not None
    assert "sospechoso" in evento


def test_dibujar_mini_evento_sin_perfil(raiz_tk, monkeypatch):
    monkeypatch.setattr(plotear, "_perfiles_cacheados", lambda: [])
    fig = _figura_embebida(raiz_tk)
    evento = {"latitud": None, "longitud": None, "prof": None}

    assert plotear.dibujar_mini_evento(fig, evento, "seisan") is False


def test_dibujar_mini_evento_con_hist(raiz_tk, monkeypatch):
    monkeypatch.setattr(plotear, "_perfiles_cacheados", lambda: [_perfil()])
    fig = _figura_embebida(raiz_tk)
    evento = {"latitud": 0.0, "longitud": 1.0, "prof": 60.0,
              "perfil": "P001"}

    # Con sismicidad histórica: usa el mismo camino del panel de análisis.
    assert plotear.dibujar_mini_evento(fig, evento, "seisan",
                                       mostrar_hist=True) is True


def test_extent_nacional_usa_margen_simetrico():
    extent = plotear._extent_planta_por_eventos(
        [{"latitud": -33.0, "longitud": -71.0}],
        territorio="Nacional",
        margen_adicional=plotear.MARGEN_MINI_MAPA_NACIONAL)

    assert extent == pytest.approx((-80.0, -63.0, -59.0, -14.5))


def test_dibujar_mini_mapa_evento_usa_nacional_y_margen(raiz_tk,
                                                        monkeypatch):
    fig = _figura_embebida(raiz_tk)
    llamado = {}

    def falso(ax, nombre, eventos, fuente, margen_adicional=None):
        llamado.update(nombre=nombre, eventos=eventos, fuente=fuente,
                       margen=margen_adicional)
        return True

    monkeypatch.setattr(plotear, "_mini_mapa_territorio", falso)
    evento = {"latitud": -33.0, "longitud": -71.0}

    assert plotear.dibujar_mini_mapa_evento(fig, evento, "seisan") is True
    assert llamado["nombre"] == "Nacional"
    assert llamado["eventos"] == [evento]
    assert llamado["fuente"] == "seisan"
    assert llamado["margen"] == plotear.MARGEN_MINI_MAPA_NACIONAL


def test_dibujar_mini_mapa_evento_dibuja(raiz_tk):
    fig = _figura_embebida(raiz_tk)

    assert plotear.dibujar_mini_mapa_evento(
        fig, {"latitud": -33.0, "longitud": -71.0}, "seisan") is True
    assert fig.axes


def test_dibujar_mini_mapa_evento_sin_coordenadas(raiz_tk):
    fig = _figura_embebida(raiz_tk)

    assert plotear.dibujar_mini_mapa_evento(
        fig, {"latitud": None, "longitud": None}, "seisan") is False


def test_zoom_mapa_nacional(raiz_tk):
    fig = _figura_embebida(raiz_tk)
    evento = {"latitud": -33.0, "longitud": -71.0}
    assert plotear.dibujar_mini_mapa_evento(fig, evento, "seisan") is True
    extent = plotear.extent_mapa_nacional(evento)
    control = plotear.conectar_zoom_mapa(
        fig, extent, centro=(evento["longitud"], evento["latitud"]))
    ax = fig.axes[-1]

    def actual():
        return ax.get_extent(crs=ccrs.PlateCarree())

    inicial = actual()
    control["zoom_in"]()
    acercado = actual()
    assert (acercado[1] - acercado[0]) < (inicial[1] - inicial[0])

    control["mover"](0.2, 0.1)
    movido = actual()
    assert movido != pytest.approx(acercado)

    control["centrar"]()
    centrado = actual()
    assert (centrado[0] + centrado[1]) / 2.0 == pytest.approx(
        evento["longitud"])
    assert (centrado[2] + centrado[3]) / 2.0 == pytest.approx(
        evento["latitud"])
    assert (centrado[1] - centrado[0]) == pytest.approx(
        movido[1] - movido[0])

    for _ in range(20):
        control["mover"](1.0, 1.0)
    limite = actual()
    assert limite[0] >= inicial[0] - 1e-9
    assert limite[1] <= inicial[1] + 1e-9
    assert limite[2] >= inicial[2] - 1e-9
    assert limite[3] <= inicial[3] + 1e-9

    for _ in range(20):
        control["zoom_out"]()
    alejado = actual()
    assert (alejado[1] - alejado[0]) == pytest.approx(
        inicial[1] - inicial[0])

    control["reset"]()
    assert actual() == pytest.approx(inicial)

    nuevo = plotear.extent_mapa_nacional(
        {"latitud": -20.0, "longitud": -70.0})
    control["actualizar"](nuevo, (-70.0, -20.0))
    assert actual() == pytest.approx(nuevo)
