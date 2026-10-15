#!/usr/bin/env python3
"""
Tests de app.py — ventana principal
===================================
Cubre la construcción de la ventana principal, los grupos de botones, el toggle
"Forzar actualización", el gating (habilitar/deshabilitar), el tooltip y el
estado inicial. **Ventana real + estado dummy**: no corre el pipeline ni usa
mocks. Necesita `DISPLAY`.
"""

import pytest

pytestmark = pytest.mark.gui


def _textos(botones):
    return {b.cget("text") for b in botones}


# --------------------------------------------------------------------------
# Construcción
# --------------------------------------------------------------------------
def test_construccion(app_factory):
    raiz, inst = app_factory()
    assert raiz.title() == "Revisión de eventos · supervisor"
    assert tuple(raiz.minsize()) == (860, 600)
    assert inst.boton_analisis.cget("text") == "Procesar catálogos"


# --------------------------------------------------------------------------
# Grupos de botones
# --------------------------------------------------------------------------
def test_grupos_de_botones(app_factory):
    _, inst = app_factory()
    # No gated: la carpeta de descargas y salir.
    assert {"Abrir carpeta", "Salir"} <= _textos(inst.botones)
    # Gated por "análisis hecho": las ventanas de consulta.
    assert {"Catálogos", "Repetidos", "No publicados", "No actualizados",
            "Comparar agencias"} <= _textos(inst.botones_fuente)
    # Condiciones propias: los tres botones de re-exportar.
    assert len(inst.condiciones) == 3


# --------------------------------------------------------------------------
# Toggle "Forzar actualización"
# --------------------------------------------------------------------------
def test_toggle_forzar_actualizacion(app_factory):
    _, inst = app_factory()
    assert inst.forzar_actualizacion.get() is False
    inst.chk_forzar.invoke()
    assert inst.forzar_actualizacion.get() is True
    inst.chk_forzar.invoke()
    assert inst.forzar_actualizacion.get() is False


# --------------------------------------------------------------------------
# Ocupado / gating
# --------------------------------------------------------------------------
def test_set_ocupado_deshabilita_los_botones(app_factory):
    _, inst = app_factory()
    inst._set_ocupado(True)
    assert all(b.instate(["disabled"]) for b in inst.botones)
    inst._set_ocupado(False)
    assert all(not b.instate(["disabled"]) for b in inst.botones)


def test_puede_procesar(app_factory, cwd_tmp):
    _, inst = app_factory()
    assert inst._puede_procesar() is False
    (cwd_tmp / "entrada.csv").write_text("x", encoding="utf-8")
    assert inst._puede_procesar() is False        # falta select.out
    (cwd_tmp / "select.out").write_text("x", encoding="utf-8")
    assert inst._puede_procesar() is True


def test_gate_de_botones_fuente(app_factory):
    _, inst = app_factory()
    inst.analisis_hecho = False
    inst._actualizar_gate()
    assert all(b.instate(["disabled"]) for b in inst.botones_fuente)
    inst.analisis_hecho = True
    inst._actualizar_gate()
    assert all(not b.instate(["disabled"]) for b in inst.botones_fuente)


# --------------------------------------------------------------------------
# Tooltip
# --------------------------------------------------------------------------
def test_tooltip_enlaza_y_muestra_ayuda(app_factory):
    _, inst = app_factory()
    inst._tooltip(inst.boton_analisis, "motivo")
    assert inst.boton_analisis.bind("<Enter>")
    assert inst.boton_analisis.bind("<Leave>")

    inst._mostrar_ayuda(inst.boton_analisis, "texto de ayuda")
    assert inst._ayuda is not None
    widget, top = inst._ayuda
    assert widget is inst.boton_analisis
    assert top.winfo_exists()

    inst._ocultar_ayuda()
    assert inst._ayuda is None


# --------------------------------------------------------------------------
# Estado inicial
# --------------------------------------------------------------------------
def test_estado_inicial_con_faltantes(app_factory):
    _, inst = app_factory(estado={"inicio": "20260101000000",
                                  "fin": "20260131235959",
                                  "faltantes": ["SeisComp"]})
    assert inst.periodo == ("20260101000000", "20260131235959")
    assert inst.catalogos_faltantes == {"SeisComp"}
    # Quedó agendado el aviso de catálogos faltantes (la fixture lo cancela).
    assert inst._after_msg is not None
