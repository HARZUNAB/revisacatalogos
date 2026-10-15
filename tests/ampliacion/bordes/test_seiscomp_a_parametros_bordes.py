#!/usr/bin/env python3
"""
Tests de bordes de seiscomp_a_parametros.py
==========================================
Casos borde que el test base no cubre: valores no finitos y notación
científica, latitud "nan" que se convierte igual, ventana sin fechas / que
ignora descartadas, ramas del informe, la marca de exportación y `_ruta_completo`
con puntos en el nombre.

El módulo no se modifica en esta tanda.
"""

import csv

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
# _numero con no finitos / notación
# --------------------------------------------------------------------------
def test_numero_no_finitos_y_notacion():
    import math
    assert math.isnan(s._numero("nan"))
    assert s._numero("inf") == float("inf")
    assert s._numero("1e3") == 1000.0
    assert s._numero("1_000") == 1000.0
    assert s._numero("0x10") is None


# --------------------------------------------------------------------------
# convertir: latitud "nan" se convierte igual
# --------------------------------------------------------------------------
def test_convertir_latitud_nan_no_descarta(tmp_path):
    origen = tmp_path / "seiscomp.csv"
    destino = tmp_path / "salida.csv"
    _escribir_exportacion(origen, [_fila(lat="nan")])
    resumen = s.convertir(str(origen), str(destino))
    assert resumen["convertidas"] == 1
    assert resumen["descartadas"] == 0
    assert _leer(destino)[1][2] == "nan"


# --------------------------------------------------------------------------
# convertir: ventana
# --------------------------------------------------------------------------
def test_convertir_ventana_sin_fechas(tmp_path):
    origen = tmp_path / "seiscomp.csv"
    destino = tmp_path / "salida.csv"
    _escribir_exportacion(origen, [_fila(ot="")])
    resumen = s.convertir(str(origen), str(destino))
    assert resumen["ventana"] == (None, None)


def test_convertir_ventana_ignora_descartadas(tmp_path):
    origen = tmp_path / "seiscomp.csv"
    destino = tmp_path / "salida.csv"
    _escribir_exportacion(origen, [
        _fila(ot="2026-01-01 00:00:00"),
        _fila(lat="", ot="2020-01-01 00:00:00"),   # descartada
    ])
    resumen = s.convertir(str(origen), str(destino))
    assert resumen["ventana"] == ("2026-01-01 00:00:00", "2026-01-01 00:00:00")
    assert resumen["descartadas"] == 1


# --------------------------------------------------------------------------
# convertir: profundidad / operador / fila corta
# --------------------------------------------------------------------------
def test_convertir_sin_profundidad_y_sin_operador(tmp_path):
    origen = tmp_path / "seiscomp.csv"
    destino = tmp_path / "salida.csv"
    _escribir_exportacion(origen, [
        _fila(prof="", op=""),
        _fila(prof="0.0", op=""),
    ])
    resumen = s.convertir(str(origen), str(destino))
    assert resumen["sin_profundidad"] == 1
    assert resumen["con_profundidad"] == 1
    assert resumen["por_operador"] == {}


def test_convertir_fila_corta_descarta(tmp_path):
    origen = tmp_path / "seiscomp.csv"
    destino = tmp_path / "salida.csv"
    with open(str(origen), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(COLUMNAS)
        w.writerow(["1"])   # una sola celda -> el resto None
    resumen = s.convertir(str(origen), str(destino))
    assert resumen["convertidas"] == 0
    assert resumen["descartadas"] == 1


def test_convertir_descartada_sin_magnitud_no_cuenta(tmp_path):
    origen = tmp_path / "seiscomp.csv"
    destino = tmp_path / "salida.csv"
    _escribir_exportacion(origen, [_fila(lat="", mag="")])
    resumen = s.convertir(str(origen), str(destino))
    assert resumen["descartadas"] == 1
    assert resumen["sin_magnitud"] == 0


# --------------------------------------------------------------------------
# informe
# --------------------------------------------------------------------------
def _resumen_base(**cambios):
    base = {"leidas": 1, "convertidas": 1, "descartadas": 0, "sin_magnitud": 0,
            "sin_profundidad": 0, "con_profundidad": 1, "por_operador": {},
            "ventana": (None, None)}
    base.update(cambios)
    return base


def test_informe_sin_profundidad_avisa_y_no_muestra_conteo(capsys):
    s.informe(_resumen_base(sin_profundidad=1), "o.csv", "d.csv")
    salida = capsys.readouterr().out
    assert "sin profundidad" in salida
    assert "Con profundidad:" not in salida


def test_informe_con_profundidad_muestra_conteo(capsys):
    s.informe(_resumen_base(con_profundidad=3), "o.csv", "d.csv")
    assert "Con profundidad: 3" in capsys.readouterr().out


def test_informe_operadores_de_mayor_a_menor(capsys):
    s.informe(_resumen_base(por_operador={"ANA": 1, "BETO": 3}), "o.csv", "d.csv")
    salida = capsys.readouterr().out
    assert salida.index("BETO") < salida.index("ANA")


def test_informe_sin_ventana_no_imprime_ventana(capsys):
    s.informe(_resumen_base(), "o.csv", "d.csv")
    assert "Ventana" not in capsys.readouterr().out


# --------------------------------------------------------------------------
# _avisar_sin_marca / _ruta_completo
# --------------------------------------------------------------------------
def test_avisar_sin_marca(capsys, tmp_path):
    origen = tmp_path / "seiscomp.csv"
    origen.write_text("x", encoding="utf-8")
    s._avisar_sin_marca(str(origen))
    assert "No está la marca" in capsys.readouterr().out


def test_avisar_con_marca_no_imprime(capsys, tmp_path):
    origen = tmp_path / "seiscomp.csv"
    origen.write_text("x", encoding="utf-8")
    (tmp_path / "seiscomp.csv.completo").write_text("x", encoding="utf-8")
    s._avisar_sin_marca(str(origen))
    assert capsys.readouterr().out == ""


def test_ruta_completo_con_punto_en_el_nombre():
    assert s._ruta_completo("/tmp/eventos.v2") == "/tmp/eventos.v2.completo"
    assert s._ruta_completo("/tmp/dir.a/eventos") == "/tmp/dir.a/eventos.csv.completo"
