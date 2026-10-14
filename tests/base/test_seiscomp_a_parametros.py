#!/usr/bin/env python3
"""
Tests de seiscomp_a_parametros.py
=================================
Cubre el conversor de la exportación cruda de SeisComp al CSV de 8 columnas que
lee generajson.py: posiciones de columnas, descarte de filas sin coordenadas,
trazabilidad del índice de fila, conteos del resumen y cálculo de la ventana.
"""

import csv
import os

import pytest

import seiscomp_a_parametros as s

COLUMNAS = ["id_evento", "id_origen", "ot_utc", "latitud", "longitud",
            "profundidad_km", "magnitud", "tipo_magnitud", "operador",
            "region", "estatus"]


def _escribir_exportacion(ruta, filas):
    with open(str(ruta), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(COLUMNAS)
        w.writerows(filas)


def _fila(i=1, ot="2026-01-01 00:00:00", lat="-33.0", lon="-71.0",
          prof="30.0", mag="5.0", tmag="ML", op="ANALISTA"):
    return [i, i * 10, ot, lat, lon, prof, mag, tmag, op, "region", "C"]


def _leer(ruta):
    with open(str(ruta), encoding="utf-8", newline="") as f:
        return list(csv.reader(f))


# --------------------------------------------------------------------------
# _numero
# --------------------------------------------------------------------------
@pytest.mark.parametrize("entrada, esperado", [
    (None, None), ("", None), ("  ", None),
    ("-33.5", -33.5), (" 12 ", 12.0), ("abc", None),
])
def test_numero(entrada, esperado):
    assert s._numero(entrada) == esperado


# --------------------------------------------------------------------------
# _ruta_completo
# --------------------------------------------------------------------------
def test_ruta_completo_con_extension():
    assert s._ruta_completo("/tmp/ev.csv") == "/tmp/ev.csv.completo"


def test_ruta_completo_sin_extension():
    assert s._ruta_completo("/tmp/ev") == "/tmp/ev.csv.completo"


# --------------------------------------------------------------------------
# convertir
# --------------------------------------------------------------------------
def test_convertir_escribe_ocho_columnas(tmp_path):
    origen = tmp_path / "seiscomp.csv"
    destino = tmp_path / "salida.csv"
    _escribir_exportacion(origen, [_fila(i=1)])

    resumen = s.convertir(str(origen), str(destino))
    filas = _leer(destino)

    assert filas[0] == ["", "Fecha_Hora", "Latitud", "Longitud", "Prof.",
                        "Mag.", "Tipo_mag.", "Analista"]
    # Primera columna = índice de fila en la exportación (0), no un contador.
    assert filas[1][0] == "0"
    assert filas[1][1:] == ["2026-01-01 00:00:00", "-33.0", "-71.0",
                            "30.0", "5.0", "ML", "ANALISTA"]
    assert resumen["leidas"] == 1
    assert resumen["convertidas"] == 1
    assert resumen["descartadas"] == 0


def test_convertir_trazabilidad_al_saltar_una_fila(tmp_path):
    origen = tmp_path / "seiscomp.csv"
    destino = tmp_path / "salida.csv"
    _escribir_exportacion(origen, [
        _fila(i=1, lat="-33.0"),
        _fila(i=2, lat=""),       # sin latitud -> descartada
        _fila(i=3, lat="-34.0"),
    ])

    resumen = s.convertir(str(origen), str(destino))
    filas = _leer(destino)

    assert resumen["descartadas"] == 1
    assert resumen["sin_coordenadas"] == 1
    # La tercera fila conserva su índice original (2), no (1).
    assert filas[1][0] == "0"
    assert filas[2][0] == "2"


def test_convertir_sin_magnitud_no_descarta(tmp_path):
    origen = tmp_path / "seiscomp.csv"
    destino = tmp_path / "salida.csv"
    _escribir_exportacion(origen, [_fila(mag="")])

    resumen = s.convertir(str(origen), str(destino))
    assert resumen["convertidas"] == 1
    assert resumen["sin_magnitud"] == 1


def test_convertir_cuenta_por_operador(tmp_path):
    origen = tmp_path / "seiscomp.csv"
    destino = tmp_path / "salida.csv"
    _escribir_exportacion(origen, [
        _fila(op="ANA"), _fila(op="ANA"), _fila(op="BETO"),
    ])

    resumen = s.convertir(str(origen), str(destino))
    assert resumen["por_operador"] == {"ANA": 2, "BETO": 1}


def test_convertir_ventana_usa_min_y_max(tmp_path):
    origen = tmp_path / "seiscomp.csv"
    destino = tmp_path / "salida.csv"
    # Desordenado a propósito.
    _escribir_exportacion(origen, [
        _fila(ot="2026-02-01 00:00:00"),
        _fila(ot="2026-01-01 00:00:00"),
        _fila(ot="2026-03-01 00:00:00"),
    ])

    resumen = s.convertir(str(origen), str(destino))
    assert resumen["ventana"] == ("2026-01-01 00:00:00", "2026-03-01 00:00:00")


def test_convertir_columnas_faltantes(tmp_path):
    origen = tmp_path / "seiscomp.csv"
    with open(str(origen), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ot_utc", "latitud"])  # faltan varias columnas
        w.writerow(["2026-01-01 00:00:00", "-33.0"])

    with pytest.raises(ValueError):
        s.convertir(str(origen), str(tmp_path / "salida.csv"))


def test_convertir_origen_inexistente(tmp_path):
    with pytest.raises(IOError):
        s.convertir(str(tmp_path / "no_existe.csv"), str(tmp_path / "s.csv"))


def test_convertir_sin_coordenadas_no_convierte_nada(tmp_path):
    origen = tmp_path / "seiscomp.csv"
    destino = tmp_path / "salida.csv"
    _escribir_exportacion(origen, [_fila(lat="", lon="")])

    resumen = s.convertir(str(origen), str(destino))
    assert resumen["convertidas"] == 0
    assert resumen["descartadas"] == 1
