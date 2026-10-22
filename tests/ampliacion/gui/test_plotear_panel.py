#!/usr/bin/env python3
"""
Tests de plotear.py — panel de análisis y aviso «Sin datos»
==========================================================
Cubre `abrir_panel` (panel embebido con tabla de perfiles) y `_avisar_sin_datos`
(ventana «Sin datos») con **interfaz real** y datos sintéticos. Necesita
`DISPLAY` y backend interactivo (TkAgg).

`asigna_perfiles.detectar_perfiles` se monkeypatchea con un perfil sintético para
no depender de las grillas del repositorio.
"""

import json
import tkinter as tk
from tkinter import ttk

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
    # El panel necesita backend interactivo: contrarresta el Agg que deja
    # test_plotear_figuras.py (que corre antes).
    matplotlib.use("TkAgg", force=True)
    plotear._panel_activo = False
    plotear._fig_ancla = None
    plotear._TOP_AVISO = None
    yield
    try:
        if plotear._TOP_AVISO is not None:
            plotear._TOP_AVISO.destroy()
    except Exception:
        pass
    plotear._panel_activo = False
    plotear._fig_ancla = None
    plotear._TOP_AVISO = None
    plt.close("all")


def _buscar(widget, tipo, predicado=None):
    for hijo in widget.winfo_children():
        if isinstance(hijo, tipo) and (predicado is None or predicado(hijo)):
            return hijo
        encontrado = _buscar(hijo, tipo, predicado)
        if encontrado is not None:
            return encontrado
    return None


def _contenedor(raiz):
    marco = ttk.Frame(raiz)
    marco.pack()
    return marco


def _perfil(pid="P001", num=1):
    slab = {"p": np.array([0.0, 100.0, 200.0]),
            "lon": np.array([0.0, 1.0, 2.0]),
            "lat": np.array([0.0, 0.0, 0.0]),
            "depth": np.array([50.0, 60.0, 70.0])}
    return {"id": pid, "num": num, "archivo": "slab%s.tmp" % pid,
            "lat_media": 0.0, "slab": slab, "topo_p": np.array([]),
            "topo_alt": np.array([])}


def _evento(perfil="P001", **extra):
    ev = {"id": 1, "fecha hora": "2020-01-01 00:00:00", "latitud": "0.0",
          "longitud": "1.0", "prof": "60.0", "magnitud": "4.5", "tipo": "ML",
          "perfil": perfil, "along_km": 100.0, "perp_km": 5.0,
          "sospechoso": False, "percibido": "N"}
    ev.update(extra)
    return ev


def _top_sin_datos(raiz):
    for widget in raiz.winfo_children():
        if isinstance(widget, tk.Toplevel) and widget.title() == "Sin datos":
            return widget
    return None


def _tops_mapas(raiz):
    return [widget for widget in raiz.winfo_children()
            if isinstance(widget, tk.Toplevel)
            and widget.title().startswith("Mapas sin perfil")]


# --------------------------------------------------------------------------
# abrir_panel
# --------------------------------------------------------------------------
def test_abrir_panel_real(raiz_tk, cwd_tmp, monkeypatch):
    import asigna_perfiles as ap
    monkeypatch.setattr(ap, "detectar_perfiles", lambda *a, **k: [_perfil()])
    eventos = [_evento("P001"), _evento("P001", sospechoso=True),
               _evento(None), _evento("P999")]
    archivo = cwd_tmp / "eventos_seisan.json"
    archivo.write_text(json.dumps(eventos), encoding="utf-8")
    contenedor = _contenedor(raiz_tk)

    ok = plotear.abrir_panel(contenedor, str(archivo), "seisan")

    assert ok is True
    arbol = _buscar(contenedor, ttk.Treeview)
    assert arbol is not None
    filas = arbol.get_children()
    # Solo P001 tiene perfil disponible; el sin-perfil y el huérfano no van.
    assert len(filas) == 1
    assert arbol.item(filas[0], "values")[1] == "P001"


def test_abrir_panel_sin_archivo(raiz_tk, cwd_tmp):
    contenedor = _contenedor(raiz_tk)
    assert plotear.abrir_panel(contenedor, None, "seisan") is False
    assert plotear.abrir_panel(contenedor, str(cwd_tmp / "no.json"),
                               "seisan") is False


def test_abrir_panel_sin_perfiles(raiz_tk, cwd_tmp, monkeypatch):
    import asigna_perfiles as ap
    monkeypatch.setattr(ap, "detectar_perfiles", lambda *a, **k: [])
    archivo = cwd_tmp / "eventos_seisan.json"
    archivo.write_text(json.dumps([_evento("P001")]), encoding="utf-8")
    contenedor = _contenedor(raiz_tk)

    assert plotear.abrir_panel(contenedor, str(archivo), "seisan") is False


def test_mapas_sin_perfil_se_pueden_reabrir(raiz_tk, cwd_tmp, monkeypatch):
    import asigna_perfiles as ap
    monkeypatch.setattr(ap, "detectar_perfiles", lambda *a, **k: [_perfil()])
    monkeypatch.setattr(plotear, "_mini_mapa_territorio",
                        lambda *a, **k: True)
    eventos = [
        _evento("P001"),
        _evento(None, id=2, latitud="-33.0", longitud="-71.0"),
    ]
    archivo = cwd_tmp / "eventos_seisan.json"
    archivo.write_text(json.dumps(eventos), encoding="utf-8")
    contenedor = _contenedor(raiz_tk)

    assert plotear.abrir_panel(contenedor, str(archivo), "seisan") is True
    boton = _buscar(contenedor, ttk.Button,
                    lambda w: w.cget("text") == "Mapas sin perfil")
    assert boton is not None
    raiz_mapa = plotear._raiz_tk()
    assert raiz_mapa is not None

    boton.invoke()
    raiz_mapa.update()
    primeros = _tops_mapas(raiz_mapa)
    assert len(primeros) == 1

    primeros[0]._cerrar()
    raiz_mapa.update()
    assert _tops_mapas(raiz_mapa) == []

    boton.invoke()
    raiz_mapa.update()
    segundos = _tops_mapas(raiz_mapa)
    assert len(segundos) == 1
    assert segundos[0] is not primeros[0]

    segundos[0]._cerrar()


# --------------------------------------------------------------------------
# _avisar_sin_datos
# --------------------------------------------------------------------------
def test_avisar_sin_datos_crea_ventana(raiz_tk):
    plotear._avisar_sin_datos("nada para plotear", raiz_tk)

    top = _top_sin_datos(raiz_tk)
    assert top is not None
    etiqueta = _buscar(top, tk.Label)
    assert etiqueta is not None
    assert etiqueta.cget("text") == "nada para plotear"
    boton = _buscar(top, tk.Button)
    assert boton is not None
    assert boton.cget("text") == "Aceptar"


def test_avisar_sin_datos_una_sola_ventana(raiz_tk):
    plotear._avisar_sin_datos("primero", raiz_tk)
    primero = _top_sin_datos(raiz_tk)
    plotear._avisar_sin_datos("segundo", raiz_tk)

    tops = [w for w in raiz_tk.winfo_children()
            if isinstance(w, tk.Toplevel) and w.title() == "Sin datos"]
    assert len(tops) == 1
    assert tops[0] is primero
    # La segunda llamada trae al frente la existente, no la recrea.
    assert _buscar(primero, tk.Label).cget("text") == "primero"


def test_avisar_sin_datos_aceptar_cierra(raiz_tk):
    plotear._avisar_sin_datos("algo", raiz_tk)
    boton = _buscar(_top_sin_datos(raiz_tk), tk.Button)
    boton.invoke()
    raiz_tk.update_idletasks()

    assert plotear._TOP_AVISO is None
    assert _top_sin_datos(raiz_tk) is None



def test_panel_no_actualizados_filtra_alta_prioridad(raiz_tk, cwd_tmp,
                                                    monkeypatch):
    import asigna_perfiles as ap
    monkeypatch.setattr(ap, "detectar_perfiles",
                        lambda *a, **k: [_perfil("P001", 1),
                                         _perfil("P002", 2)])
    eventos = [
        _evento("P001", revision="Alta", publicacion_probable="Esta fuente"),
        _evento("P002", revision="Baja", publicacion_probable="Otra fuente"),
    ]
    archivo = cwd_tmp / "eventos_seiscomp_noact.json"
    archivo.write_text(json.dumps(eventos), encoding="utf-8")
    contenedor = _contenedor(raiz_tk)

    assert plotear.abrir_panel(contenedor, str(archivo), "seiscomp",
                               vista="seiscomp_noact") is True
    arbol = _buscar(contenedor, ttk.Treeview)
    assert len(arbol.get_children()) == 2
    boton = _buscar(contenedor, ttk.Button,
                    lambda w: w.cget("text") == "Solo alta prioridad")
    assert boton is not None
    assert _buscar(contenedor, ttk.Button,
                   lambda w: w.cget("text") == "Criterios de clasificación") is not None

    llamado = []
    monkeypatch.setattr(plotear.descargas, "mostrar_texto_mono",
                        lambda *a, **k: llamado.append(a))
    ayuda = _buscar(contenedor, ttk.Button,
                    lambda w: w.cget("text") == "Criterios de clasificación")
    ayuda.invoke()
    assert llamado
    assert llamado[0][1] == "Clasificación de No actualizados"
    assert llamado[0][2] == plotear.cruce_noact.AYUDA_REVISION_NO_ACTUALIZADOS

    boton.invoke()
    raiz_tk.update()
    assert len(arbol.get_children()) == 1
    assert arbol.item(arbol.get_children()[0], "values")[1] == "P001"

    inicio = _buscar(contenedor, ttk.Button,
                     lambda w: w.cget("text") == "Inicio")
    inicio.invoke()
    raiz_tk.update()
    assert len(arbol.get_children()) == 2
