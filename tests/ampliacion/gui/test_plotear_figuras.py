#!/usr/bin/env python3
"""
Tests de plotear.py — figuras (backend Agg)
===========================================
Cubre la construcción de figuras de `plotear_planta` y `plotear_perfil` con el
backend `Agg`, sin pantalla. No se cubre `abrir_eventos`/`abrir_evento` porque
usan `mgr.show()` (interactivo) y bajo Agg fallan; esas figuras se validan en el
flujo real de `gui/`/`verificacion/`.

Marcador `gui`: matplotlib/cartopy no están en el CI, así que el módulo se
saltea con `importorskip`.
"""

import contextlib
import warnings

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
def _backend_agg():
    # Agg: `plt.show()` no abre ventana ni bloquea (no-op con un warning).
    matplotlib.use("Agg", force=True)


@contextlib.contextmanager
def _silencio():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        yield


def _perfil():
    slab = {"p": np.array([0.0, 100.0, 200.0]),
            "lon": np.array([0.0, 1.0, 2.0]),
            "lat": np.array([0.0, 0.0, 0.0]),
            "depth": np.array([50.0, 60.0, 70.0])}
    return {"id": "P001", "num": 1, "archivo": "slabP001.tmp", "lat_media": 0.0,
            "slab": slab, "topo_p": np.array([]), "topo_alt": np.array([])}


_EVENTO = {"latitud": "0.0", "longitud": "1.0", "prof": "60.0",
           "magnitud": "4.5", "tipo": "ML", "fecha hora": "2020-01-01 00:00:00"}


def test_planta_crea_figura(cwd_tmp):
    plt.close("all")
    with _silencio():
        percibidos, total = plotear.plotear_planta([dict(_EVENTO)], "seisan",
                                                   bloquear=True)
    assert total == 1
    assert len(plt.get_fignums()) == 1
    plt.close("all")


def test_planta_cuenta_percibidos(cwd_tmp):
    plt.close("all")
    evento = dict(_EVENTO, id=1, percibido="S")
    with _silencio():
        percibidos, total = plotear.plotear_planta([evento], "eventquery",
                                                   bloquear=True)
    assert (percibidos, total) == (1, 1)
    plt.close("all")


def test_perfil_crea_figura(cwd_tmp):
    plt.close("all")
    with _silencio():
        plotear.plotear_perfil([dict(_EVENTO)], _perfil(), "seisan", 0,
                               bloquear=True)
    # Planta + perfil (y algún eje auxiliar): al menos dos.
    assert len(plt.gcf().axes) >= 2
    plt.close("all")
