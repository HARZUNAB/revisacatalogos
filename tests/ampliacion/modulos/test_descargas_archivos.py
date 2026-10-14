#!/usr/bin/env python3
"""
Tests de descargas.py — nombres y escritura de archivos
=======================================================
Cubre la parte sin interfaz de `descargas.py`: la carpeta de descargas, la
construcción de nombres únicos, la escritura de tablas (CSV con BOM, TXT con
tab) y la lectura de informes de texto.

El `datetime` del módulo se congela con una fixture para que los nombres sean
predecibles.
"""

import csv
import datetime as _dt
import os

import pytest

import descargas


class _FechaFija:
    """Reemplazo de `datetime` con `now()` fijo, para nombres reproducibles."""

    @staticmethod
    def now():
        return _dt.datetime(2026, 1, 2, 3, 4, 5)


@pytest.fixture
def fecha_fija(monkeypatch):
    monkeypatch.setattr(descargas, "datetime", _FechaFija)


# --------------------------------------------------------------------------
# Carpetas
# --------------------------------------------------------------------------
def test_carpeta_crea_descargas(tmp_path):
    destino = descargas._carpeta(str(tmp_path))
    assert destino == os.path.join(str(tmp_path), "descargas")
    assert os.path.isdir(destino)


def test_carpeta_descargas_usa_cwd(cwd_tmp):
    assert descargas.carpeta_descargas() == os.path.join(str(cwd_tmp), "descargas")


def test_carpeta_descargas_acepta_cwd(tmp_path):
    assert descargas.carpeta_descargas(str(tmp_path)) == \
        os.path.join(str(tmp_path), "descargas")


# --------------------------------------------------------------------------
# nombre_descarga
# --------------------------------------------------------------------------
def test_nombre_descarga_normaliza_la_etiqueta(fecha_fija, cwd_tmp):
    ruta = descargas.nombre_descarga("Listado Raro!", "csv")
    assert os.path.basename(ruta) == "listadoraro_20260102030405.csv"
    assert os.path.dirname(ruta) == os.path.join(str(cwd_tmp), "descargas")


def test_nombre_descarga_extension_invalida_cae_a_csv(fecha_fija, cwd_tmp):
    ruta = descargas.nombre_descarga("x", "pdf")
    assert ruta.endswith(".csv")


def test_nombre_descarga_etiqueta_vacia(fecha_fija, cwd_tmp):
    ruta = descargas.nombre_descarga("", "csv")
    assert os.path.basename(ruta) == "descarga_20260102030405.csv"


def test_nombre_descarga_agrega_correlativo_si_existe(fecha_fija, cwd_tmp):
    ruta1 = descargas.nombre_descarga("tabla", "csv")
    open(ruta1, "w").close()
    ruta2 = descargas.nombre_descarga("tabla", "csv")
    assert ruta2 != ruta1
    assert os.path.basename(ruta2) == "tabla_20260102030405_2.csv"


# --------------------------------------------------------------------------
# escritura de tablas
# --------------------------------------------------------------------------
def test_escribir_filas_csv_con_bom_y_quoting(tmp_path):
    ruta = str(tmp_path / "t.csv")
    descargas.escribir_filas(ruta, ["a", "b"], [[1, "x,y"]], "csv")
    datos = open(ruta, "rb").read()
    assert datos.startswith(b"\xef\xbb\xbf")  # BOM utf-8-sig
    with open(ruta, encoding="utf-8-sig", newline="") as f:
        filas = list(csv.reader(f))
    assert filas == [["a", "b"], ["1", "x,y"]]


def test_escribir_filas_txt_sin_bom_con_tab(tmp_path):
    ruta = str(tmp_path / "t.txt")
    descargas.escribir_filas(ruta, ["a", "b"], [[1, 2]], "txt")
    datos = open(ruta, "rb").read()
    assert not datos.startswith(b"\xef\xbb\xbf")
    assert datos == b"a\tb\r\n1\t2\r\n"


# --------------------------------------------------------------------------
# exportar / leer
# --------------------------------------------------------------------------
def test_exportar_tabla_sin_filas_devuelve_none(cwd_tmp):
    assert descargas.exportar_tabla(["a"], [], "vacia") is None


def test_exportar_tabla_escribe_y_devuelve_ruta(fecha_fija, cwd_tmp):
    ruta = descargas.exportar_tabla(["a", "b"], [[1, 2]], "etiq")
    assert os.path.isfile(ruta)
    assert os.path.basename(ruta) == "etiq_20260102030405.csv"


def test_exportar_lineas(fecha_fija, cwd_tmp):
    ruta = descargas.exportar_lineas(["uno", "dos\n"], "informe")
    assert ruta.endswith(".txt")
    assert open(ruta, encoding="utf-8").read() == "uno\ndos\n"
    assert descargas.exportar_lineas([], "x") is None


def test_leer_lineas_inexistente(tmp_path):
    assert descargas.leer_lineas(str(tmp_path / "no_existe.txt")) == []


def test_leer_lineas_descarta_bom(tmp_path):
    ruta = str(tmp_path / "bom.txt")
    with open(ruta, "w", encoding="utf-8-sig") as f:
        f.write("alfa\nbeta\n")
    assert descargas.leer_lineas(ruta) == ["alfa\n", "beta\n"]
