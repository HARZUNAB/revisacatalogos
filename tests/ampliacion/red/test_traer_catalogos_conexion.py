#!/usr/bin/env python3
"""
Tests de red de traer_catalogos.py — clase Conexion
===================================================
Cubre la sesión SSH/SCP con `subprocess` mockeado: no se toca la red real.
Se verifican el armado de comandos, el entorno del ayudante askpass, el
log/progreso y el manejo de errores.

Marcador `red` (no se excluye del CI: es todo mock).
"""

import os
import shlex
import types

import pytest

import traer_catalogos as t

pytestmark = pytest.mark.red


class _PopenFalso:
    def __init__(self, args, kwargs, returncode, lineas):
        self.args = args
        self.kwargs = kwargs
        self.returncode = returncode
        self.stdout = iter([linea + "\n" for linea in lineas])

    def wait(self):
        return self.returncode


class _SubprocessFalso:
    """Reemplazo de `subprocess` con Popen/run controlados."""

    DEVNULL = object()
    PIPE = object()
    STDOUT = object()

    def __init__(self, returncode=0, lineas=(), salida=""):
        self.returncode = returncode
        self.lineas = lineas
        self.salida = salida
        self.popen = None
        self.run_args = None

    def Popen(self, args, **kwargs):
        self.popen = _PopenFalso(args, kwargs, self.returncode, self.lineas)
        return self.popen

    def run(self, args, **kwargs):
        self.run_args = (args, kwargs)
        return types.SimpleNamespace(returncode=self.returncode,
                                     stdout=self.salida)


def _conexion(monkeypatch, log=None, **kwargs):
    fake = _SubprocessFalso(**kwargs)
    monkeypatch.setattr(t, "subprocess", fake)
    conexion = t.Conexion("secreta", log=log)
    conexion._preparar()
    return conexion, fake


# --------------------------------------------------------------------------
# Básicos
# --------------------------------------------------------------------------
def test_remoto():
    assert t.Conexion("x")._remoto() == \
        "%s@%s" % (t.USUARIO_REMOTO, t.IP_REMOTA)


def test_entorno(monkeypatch):
    conexion, _ = _conexion(monkeypatch)
    try:
        env = conexion._entorno()
        assert env["RV_SSH_PASS"] == "secreta"
        assert env["SSH_ASKPASS"] == conexion._askpass
        assert env["SSH_ASKPASS_REQUIRE"] == "force"
    finally:
        conexion.cerrar()


# --------------------------------------------------------------------------
# Ayudante askpass
# --------------------------------------------------------------------------
def test_preparar_y_cerrar():
    conexion = t.Conexion("x")
    conexion._preparar()
    directorio = conexion._dir
    assert os.path.isdir(directorio)
    assert oct(os.stat(directorio).st_mode & 0o777) == oct(0o700)
    assert os.path.isfile(conexion._askpass)
    assert oct(os.stat(conexion._askpass).st_mode & 0o777) == oct(0o700)
    with open(conexion._askpass) as f:
        assert f.read() == "#!/bin/sh\nprintf '%s' \"$RV_SSH_PASS\"\n"
    conexion.cerrar()
    assert not os.path.isdir(directorio)
    conexion.cerrar()  # idempotente


def test_context_manager_limpia_el_ayudante():
    with t.Conexion("x") as conexion:
        directorio = conexion._dir
        assert os.path.isdir(directorio)
    assert not os.path.isdir(directorio)


# --------------------------------------------------------------------------
# _correr / _capturar
# --------------------------------------------------------------------------
def test_correr_devuelve_codigo_y_loguea(monkeypatch):
    logueado = []
    conexion, fake = _conexion(monkeypatch, log=logueado.append,
                               returncode=0, lineas=["hola", "mundo"])
    try:
        rc = conexion._correr(["ssh", "host", "cmd"])
    finally:
        conexion.cerrar()
    assert rc == 0
    assert fake.popen.args == ["ssh", "host", "cmd"]
    assert fake.popen.kwargs["env"]["RV_SSH_PASS"] == "secreta"
    assert "$ ssh host cmd" in logueado
    assert "hola" in logueado and "mundo" in logueado


def test_correr_oserror_revienta(monkeypatch):
    class _SubprocessFalla(_SubprocessFalso):
        def Popen(self, args, **kwargs):
            raise OSError("boom")

    monkeypatch.setattr(t, "subprocess", _SubprocessFalla())
    conexion = t.Conexion("x")
    conexion._preparar()
    try:
        with pytest.raises(RuntimeError):
            conexion._correr(["ssh"])
    finally:
        conexion.cerrar()


def test_capturar(monkeypatch):
    conexion, fake = _conexion(monkeypatch, returncode=0,
                               salida="/usr/bin/select\n")
    try:
        codigo, salida = conexion._capturar(["ssh"])
    finally:
        conexion.cerrar()
    assert (codigo, salida) == (0, "/usr/bin/select\n")
    assert fake.run_args[0] == ["ssh"]


# --------------------------------------------------------------------------
# ssh_login / resolver
# --------------------------------------------------------------------------
def test_ssh_login_arma_bash_lc(monkeypatch):
    conexion, fake = _conexion(monkeypatch, returncode=0)
    try:
        conexion.ssh_login("echo OK")
    finally:
        conexion.cerrar()
    args = fake.popen.args
    assert args[0] == "ssh"
    assert args[-2] == "%s@%s" % (t.USUARIO_REMOTO, t.IP_REMOTA)
    assert args[-1] == "bash -lc %s" % shlex.quote("echo OK")


def test_ssh_login_falla(monkeypatch):
    conexion, _ = _conexion(monkeypatch, returncode=1)
    try:
        with pytest.raises(RuntimeError):
            conexion.ssh_login("echo OK")
    finally:
        conexion.cerrar()


def test_resolver_toma_la_ultima_linea(monkeypatch):
    conexion, _ = _conexion(monkeypatch, returncode=0,
                            salida="ruido\n/usr/bin/select\n\n")
    try:
        assert conexion.resolver("select") == "/usr/bin/select"
    finally:
        conexion.cerrar()


def test_resolver_sin_resultado_falla(monkeypatch):
    conexion, _ = _conexion(monkeypatch, returncode=0, salida="\n   \n")
    try:
        with pytest.raises(RuntimeError):
            conexion.resolver("select")
    finally:
        conexion.cerrar()


def test_resolver_codigo_no_cero_falla(monkeypatch):
    conexion, _ = _conexion(monkeypatch, returncode=1,
                            salida="/usr/bin/select\n")
    try:
        with pytest.raises(RuntimeError):
            conexion.resolver("select")
    finally:
        conexion.cerrar()


# --------------------------------------------------------------------------
# subir / bajar
# --------------------------------------------------------------------------
def test_subir(monkeypatch):
    conexion, fake = _conexion(monkeypatch, returncode=0)
    try:
        conexion.subir("local.inp", "tmp/select.inp")
    finally:
        conexion.cerrar()
    args = fake.popen.args
    assert args[0] == "scp"
    assert args[-2] == "local.inp"
    assert args[-1] == "%s:tmp/select.inp" % conexion._remoto()


def test_subir_falla(monkeypatch):
    conexion, _ = _conexion(monkeypatch, returncode=1)
    try:
        with pytest.raises(RuntimeError):
            conexion.subir("local.inp", "tmp/select.inp")
    finally:
        conexion.cerrar()


def test_bajar(monkeypatch):
    conexion, fake = _conexion(monkeypatch, returncode=0)
    try:
        conexion.bajar("tmp/select.out", "local.out")
    finally:
        conexion.cerrar()
    args = fake.popen.args
    assert args[0] == "scp"
    assert args[-2] == "%s:tmp/select.out" % conexion._remoto()
    assert args[-1] == "local.out"


def test_bajar_falla(monkeypatch):
    conexion, _ = _conexion(monkeypatch, returncode=1)
    try:
        with pytest.raises(RuntimeError):
            conexion.bajar("tmp/select.out", "local.out")
    finally:
        conexion.cerrar()
