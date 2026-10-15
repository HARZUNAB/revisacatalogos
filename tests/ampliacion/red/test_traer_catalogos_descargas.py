#!/usr/bin/env python3
"""
Tests de red de traer_catalogos.py — descargas
==============================================
Cubre la orquestación de `verificar_conexion`, `traer_seisan` y
`traer_eventquery` con una `Conexion` falsa que registra las llamadas (sin red).

Marcador `red` (no se excluye del CI: es todo mock).
"""

import pytest

import traer_catalogos as t

pytestmark = pytest.mark.red

_PLANTILLA = (b"Start time                 : 20200101000000\n"
              b"End time                   : 20200102000000\n")


class ConexionFalsa:
    """Registra las llamadas; `bajar` crea el destino como la bajada real."""

    def __init__(self):
        self.llamadas = []
        self.rutas = {"select": "/usr/bin/select",
                      "eventquery2": "/usr/bin/eventquery2"}

    def resolver(self, nombre):
        self.llamadas.append(("resolver", nombre))
        return self.rutas[nombre]

    def ssh_login(self, comando):
        self.llamadas.append(("ssh_login", comando))

    def subir(self, local, remoto):
        self.llamadas.append(("subir", local, remoto))

    def bajar(self, remoto, local):
        self.llamadas.append(("bajar", remoto, local))
        with open(local, "w") as f:
            f.write("bajado")


def _plantilla(monkeypatch, tmp_path):
    ruta = tmp_path / "select.inp"
    ruta.write_bytes(_PLANTILLA)
    monkeypatch.setattr(t, "PLANTILLA", str(ruta))


# --------------------------------------------------------------------------
# verificar_conexion
# --------------------------------------------------------------------------
def test_verificar_conexion():
    conexion = ConexionFalsa()
    logueado = []
    pasos = []
    t.verificar_conexion(conexion, log=logueado.append, progreso=pasos.append)
    assert ("ssh_login", "echo OK") in conexion.llamadas
    assert pasos == [0.1, 1.0]
    assert any("Conectando" in linea for linea in logueado)


# --------------------------------------------------------------------------
# traer_seisan
# --------------------------------------------------------------------------
def test_traer_seisan_sin_reuso(monkeypatch, tmp_path):
    _plantilla(monkeypatch, tmp_path)
    conexion = ConexionFalsa()
    pasos = []
    ini, fin = "20260301000000", "20260302000000"

    destino = t.traer_seisan(ini, fin, conexion, cwd=str(tmp_path),
                             progreso=pasos.append)

    assert destino == str(tmp_path / ("select_%s_%s.out" % (ini, fin)))
    assert [c[0] for c in conexion.llamadas] == \
        ["resolver", "ssh_login", "subir", "ssh_login", "bajar"]
    assert conexion.llamadas[0] == ("resolver", "select")
    assert conexion.llamadas[1] == ("ssh_login", "mkdir -p tmp")
    comando = conexion.llamadas[3][1]
    assert comando.startswith("cd tmp && ")
    assert "select_%s_%s.out" % (ini, fin) in comando
    assert conexion.llamadas[4] == (
        "bajar", "tmp/select_%s_%s.out" % (ini, fin), destino)
    # El .inp local solo servía para subirlo: se borra.
    assert not (tmp_path / "trabajo" / "select.inp").exists()
    assert pasos[0] == 0.1 and pasos[-1] == 1.0


def test_traer_seisan_forzar_rebaja(monkeypatch, tmp_path):
    _plantilla(monkeypatch, tmp_path)
    ini, fin = "20260301000000", "20260302000000"
    (tmp_path / ("select_%s_%s.out" % (ini, fin))).write_text("viejo")
    conexion = ConexionFalsa()

    t.traer_seisan(ini, fin, conexion, cwd=str(tmp_path), forzar=True)

    # Con forzar no reusa: consulta al servidor igual.
    assert ("resolver", "select") in conexion.llamadas


# --------------------------------------------------------------------------
# traer_eventquery
# --------------------------------------------------------------------------
def test_traer_eventquery_sin_reuso(tmp_path):
    conexion = ConexionFalsa()
    pasos = []
    ini, fin = "20260301000000", "20260302000000"

    destino = t.traer_eventquery(ini, fin, conexion, cwd=str(tmp_path),
                                 progreso=pasos.append)

    assert destino == str(tmp_path / ("eventquery_%s_%s.csv" % (ini, fin)))
    assert [c[0] for c in conexion.llamadas] == \
        ["resolver", "ssh_login", "ssh_login", "bajar"]
    assert conexion.llamadas[0] == ("resolver", "eventquery2")
    assert conexion.llamadas[1] == ("ssh_login", "mkdir -p tmp")
    comando = conexion.llamadas[2][1]
    assert "--start-time" in comando and t.a_iso(ini) in comando
    assert "--end-time" in comando and t.a_iso(fin) in comando
    assert conexion.llamadas[3] == (
        "bajar", "tmp/eventquery_%s_%s.csv" % (ini, fin), destino)
    assert pasos[0] == 0.15 and pasos[-1] == 1.0


def test_traer_eventquery_forzar_rebaja(tmp_path):
    ini, fin = "20260301000000", "20260302000000"
    (tmp_path / ("eventquery_%s_%s.csv" % (ini, fin))).write_text("viejo")
    conexion = ConexionFalsa()

    t.traer_eventquery(ini, fin, conexion, cwd=str(tmp_path), forzar=True)

    assert ("resolver", "eventquery2") in conexion.llamadas
