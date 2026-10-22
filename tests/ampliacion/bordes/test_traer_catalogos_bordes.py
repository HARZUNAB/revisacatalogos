#!/usr/bin/env python3
"""
Tests de bordes de traer_catalogos.py
=====================================
Casos borde de la parte pura y del reuso local que el test base no cubre:
longitudes y fechas raras en `a_iso`, plantillas que no validan el valor,
separadores con tabulador, `_emitir`/`_ruta_tmp` y el reuso sin tocar la red.

La parte SSH/SCP se sustituye por una conexión espía. El módulo no se modifica
en esta tanda.
"""

import pytest

import traer_catalogos as t


# --------------------------------------------------------------------------
# a_iso
# --------------------------------------------------------------------------
def test_a_iso_trece_digitos_no_falla():
    # strptime acepta 13 dígitos para el formato de 14: interpreta mal y sigue.
    assert t.a_iso("2026010112304") == "2026-01-01T12:30:04"


def test_a_iso_quince_digitos_revienta():
    with pytest.raises(ValueError):
        t.a_iso("202601011230451")


def test_a_iso_mes_invalido_y_bisiesto():
    with pytest.raises(ValueError):
        t.a_iso("20261301120000")
    with pytest.raises(ValueError):
        t.a_iso("20230229120000")
    assert t.a_iso("20240229120000") == "2024-02-29T12:00:00"


def test_a_iso_entero_no_es_str():
    with pytest.raises(TypeError):
        t.a_iso(20260101123045)


# --------------------------------------------------------------------------
# generar_select_inp
# --------------------------------------------------------------------------
_PLANTILLA_BASE = (
    b"Start time                 : 20200101000000\n"
    b"End time                   : 20200102000000\n"
)


def _usar_plantilla(monkeypatch, tmp_path, contenido=_PLANTILLA_BASE):
    ruta = tmp_path / "select.inp"
    ruta.write_bytes(contenido)
    monkeypatch.setattr(t, "PLANTILLA", str(ruta))
    return ruta


def test_generar_select_inp_no_valida_el_valor(monkeypatch, tmp_path):
    _usar_plantilla(monkeypatch, tmp_path)
    destino = tmp_path / "salida" / "select.inp"
    t.generar_select_inp("abc", "def", str(destino))
    data = destino.read_bytes()
    assert b"Start time                 : abc" in data
    assert b"End time                   : def" in data


def test_generar_select_inp_etiqueta_sin_catorce_digitos(monkeypatch, tmp_path):
    _usar_plantilla(monkeypatch, tmp_path,
                    b"Start time: 2020\nEnd time: 20200102000000\n")
    destino = tmp_path / "salida" / "select.inp"
    with pytest.raises(RuntimeError):
        t.generar_select_inp("20260301000000", "20260302000000", str(destino))
    assert not destino.exists()


def test_generar_select_inp_con_tabuladores(monkeypatch, tmp_path):
    _usar_plantilla(
        monkeypatch, tmp_path,
        b"Start time\t:\t20200101000000\nEnd time\t:\t20200102000000\n")
    destino = tmp_path / "select.inp"
    t.generar_select_inp("20260301000000", "20260302000000", str(destino))
    data = destino.read_bytes()
    assert b"20260301000000" in data and b"20260302000000" in data


# --------------------------------------------------------------------------
# _emitir / _ruta_tmp
# --------------------------------------------------------------------------
def test_emitir_recorta_a_cero_uno():
    vistos = []
    t._emitir(vistos.append, -5.0)
    t._emitir(vistos.append, 5.0)
    assert vistos == [0.0, 1.0]
    t._emitir(None, 0.3)  # sin interesado no falla


def test_ruta_tmp():
    assert t._ruta_tmp("x.csv") == "tmp/x.csv"


# --------------------------------------------------------------------------
# Reuso local sin tocar la red
# --------------------------------------------------------------------------
class ConexionEspia:
    def __init__(self):
        self.llamadas = []

    def resolver(self, nombre):
        self.llamadas.append(("resolver", nombre))
        raise RuntimeError("resolver llamado")

    def ssh_login(self, comando):
        self.llamadas.append(("ssh_login", comando))

    def subir(self, local, remoto):
        self.llamadas.append(("subir", local, remoto))

    def bajar(self, remoto, local):
        self.llamadas.append(("bajar", remoto, local))


def test_traer_seisan_reusa_sin_llamar_a_la_red(tmp_path):
    ini, fin = "20260101000000", "20260102000000"
    (tmp_path / ("select_%s_%s.out" % (ini, fin))).write_text(
        " 2025  2 1 0041 28.5QL -28.121 -70.037109.0  GUC 10 0.3\n",
        encoding="utf-8")
    espia = ConexionEspia()
    destino = t.traer_seisan(ini, fin, espia, cwd=str(tmp_path))
    assert destino == str(tmp_path / ("select_%s_%s.out" % (ini, fin)))
    assert espia.llamadas == []


def test_traer_eventquery_no_reusa_un_archivo_vacio(tmp_path):
    ini, fin = "20260101000000", "20260102000000"
    (tmp_path / ("eventquery_%s_%s.csv" % (ini, fin))).write_text(
        "", encoding="utf-8")   # tamaño 0 -> no es caché válida
    espia = ConexionEspia()
    with pytest.raises(RuntimeError):
        t.traer_eventquery(ini, fin, espia, cwd=str(tmp_path))
    assert ("resolver", "eventquery2") in espia.llamadas
