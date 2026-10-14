#!/usr/bin/env python3
"""
Tests de prog.py
================
Cubre el protocolo de progreso `@@PROGRESO@@`: que solo emita con RV_PROG=1,
que recorte la fracción a [0, 1], que difumine (no repita el mismo paso) y que
`avance_reset` permita volver a emitir el mismo valor.
"""

import pytest

import prog


@pytest.fixture(autouse=True)
def _limpia_paso():
    """Cada test arranca sin último paso recordado."""
    prog.avance_reset()


def test_sin_rv_prog_no_emite(monkeypatch, capsys):
    monkeypatch.delenv("RV_PROG", raising=False)
    prog.avance(0.5)
    assert capsys.readouterr().out == ""


def test_con_rv_prog_emite_marcador(monkeypatch, capsys):
    monkeypatch.setenv("RV_PROG", "1")
    prog.avance(0.5)
    assert capsys.readouterr().out == "@@PROGRESO@@ 0.5000\n"


def test_emite_uno_y_cero(monkeypatch, capsys):
    monkeypatch.setenv("RV_PROG", "1")
    prog.avance(1.0)
    prog.avance_reset()
    prog.avance(0.0)
    salida = capsys.readouterr().out
    assert "@@PROGRESO@@ 1.0000" in salida
    assert "@@PROGRESO@@ 0.0000" in salida


def test_fraccion_se_recorta_al_rango(monkeypatch, capsys):
    monkeypatch.setenv("RV_PROG", "1")
    prog.avance(-1.0)
    prog.avance(2.0)
    salida = capsys.readouterr().out
    assert "@@PROGRESO@@ 0.0000" in salida
    assert "@@PROGRESO@@ 1.0000" in salida


def test_difumina_mismo_paso(monkeypatch, capsys):
    monkeypatch.setenv("RV_PROG", "1")
    prog.avance(0.5)
    prog.avance(0.5004)  # redondea al mismo paso (500)
    salida = capsys.readouterr().out
    assert salida.count("@@PROGRESO@@") == 1


def test_paso_distinto_si_emite(monkeypatch, capsys):
    monkeypatch.setenv("RV_PROG", "1")
    prog.avance(0.500)
    prog.avance(0.501)  # paso 501, distinto de 500
    salida = capsys.readouterr().out
    assert salida.count("@@PROGRESO@@") == 2


def test_avance_reset_permite_reemitir(monkeypatch, capsys):
    monkeypatch.setenv("RV_PROG", "1")
    prog.avance(0.5)
    capsys.readouterr()
    prog.avance_reset()
    prog.avance(0.5)
    assert capsys.readouterr().out == "@@PROGRESO@@ 0.5000\n"
