#!/usr/bin/env python3
"""
Tests de generajson.py — procesar_csv y resumen
==============================================
Cubre `procesar_csv` de punta a punta con un CSV mínimo por fuente y las
salidas que escribe: `datos/eventos_<vista>.json`, `datos/conteo_perfiles_<vista>.json`
y, solo con entregables, `descargas/sospechosos_<vista>.csv`.

`detectar_perfiles` se parchea a lista vacía para que el test sea determinista:
sin grillas reales todos los eventos quedan sin perfil (y `es_sospechoso`
corta ahí sin tocar el catálogo histórico).
"""

import csv
import json
import os

import pytest

import asigna_perfiles as ap
import generajson
from generajson import _resumen_y_conteo


@pytest.fixture
def sin_perfiles(monkeypatch):
    """Fuerza la ausencia de perfiles (no depende de grillas/ en disco)."""
    monkeypatch.setattr(ap, "detectar_perfiles", lambda *a, **k: [])


def _escribir_csv(ruta, encabezado, filas):
    with open(ruta, "w", newline="") as f:
        escritor = csv.writer(f)
        escritor.writerow(encabezado)
        for fila in filas:
            escritor.writerow(fila)
    return ruta


def _csv_seisan(ruta):
    return _escribir_csv(
        ruta,
        ["id", "fecha hora", "lat", "lon", "prof", "mag", "tipo", "analista"],
        [[0, "2020-01-01 00:00:00", -30.0, -71.0, 50.0, 4.5, "ML", "jere"],
         [1, "2020-01-02 00:00:00", -31.0, -72.0, 30.0, 5.0, "Mw", "cris"]])


def _leer_json(ruta):
    with open(ruta) as f:
        return json.load(f)


# --------------------------------------------------------------------------
# procesar_csv: seisan
# --------------------------------------------------------------------------
def test_procesar_csv_genera_json_y_conteo(cwd_tmp, sin_perfiles, sin_entregables):
    ruta = _csv_seisan(str(cwd_tmp / "eventos.csv"))

    resultado = generajson.procesar_csv(ruta, "seisan", salida="prueba")

    assert resultado == (2, 0, 2)

    eventos = _leer_json(os.path.join(str(cwd_tmp), "datos", "eventos_prueba.json"))
    assert len(eventos) == 2
    assert eventos[0]["id"] == 1
    assert eventos[0]["fecha hora"] == "2020-01-01 00:00:00"
    assert eventos[0]["analista"] == "jere"
    assert eventos[0]["archivo_origen"] == "eventos.csv"
    # Sin perfiles, todos quedan sin perfil y marcados como sospechosos.
    for ev in eventos:
        assert ev["perfil"] is None
        assert ev["sospechoso"] is True
        assert ev["motivo"] == "sin_perfiles"
        assert "lon" not in ev and "lat" not in ev

    conteo = _leer_json(
        os.path.join(str(cwd_tmp), "datos", "conteo_perfiles_prueba.json"))
    assert conteo["total"] == 2
    assert conteo["con_perfil"] == 0
    assert conteo["sin_perfil"] == 2
    assert conteo["conteo"] == {"(sin perfil)": 2}
    assert conteo["sin_perfil_motivos"] == {"sin_perfiles": 2}
    assert conteo["cobertura_set"] is None


def test_procesar_csv_sin_entregables_no_escribe_sospechosos(
        cwd_tmp, sin_perfiles, sin_entregables):
    ruta = _csv_seisan(str(cwd_tmp / "eventos.csv"))
    generajson.procesar_csv(ruta, "seisan", salida="prueba")
    assert not os.path.exists(
        os.path.join(str(cwd_tmp), "descargas", "sospechosos_prueba.csv"))


def test_procesar_csv_con_entregables_escribe_sospechosos(
        cwd_tmp, sin_perfiles, con_entregables):
    ruta = _csv_seisan(str(cwd_tmp / "eventos.csv"))
    generajson.procesar_csv(ruta, "seisan", salida="prueba")

    destino = os.path.join(str(cwd_tmp), "descargas", "sospechosos_prueba.csv")
    assert os.path.exists(destino)
    with open(destino, newline="") as f:
        filas = list(csv.reader(f))
    # Encabezado + los dos eventos (todos sospechosos por estar sin perfil).
    assert filas[0][0] == "id"
    assert len(filas) == 3


def test_procesar_csv_ignora_filas_cortas(cwd_tmp, sin_perfiles, sin_entregables):
    ruta = _escribir_csv(
        str(cwd_tmp / "eventos.csv"),
        ["id", "fecha hora", "lat", "lon", "prof", "mag", "tipo", "analista"],
        [[0, "2020-01-01 00:00:00", -30.0, -71.0, 50.0, 4.5, "ML", "jere"],
         [1, "corta"],  # menos de 5 columnas -> se salta
         [2, "2020-01-03 00:00:00", "no_es_float", -71.0, 10.0, 3.0, "ML", "x"]])
    resultado = generajson.procesar_csv(ruta, "seisan", salida="prueba")
    assert resultado[0] == 1


def test_procesar_csv_eventquery_avisa_sin_atribucion(
        cwd_tmp, sin_perfiles, sin_entregables, capsys):
    # Sin datos/atribucion_*.csv en el CWD, avisa que falta atribución.
    ruta = _escribir_csv(
        str(cwd_tmp / "eventos.csv"),
        ["id", "fecha hora", "lat", "lon", "prof", "mag", "tipo", "x",
         "percibido"],
        [[0, "2020-01-01 00:00:00", -30.0, -71.0, 50.0, 4.5, "ML", "", "S"]])
    generajson.procesar_csv(ruta, "eventquery", salida="evq")
    assert "sin atribución" in capsys.readouterr().out


def test_procesar_csv_agencia_vacia(cwd_tmp, sin_perfiles, sin_entregables):
    # CSV de una agencia con solo el encabezado (ventana sin datos): no rompe y
    # deja un JSON vacío.
    ruta = _escribir_csv(
        str(cwd_tmp / "consultaapi_EMSC.csv"),
        ["id", "fecha hora", "lat", "lon", "prof", "mag", "tipo", "ref",
         "agencia"],
        [])
    resultado = generajson.procesar_csv(ruta, "agencia", salida="agencia_EMSC",
                                        agencia="EMSC")
    assert resultado == (0, 0, 0)
    eventos = _leer_json(
        os.path.join(str(cwd_tmp), "datos", "eventos_agencia_EMSC.json"))
    assert eventos == []


# --------------------------------------------------------------------------
# _resumen_y_conteo
# --------------------------------------------------------------------------
def test_resumen_y_conteo_cuenta_perfiles(cwd_tmp):
    eventos = [
        {"perfil": "P001", "sospechoso": False},
        {"perfil": "P001", "sospechoso": False},
        {"perfil": None, "motivo": "fuera_cobertura_norte", "sospechoso": True},
    ]
    total, con_perfil, sin_perfil = _resumen_y_conteo(eventos, "vista", [],
                                                      "(no generado)")
    assert (total, con_perfil, sin_perfil) == (3, 2, 1)

    conteo = _leer_json(os.path.join(str(cwd_tmp), "datos",
                                     "conteo_perfiles_vista.json"))
    assert conteo["total"] == 3
    assert conteo["con_perfil"] == 2
    assert conteo["sin_perfil"] == 1
    assert conteo["conteo"] == {"P001": 2, "(sin perfil)": 1}
    assert conteo["sin_perfil_motivos"] == {"fuera_cobertura_norte": 1}
