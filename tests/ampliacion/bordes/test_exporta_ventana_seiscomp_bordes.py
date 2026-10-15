#!/usr/bin/env python3
"""
Tests de bordes de exporta_ventana_seiscomp.py
=============================================
Casos borde de la parte pura que el test base no cubre: magnitud de estación no
numérica (se ignora, igual que `_acumular_por_evento`), límites del rango
creíble, append/vacío del CSV, celdas raras, radio y actividad en el borde,
vigencia inclusiva, época abierta, antimeridiano y rutas derivadas.
"""

import decimal
import math
from datetime import datetime, timedelta

import pytest

import exporta_ventana_seiscomp as ex


# --------------------------------------------------------------------------
# _resumen_fases: magnitud no numérica y límites de rango
# --------------------------------------------------------------------------
def test_resumen_fases_magnitud_no_numerica_se_ignora():
    # Igual que _acumular_por_evento: una magnitud no numérica no corta el
    # resumen, solo no entra al conteo de rango.
    resumen = ex._resumen_fases([{"tiene_magnitud": "Si", "mag_estacion": "xx",
                                  "mag_est_residuo": ""}])
    assert resumen["con_magnitud"] == 1
    assert resumen["fuera_de_rango"] == 0


def test_resumen_fases_limites_del_rango():
    lo, hi = ex.RANGO_MAG_ESTACION
    dentro = ex._resumen_fases([
        {"tiene_magnitud": "Si", "mag_estacion": str(lo), "mag_est_residuo": ""},
        {"tiene_magnitud": "Si", "mag_estacion": str(hi), "mag_est_residuo": ""},
    ])
    assert dentro["fuera_de_rango"] == 0
    fuera = ex._resumen_fases([
        {"tiene_magnitud": "Si", "mag_estacion": str(lo - 0.01),
         "mag_est_residuo": ""},
        {"tiene_magnitud": "Si", "mag_estacion": str(hi + 0.01),
         "mag_est_residuo": ""},
    ])
    assert fuera["fuera_de_rango"] == 2


# --------------------------------------------------------------------------
# _escribir_csv: append y vacío
# --------------------------------------------------------------------------
def test_escribir_csv_append_no_repite_cabecera(tmp_path):
    ruta = str(tmp_path / "out.csv")
    cabecera = ["id_evento"]
    ex._escribir_csv(ruta, [{"id_evento": "E1"}], cabecera=cabecera)
    ex._escribir_csv(ruta, [{"id_evento": "E2"}], cabecera=cabecera, append=True)
    lineas = (tmp_path / "out.csv").read_text(encoding="utf-8").splitlines()
    assert lineas == ["id_evento", "E1", "E2"]


def test_escribir_csv_sin_filas_solo_cabecera(tmp_path):
    ruta = str(tmp_path / "out.csv")
    ex._escribir_csv(ruta, [], cabecera=["a", "b"])
    assert (tmp_path / "out.csv").read_text(encoding="utf-8").splitlines() == ["a,b"]


# --------------------------------------------------------------------------
# _celda con valores raros
# --------------------------------------------------------------------------
def test_celda_cero_y_bool_no_son_vacio():
    assert ex._celda(0) == 0
    assert ex._celda(True) is True


def test_celda_decimal_nan():
    assert math.isnan(ex._celda(decimal.Decimal("NaN")))


# --------------------------------------------------------------------------
# _no_picadas_de_evento: radio y actividad en el borde
# --------------------------------------------------------------------------
def test_no_picadas_radio_no_positivo():
    for radio in (0, -5):
        filas, descartadas = ex._no_picadas_de_evento(
            datetime(2020, 6, 1), "E1", "O1", -26.0, -70.0, {}, set(), {},
            radio_km=radio)
        assert filas == [] and descartadas == 0


def _fila_inventario(red="IU", estacion="ABC", lat=-26.0, lon=-70.0, **extra):
    fila = {"red": red, "estacion": estacion, "loc": "00", "cha": "BHZ",
            "latitud": lat, "longitud": lon, "elevacion": "1000",
            "lugar": "Lugar", "pais": "Chile"}
    fila.update(extra)
    return fila


def test_no_picadas_actividad_horas_cero_es_inclusiva():
    filas_inv = [_fila_inventario(epoca_inicio=datetime(2019, 1, 1))]
    indice = ex._indice_por_celda(filas_inv)
    instante = datetime(2020, 6, 1, 12, 0, 0)
    filas, _ = ex._no_picadas_de_evento(
        instante, "E1", "O1", -26.0, -70.0, indice, picadas=set(),
        actividad={("IU", "ABC"): [instante]}, radio_km=100.0,
        actividad_horas=0)
    assert filas[0]["actividad_ventana"] == 1


# --------------------------------------------------------------------------
# _vigente / _stream_valido
# --------------------------------------------------------------------------
def test_vigente_bordes_inclusivos():
    d0, d1 = datetime(2020, 1, 1), datetime(2021, 1, 1)
    assert ex._vigente(d0, d1, d0) is True
    assert ex._vigente(d0, d1, d1) is True


def _registro(epoca_inicio=None, epoca_fin=None, red_fin=None, cha="BHZ"):
    return {"red": "IU", "estacion": "ABC", "loc": "00", "cha": cha,
            "epoca_inicio": epoca_inicio, "epoca_fin": epoca_fin,
            "red_inicio": None, "red_fin": red_fin,
            "loc_inicio": None, "loc_fin": None,
            "cha_inicio": None, "cha_fin": None,
            "latitud": -26.0, "longitud": -70.0, "elevacion": "1000",
            "lugar": "Lugar", "pais": "Chile"}


def test_stream_valido_epoca_abierta():
    registro, cantidad = ex._stream_valido([_registro()], datetime(1990, 1, 1))
    assert cantidad == 1
    assert registro is not None


def test_stream_valido_red_vencida():
    registros = [_registro(red_fin=datetime(1990, 1, 1))]
    assert ex._stream_valido(registros, datetime(2020, 1, 1)) == (None, 0)


# --------------------------------------------------------------------------
# _distancia_km / _coordenada_valida
# --------------------------------------------------------------------------
def test_distancia_km_antimeridiano():
    # 179.9° a -179.9° son 0.2° de longitud, no casi una vuelta.
    assert ex._distancia_km(10.0, 179.9, 10.0, -179.9) == pytest.approx(
        21.9, abs=0.5)


def test_coordenada_valida_casi_cero_y_extremos():
    assert ex._coordenada_valida(0.0, 0.0001) is True
    assert ex._coordenada_valida(90.0, 180.0) is True
    assert ex._coordenada_valida(-90.0, -180.0) is True


# --------------------------------------------------------------------------
# Rutas y marca
# --------------------------------------------------------------------------
def test_ruta_fases_solo_separa_el_ultimo_sufijo():
    assert ex._ruta_fases("a.tar.gz") == "a.tar_fases.gz"


def test_radio_de_la_marca_variantes(tmp_path):
    ruta = tmp_path / "x.txt"
    ruta.write_text("radio 12.5km", encoding="utf-8")
    assert ex._radio_de_la_marca(str(ruta)) == 12.5
    ruta.write_text("radio abc km", encoding="utf-8")
    assert ex._radio_de_la_marca(str(ruta)) is None


# --------------------------------------------------------------------------
# _bases_a_consultar / _prioridad_por_base
# --------------------------------------------------------------------------
def test_bases_a_consultar_no_recorta():
    assert ex._bases_a_consultar("") == [""]
    assert ex._bases_a_consultar(" seiscomp ") == [" seiscomp "]


def test_prioridad_por_base_con_cobertura_none():
    prioridad = ex._prioridad_por_base(
        {"a": None, "b": {"hasta": datetime(2026, 10, 1)}})
    assert prioridad["a"] < prioridad["b"]
