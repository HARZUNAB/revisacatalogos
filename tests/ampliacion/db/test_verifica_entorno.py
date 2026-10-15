#!/usr/bin/env python3
"""
Tests de verifica_entorno.py
============================
Cubre las comprobaciones del entorno con `psycopg2` mockeado y las funciones
inyectables: lectura de requirements, comparación de versiones, venv, base de
datos (con sus distintos avisos) e informe/main.

Marcador `db` (excluido del CI: no hay PostgreSQL en integración).
"""

import sys

import pytest

import verifica_entorno as ve

pytestmark = pytest.mark.db

CONFIG = {"user": "u", "host": "h", "database": "d", "password": "p"}


# --------------------------------------------------------------------------
# _pedidos / verificar_requirements
# --------------------------------------------------------------------------
def test_pedidos(tmp_path):
    req = tmp_path / "req.txt"
    req.write_text("pytest==7.4.4\n"
                   "numpy>=1.19  # comentario\n"
                   "\n"
                   "foo\n", encoding="utf-8")
    pedidos = ve._pedidos(str(req))
    assert pedidos["pytest"] == "7.4.4"
    assert pedidos["numpy"] is None
    assert pedidos["foo"] is None


def test_pedidos_archivo_inexistente():
    assert ve._pedidos("/no/existe/req.txt") == {}


def test_verificar_requirements(monkeypatch, tmp_path):
    req = tmp_path / "req.txt"
    req.write_text("pytest==7.4.4\nnumpy==1.19.5\n", encoding="utf-8")
    monkeypatch.setattr(ve, "_version_instalada",
                        lambda nombre: {"pytest": "7.4.4",
                                        "numpy": "1.20.0"}.get(nombre))
    r = ve.verificar_requirements(str(req))
    assert r["ok"] is False
    assert any("numpy" in d for d in r["distintas"])


def test_verificar_requirements_faltante(monkeypatch, tmp_path):
    req = tmp_path / "req.txt"
    req.write_text("pytest==7.4.4\n", encoding="utf-8")
    monkeypatch.setattr(ve, "_version_instalada", lambda nombre: None)
    r = ve.verificar_requirements(str(req))
    assert r["ok"] is False
    assert r["faltantes"] == ["pytest"]


def test_verificar_requirements_ok(monkeypatch, tmp_path):
    req = tmp_path / "req.txt"
    req.write_text("pytest==7.4.4\n", encoding="utf-8")
    monkeypatch.setattr(ve, "_version_instalada", lambda nombre: "7.4.4")
    assert ve.verificar_requirements(str(req))["ok"] is True


# --------------------------------------------------------------------------
# verificar_venv
# --------------------------------------------------------------------------
def test_verificar_venv_dentro(monkeypatch):
    monkeypatch.setattr(ve.sys, "prefix", "/venv")
    monkeypatch.setattr(ve.sys, "base_prefix", "/usr")
    assert ve.verificar_venv()["ok"] is True


def test_verificar_venv_fuera(monkeypatch):
    monkeypatch.setattr(ve.sys, "prefix", "/usr")
    monkeypatch.setattr(ve.sys, "base_prefix", "/usr")
    r = ve.verificar_venv()
    assert r["ok"] is False
    assert "NO es un entorno virtual" in r["detalle"]


# --------------------------------------------------------------------------
# verificar_base
# --------------------------------------------------------------------------
def test_verificar_base_ok(psycopg2_falso):
    class Conn:
        def close(self):
            pass

    psycopg2_falso.conexion = Conn()
    assert ve.verificar_base(config=CONFIG)["ok"] is True


def test_verificar_base_pg_hba(psycopg2_falso):
    psycopg2_falso.error_conectar = Exception("pg_hba.conf rejects connection")
    r = ve.verificar_base(config=CONFIG)
    assert r["ok"] is False
    assert "permisos" in r["aviso"]


def test_verificar_base_dns(psycopg2_falso):
    psycopg2_falso.error_conectar = Exception("could not translate host name")
    r = ve.verificar_base(config=CONFIG)
    assert r["ok"] is False
    assert "resolver" in r["aviso"]


def test_verificar_base_no_existe(psycopg2_falso):
    psycopg2_falso.error_conectar = Exception('database "x" does not exist')
    r = ve.verificar_base(config=CONFIG)
    assert r["ok"] is False
    assert "no existe" in r["aviso"]


def test_verificar_base_sin_psycopg2(monkeypatch):
    monkeypatch.setitem(sys.modules, "psycopg2", None)
    r = ve.verificar_base(config=CONFIG)
    assert r["ok"] is False
    assert "psycopg2" in r["detalle"]


# --------------------------------------------------------------------------
# informe / main
# --------------------------------------------------------------------------
def test_informe(monkeypatch):
    monkeypatch.setattr(ve, "verificar_venv",
                        lambda: {"ok": True, "titulo": "v", "detalle": "",
                                 "aviso": ""})
    monkeypatch.setattr(ve, "verificar_requirements",
                        lambda: {"ok": False, "titulo": "r", "detalle": "",
                                 "aviso": "falta"})
    monkeypatch.setattr(ve, "verificar_tkinter",
                        lambda: {"ok": True, "titulo": "t", "detalle": "",
                                 "aviso": ""})
    monkeypatch.setattr(ve, "verificar_base",
                        lambda: {"ok": True, "titulo": "b", "detalle": "",
                                 "aviso": ""})
    res = ve.informe()
    assert res["faltan"] == ["requisitos"]
    assert res["ok"] is False


def test_main_ok(monkeypatch, capsys):
    monkeypatch.setattr(ve, "informe", lambda: {
        "revisiones": [("venv", {"ok": True, "titulo": "Entorno",
                                 "detalle": "ok", "aviso": ""})],
        "faltan": [], "ok": True})
    assert ve.main() == 0
    assert "Todo lo necesario" in capsys.readouterr().out


def test_main_falta(monkeypatch, capsys):
    monkeypatch.setattr(ve, "informe", lambda: {
        "revisiones": [("base", {"ok": False, "titulo": "Base",
                                 "detalle": "no", "aviso": "aviso"})],
        "faltan": ["base"], "ok": False})
    assert ve.main() == 1
    assert "Falta resolver: base" in capsys.readouterr().out
