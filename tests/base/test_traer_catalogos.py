#!/usr/bin/env python3
"""
Tests de traer_catalogos.py
===========================
Cubre las dos funciones puras de la capa de red: la conversión de marca de
tiempo y la generación del ``select.inp`` a partir de la plantilla. La parte que
habla con el servidor (SSH/SCP) no se testea acá.
"""

import pytest

import traer_catalogos as t


# --------------------------------------------------------------------------
# a_iso
# --------------------------------------------------------------------------
def test_a_iso():
    assert t.a_iso("20260101123045") == "2026-01-01T12:30:45"


def test_a_iso_marca_invalida():
    with pytest.raises(ValueError):
        t.a_iso("no-es-fecha")


# --------------------------------------------------------------------------
# generar_select_inp
# --------------------------------------------------------------------------
PLANTILLA_BASE = (
    b"Start time                 : 20200101000000\n"
    b"Some other field           : keep me\n"
    b"End time                   : 20200102000000\n"
    b"binary\x00\x00\x00: should survive\n"
)


def _usar_plantilla(monkeypatch, tmp_path, contenido=PLANTILLA_BASE):
    ruta = tmp_path / "select.inp"
    ruta.write_bytes(contenido)
    monkeypatch.setattr(t, "PLANTILLA", str(ruta))
    return ruta


def test_generar_select_inp_reemplaza_inicio_y_fin(monkeypatch, tmp_path):
    _usar_plantilla(monkeypatch, tmp_path)
    destino = tmp_path / "salida" / "select.inp"

    t.generar_select_inp("20260301000000", "20260302000000", str(destino))

    data = destino.read_bytes()
    assert b"Start time" in data and b"20260301000000" in data
    assert b"End time" in data and b"20260302000000" in data
    # El resto de la plantilla no se toca.
    assert b"Some other field           : keep me" in data


def test_generar_select_inp_preserva_bytes_nulos(monkeypatch, tmp_path):
    _usar_plantilla(monkeypatch, tmp_path)
    destino = tmp_path / "salida" / "select.inp"

    t.generar_select_inp("20260301000000", "20260302000000", str(destino))
    assert b"binary\x00\x00\x00" in destino.read_bytes()


def test_generar_select_inp_crea_la_carpeta_destino(monkeypatch, tmp_path):
    _usar_plantilla(monkeypatch, tmp_path)
    destino = tmp_path / "nueva" / "sub" / "select.inp"

    t.generar_select_inp("20260301000000", "20260302000000", str(destino))
    assert destino.is_file()


def test_generar_select_inp_falla_si_falta_la_etiqueta(monkeypatch, tmp_path):
    _usar_plantilla(monkeypatch, tmp_path,
                    b"Start time: 20200101000000\nsin End time\n")
    with pytest.raises(RuntimeError):
        t.generar_select_inp("20260301000000", "20260302000000",
                             str(tmp_path / "select.inp"))


def test_generar_select_inp_falla_si_hay_reemplazos_multiples(monkeypatch, tmp_path):
    _usar_plantilla(
        monkeypatch, tmp_path,
        b"Start time: 20200101000000\nStart time: 20200101000000\n"
        b"End time: 20200102000000\n")
    with pytest.raises(RuntimeError):
        t.generar_select_inp("20260301000000", "20260302000000",
                             str(tmp_path / "select.inp"))
