#!/usr/bin/env python3
"""
Tests de descargas.py — avisos y carpeta (sin Tk real)
======================================================
Lo que **no** necesita una ventana real: los avisos por messagebox (que se
sustituye porque es modal/bloqueante), `abrir_carpeta` (lanza un explorador
externo) y la rama sin padre de `preguntar_formato`.

Lo que sí usa Tk real (`encima_de`, `_etiqueta_secundaria`, `descargar_tabla`,
`descargar_texto`) está en `tests/ampliacion/gui/test_descargas_widgets.py`.
"""

import sys
import types

import pytest

import descargas


class MessageboxFalso:
    def __init__(self):
        self.llamadas = []
        self.error = None

    def showerror(self, titulo, mensaje, parent=None):
        if self.error is not None:
            raise self.error
        self.llamadas.append(("showerror", titulo, mensaje, parent))

    def showinfo(self, titulo, mensaje, parent=None):
        if self.error is not None:
            raise self.error
        self.llamadas.append(("showinfo", titulo, mensaje, parent))


@pytest.fixture
def tkinter_falso(monkeypatch):
    mod = types.ModuleType("tkinter")
    mb = MessageboxFalso()
    mod.messagebox = mb
    monkeypatch.setitem(sys.modules, "tkinter", mod)
    return mb


# --------------------------------------------------------------------------
# _avisar_error / _avisar_exito (messagebox sustituido)
# --------------------------------------------------------------------------
def test_avisar_error(tkinter_falso):
    descargas._avisar_error(None, "no se pudo")
    tipo, titulo, mensaje, parent = tkinter_falso.llamadas[0]
    assert tipo == "showerror" and mensaje == "no se pudo" and parent is None


def test_avisar_exito(tkinter_falso, tmp_path):
    descargas._avisar_exito(None, str(tmp_path / "descargas" / "x.csv"))
    tipo, titulo, mensaje, _ = tkinter_falso.llamadas[0]
    assert tipo == "showinfo" and "x.csv" in mensaje


def test_avisar_error_fallback_consola(tkinter_falso, capsys):
    tkinter_falso.error = RuntimeError("sin display")
    descargas._avisar_error(None, "no se pudo")
    assert "[descargas] no se pudo" in capsys.readouterr().out


def test_avisar_exito_fallback_consola(tkinter_falso, capsys, tmp_path):
    tkinter_falso.error = RuntimeError("sin display")
    descargas._avisar_exito(None, str(tmp_path / "x.csv"))
    assert "[descargas]" in capsys.readouterr().out


# --------------------------------------------------------------------------
# abrir_carpeta (subprocess sustituido)
# --------------------------------------------------------------------------
def test_abrir_carpeta_inexistente(tmp_path):
    assert descargas.abrir_carpeta(str(tmp_path / "no_existe")) is False


def test_abrir_carpeta_linux(monkeypatch, tmp_path):
    llamadas = []
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(descargas.subprocess, "Popen",
                        lambda args: llamadas.append(args))
    assert descargas.abrir_carpeta(str(tmp_path)) is True
    assert llamadas == [["xdg-open", str(tmp_path)]]


def test_abrir_carpeta_mac(monkeypatch, tmp_path):
    llamadas = []
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(descargas.subprocess, "Popen",
                        lambda args: llamadas.append(args))
    assert descargas.abrir_carpeta(str(tmp_path)) is True
    assert llamadas == [["open", str(tmp_path)]]


def test_abrir_carpeta_falla(monkeypatch, tmp_path, capsys):
    def revienta(args):
        raise OSError("no hay explorador")

    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(descargas.subprocess, "Popen", revienta)
    assert descargas.abrir_carpeta(str(tmp_path)) is False
    assert "no se pudo abrir" in capsys.readouterr().out


# --------------------------------------------------------------------------
# preguntar_formato: rama sin display
# --------------------------------------------------------------------------
def test_preguntar_formato_sin_padre():
    assert descargas.preguntar_formato(None) is None
