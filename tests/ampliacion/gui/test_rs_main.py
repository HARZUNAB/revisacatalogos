#!/usr/bin/env python3
"""
Tests de revisa_seiscomp.py — main (ramas CLI)
==============================================
Cubre las ramas de `main()` que retornan **antes** de crear la ventana: `--help`,
`--catalogo` sin ruta y "no hay CSV de SeisComp". La rama que abre el panel crea
su propia raíz Tk y entra en `mainloop()`, así que queda para `verificacion/`
(end-to-end). Marcador `gui`.
"""

import sys

import pytest

import revisa_seiscomp as rs

pytestmark = pytest.mark.gui


def test_main_help(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["revisa_seiscomp.py", "--help"])
    assert rs.main() == 0
    assert "revisa_seiscomp" in capsys.readouterr().out


def test_main_catalogo_sin_ruta(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["revisa_seiscomp.py", "--catalogo"])
    assert rs.main() == 2
    assert "--catalogo necesita" in capsys.readouterr().out


def test_main_sin_csv(monkeypatch, capsys, cwd_tmp):
    monkeypatch.setattr(sys, "argv", ["revisa_seiscomp.py"])
    assert rs.main() == 1
    assert "No hay CSV de SeisComp" in capsys.readouterr().out
