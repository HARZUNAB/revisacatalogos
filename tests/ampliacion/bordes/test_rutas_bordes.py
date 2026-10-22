#!/usr/bin/env python3
"""
Tests de bordes de rutas.py
===========================
Casos borde del descarte y de las rutas que el test base no cubre: escrituras
no-string, nombres con separador de directorio, truncado y rutas vacías.

El módulo no se modifica en esta tanda.
"""

import os

import pytest

import rutas


# --------------------------------------------------------------------------
# TextoDescartado
# --------------------------------------------------------------------------
def test_descarte_tolera_falsy_y_revienta_con_no_string():
    d = rutas.TextoDescartado()
    assert d.write(None) == 0
    assert d.write(0) == 0
    with pytest.raises(TypeError):
        d.write(123)


# --------------------------------------------------------------------------
# entregable
# --------------------------------------------------------------------------
def test_entregable_con_subcarpeta_revienta(cwd_tmp, con_entregables):
    # p_descargas crea descargas/, pero no subcarpetas del nombre.
    with pytest.raises(FileNotFoundError):
        rutas.entregable("sub/x.txt")


def test_entregable_trunca_el_existente(cwd_tmp, con_entregables):
    ruta = rutas.entregable("si.txt")
    ruta.write("viejo")
    ruta.close()
    ruta = rutas.entregable("si.txt")
    ruta.write("nuevo")
    ruta.close()
    with open(os.path.join(str(cwd_tmp), "descargas", "si.txt")) as f:
        assert f.read() == "nuevo"


# --------------------------------------------------------------------------
# p_* con nombres vacíos o con subcarpeta
# --------------------------------------------------------------------------
def test_p_datos_nombre_vacio(cwd_tmp):
    assert rutas.p_datos("") == os.path.join("datos", "")


def test_p_datos_con_subcarpeta_no_la_crea(cwd_tmp):
    ruta = rutas.p_datos("sub/x.csv")
    assert ruta == os.path.join("datos", "sub", "x.csv")
    assert not os.path.isdir(os.path.join(str(cwd_tmp), "datos", "sub"))


# --------------------------------------------------------------------------
# asegurar_dirs
# --------------------------------------------------------------------------
def test_asegurar_dirs_es_idempotente(cwd_tmp):
    rutas.asegurar_dirs()
    rutas.asegurar_dirs()
    for d in rutas.DIRS:
        assert os.path.isdir(os.path.join(str(cwd_tmp), d))


# --------------------------------------------------------------------------
# csv_tiene_filas
# --------------------------------------------------------------------------
def test_csv_tiene_filas_con_datos(cwd_tmp):
    ruta = os.path.join(str(cwd_tmp), "con.csv")
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(",Fecha_Hora,Latitud\n0,2026-01-01,-33.0\n")
    assert rutas.csv_tiene_filas(ruta) is True


def test_csv_tiene_filas_solo_encabezado(cwd_tmp):
    ruta = os.path.join(str(cwd_tmp), "vacio.csv")
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(",Fecha_Hora,Latitud\n")
    assert rutas.csv_tiene_filas(ruta) is False


def test_csv_tiene_filas_inexistente(tmp_path):
    assert rutas.csv_tiene_filas(str(tmp_path / "no_existe.csv")) is False
