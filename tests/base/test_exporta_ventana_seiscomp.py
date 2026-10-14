#!/usr/bin/env python3
"""
Tests de exporta_ventana_seiscomp.py
====================================
Cubre la parte pura del exportador: geometría y radio de estaciones, vigencia de
épocas e inventario, conteo de fases, fusión de bases y utilidades de archivo.

No abre conexión a la base ni toca la pantalla.
"""

import decimal
from datetime import datetime, timedelta

import pytest

import exporta_ventana_seiscomp as ex


# --------------------------------------------------------------------------
# _distancia_km / _celda_grado / _coordenada_valida
# --------------------------------------------------------------------------
def test_distancia_km_mismo_punto():
    assert ex._distancia_km(-26.0, -70.0, -26.0, -70.0) == pytest.approx(0.0)


def test_distancia_km_un_grado_de_latitud():
    # Un grado de latitud ~ 111.19 km (con el radio medio terrestre).
    d = ex._distancia_km(0.0, 0.0, 1.0, 0.0)
    assert d == pytest.approx(111.19, abs=0.1)


def test_celda_grado():
    assert ex._celda_grado(-26.15, -70.5) == (-27, -71)
    assert ex._celda_grado(0.9, 0.1) == (0, 0)


@pytest.mark.parametrize("lat, lon, esperado", [
    (-26.0, -70.0, True),
    (None, -70.0, False),
    (-26.0, None, False),
    (91.0, 0.0, False),
    (0.0, 181.0, False),
    (0.0, 0.0, False),
])
def test_coordenada_valida(lat, lon, esperado):
    assert ex._coordenada_valida(lat, lon) is esperado


# --------------------------------------------------------------------------
# _indice_por_celda / _estaciones_en_el_radio
# --------------------------------------------------------------------------
def _fila_inventario(red="IU", estacion="ABC", lat=-26.0, lon=-70.0, **extra):
    fila = {"red": red, "estacion": estacion, "loc": "00", "cha": "BHZ",
            "latitud": lat, "longitud": lon, "elevacion": "1000",
            "lugar": "Lugar", "pais": "Chile"}
    fila.update(extra)
    return fila


def test_indice_por_celda_basico():
    filas = [_fila_inventario(), _fila_inventario("CX", "XYZ", lat=10.0,
                                                  lon=10.0)]
    indice = ex._indice_por_celda(filas)
    assert ex._celda_grado(-26.0, -70.0) in indice
    assert ex._celda_grado(10.0, 10.0) in indice


def test_indice_por_celda_descarta_invalidas_y_bindings():
    filas = [
        _fila_inventario(),
        _fila_inventario("ZZ", "NOBIND"),
        _fila_inventario("CX", "ORIGEN", lat=0.0, lon=0.0),
        {"red": "", "estacion": "SINRED", "latitud": -1.0, "longitud": -1.0},
    ]
    indice = ex._indice_por_celda(filas, bindings={("IU", "ABC")})
    registros = [r for celda in indice.values() for r in celda]
    assert {r["estacion"] for r in registros} == {"ABC"}


def test_indice_por_celda_deduplica_streams():
    fila = _fila_inventario(epoca_inicio=datetime(2020, 1, 1))
    indice = ex._indice_por_celda([fila, dict(fila)])
    registros = [r for celda in indice.values() for r in celda]
    assert len(registros) == 1


def test_estaciones_en_el_radio():
    filas = [
        _fila_inventario("IU", "CERCANA", lat=-26.0, lon=-70.0),
        _fila_inventario("IU", "LEJANA", lat=-40.0, lon=-70.0),
    ]
    indice = ex._indice_por_celda(filas)
    cerca = ex._estaciones_en_el_radio(indice, -26.0, -70.0, 100.0)
    assert {r["estacion"] for r in cerca} == {"CERCANA"}
    # radio None -> todos.
    todos = ex._estaciones_en_el_radio(indice, -26.0, -70.0, None)
    assert {r["estacion"] for r in todos} == {"CERCANA", "LEJANA"}


# --------------------------------------------------------------------------
# _vigente / _stream_valido
# --------------------------------------------------------------------------
def test_vigente():
    d0, d1 = datetime(2020, 1, 1), datetime(2021, 1, 1)
    assert ex._vigente(d0, d1, datetime(2020, 6, 1)) is True
    assert ex._vigente(d0, d1, datetime(2019, 1, 1)) is False
    assert ex._vigente(d0, d1, datetime(2022, 1, 1)) is False
    # Sin límites.
    assert ex._vigente(None, None, datetime(2020, 6, 1)) is True


def _registro(epoca_inicio=None, epoca_fin=None, loc="00", cha="BHZ"):
    return {"red": "IU", "estacion": "ABC", "loc": loc, "cha": cha,
            "epoca_inicio": epoca_inicio, "epoca_fin": epoca_fin,
            "red_inicio": None, "red_fin": None,
            "loc_inicio": None, "loc_fin": None,
            "cha_inicio": None, "cha_fin": None,
            "latitud": -26.0, "longitud": -70.0, "elevacion": "1000",
            "lugar": "Lugar", "pais": "Chile"}


def test_stream_valido_sin_vigentes():
    instante = datetime(2015, 1, 1)
    registros = [_registro(datetime(2020, 1, 1), datetime(2021, 1, 1))]
    assert ex._stream_valido(registros, instante) == (None, 0)


def test_stream_valido_elige_el_mas_reciente_y_cuenta():
    instante = datetime(2020, 6, 1)
    registros = [
        _registro(datetime(2019, 1, 1), datetime(2021, 1, 1), cha="BHN"),
        _registro(datetime(2020, 1, 1), datetime(2021, 1, 1), cha="BHZ"),
    ]
    vigente, cantidad = ex._stream_valido(registros, instante)
    assert cantidad == 2
    assert vigente["cha"] == "BHZ"


# --------------------------------------------------------------------------
# _no_picadas_de_evento
# --------------------------------------------------------------------------
def test_no_picadas_de_evento_basico():
    filas_inv = [_fila_inventario("IU", "ABC", lat=-26.0, lon=-70.0,
                                  epoca_inicio=datetime(2019, 1, 1))]
    indice = ex._indice_por_celda(filas_inv)
    filas, descartadas = ex._no_picadas_de_evento(
        datetime(2020, 6, 1), "E1", "O1", -26.0, -70.0, indice,
        picadas=set(), actividad={}, radio_km=100.0)
    assert len(filas) == 1
    assert filas[0]["estacion"] == "ABC"
    assert filas[0]["distancia_km"] == 0.0
    assert filas[0]["actividad_ventana"] == 0
    assert filas[0]["waveform_status"] == ex.ESTADO_SIN_CONSULTAR
    assert descartadas == 0


def test_no_picadas_de_evento_excluye_picadas():
    filas_inv = [_fila_inventario("IU", "ABC", lat=-26.0, lon=-70.0)]
    indice = ex._indice_por_celda(filas_inv)
    filas, _ = ex._no_picadas_de_evento(
        datetime(2020, 6, 1), "E1", "O1", -26.0, -70.0, indice,
        picadas={("IU", "ABC")}, actividad={}, radio_km=100.0)
    assert filas == []


def test_no_picadas_de_evento_cuenta_actividad():
    filas_inv = [_fila_inventario("IU", "ABC", lat=-26.0, lon=-70.0)]
    indice = ex._indice_por_celda(filas_inv)
    instante = datetime(2020, 6, 1, 12, 0, 0)
    actividad = {("IU", "ABC"): [instante - timedelta(hours=1),
                                 instante + timedelta(hours=2),
                                 instante + timedelta(hours=40)]}
    filas, _ = ex._no_picadas_de_evento(
        instante, "E1", "O1", -26.0, -70.0, indice,
        picadas=set(), actividad=actividad, radio_km=100.0)
    assert filas[0]["actividad_ventana"] == 2


def test_no_picadas_de_evento_descarta_sin_stream_vigente():
    filas_inv = [_fila_inventario("IU", "ABC", lat=-26.0, lon=-70.0,
                                  epoca_inicio=datetime(2030, 1, 1))]
    indice = ex._indice_por_celda(filas_inv)
    filas, descartadas = ex._no_picadas_de_evento(
        datetime(2020, 6, 1), "E1", "O1", -26.0, -70.0, indice,
        picadas=set(), actividad={}, radio_km=100.0)
    assert filas == []
    assert descartadas == 1


def test_no_picadas_de_evento_coordenada_invalida():
    filas, descartadas = ex._no_picadas_de_evento(
        datetime(2020, 6, 1), "E1", "O1", None, None, {}, set(), {})
    assert filas == [] and descartadas == 0


# --------------------------------------------------------------------------
# Utilidades de archivo y celdas
# --------------------------------------------------------------------------
def test_celda():
    assert ex._celda(None) == ""
    assert ex._celda(datetime(2020, 6, 1, 12, 30, 0)) == "2020-06-01 12:30:00"
    assert ex._celda(decimal.Decimal("4.2")) == 4.2
    assert ex._celda("texto") == "texto"


def test_rutas_derivadas():
    assert ex._ruta_fases("datos/x.csv") == "datos/x_fases.csv"
    assert ex._ruta_no_picadas("datos/x.csv") == "datos/x_no_picadas.csv"
    assert ex._ruta_completo("datos/x.csv") == "datos/x.csv.completo"
    assert ex._ruta_fases("datos/x") == "datos/x_fases.csv"


def test_escribir_csv_y_verificar_columnas(tmp_path):
    ruta = tmp_path / "out.csv"
    filas = [{"id_evento": "E1", "magnitud": decimal.Decimal("4.2")}]
    ex._escribir_csv(str(ruta), filas, cabecera=["id_evento", "magnitud"])
    texto = ruta.read_text(encoding="utf-8")
    assert texto.splitlines()[0] == "id_evento,magnitud"
    assert "E1,4.2" in texto
    # _verificar_columnas no lanza (solo imprime en discrepancia).
    ex._verificar_columnas(filas, cabecera=["id_evento", "magnitud"])


def test_escribir_marca_y_leer_radio(tmp_path):
    ruta = tmp_path / "x.completo"
    ex._escribir_marca(str(ruta), datetime(2026, 9, 1), datetime(2026, 9, 30),
                       eventos=10, fases=100, no_picadas=5, radio_km=400.0,
                       bases=["seiscomp"], descartadas=2)
    assert ex._radio_de_la_marca(str(ruta)) == 400.0
    assert ex._radio_de_la_marca(str(tmp_path / "no_existe")) is None


# --------------------------------------------------------------------------
# Resúmenes de fases
# --------------------------------------------------------------------------
def test_resumen_fases():
    filas = [
        {"tiene_magnitud": "Si", "mag_estacion": "4.1", "mag_est_residuo": "0.1"},
        {"tiene_magnitud": "Si", "mag_estacion": "-2.0",
         "mag_est_residuo": None},
        {"tiene_magnitud": "No"},
    ]
    resumen = ex._resumen_fases(filas)
    assert resumen["con_magnitud"] == 2
    assert resumen["sin_magnitud"] == 1
    assert resumen["con_residuo"] == 1
    assert resumen["negativas"] == 1
    assert resumen["fuera_de_rango"] == 1


def test_acumular_y_resumen_desde_mapa():
    filas = [
        {"id_evento": "E1", "usada": "true", "red": "IU", "estacion": "ABC",
         "tiene_magnitud": "Si", "mag_estacion": "4.0", "mag_est_residuo": "0.1"},
        {"id_evento": "E1", "usada": "false", "red": "IU", "estacion": "ABC",
         "tiene_magnitud": "Si", "mag_estacion": "5.0", "mag_est_residuo": ""},
        {"id_evento": "E2", "usada": "true", "red": "CX", "estacion": "XYZ",
         "tiene_magnitud": "No"},
    ]
    mapa = {}
    ex._acumular_por_evento(mapa, filas)
    assert set(mapa) == {"E1", "E2"}

    total = ex._resumen_desde_mapa(mapa)
    assert total["eventos"] == 2
    assert total["fases"] == 3
    assert total["usadas"] == 2
    assert total["no_usadas"] == 1
    assert total["con_magnitud"] == 2
    assert total["con_residuo"] == 1
    assert total["mag_promedio"] == pytest.approx(4.5)


# --------------------------------------------------------------------------
# Fusión de bases
# --------------------------------------------------------------------------
def test_prioridad_por_base():
    coberturas = {
        "seiscomp": {"hasta": datetime(2026, 9, 30)},
        "seiscomp2": {"hasta": datetime(2026, 10, 31)},
    }
    prioridad = ex._prioridad_por_base(coberturas)
    assert prioridad["seiscomp"] < prioridad["seiscomp2"]


def test_fusionar_eventos_gana_la_mas_reciente():
    filas_por_base = {
        "seiscomp": [{"id_evento": "E1", "magnitud": "4.0"}],
        "seiscomp2": [{"id_evento": "E1", "magnitud": "4.5"},
                      {"id_evento": "E2", "magnitud": "3.0"}],
    }
    prioridad = {"seiscomp": 0, "seiscomp2": 1}
    fusionados = ex._fusionar_eventos(filas_por_base, prioridad)
    por_id = {f["id_evento"]: f for f in fusionados}
    assert len(fusionados) == 2
    assert por_id["E1"]["base_datos"] == "seiscomp2"
    assert por_id["E1"]["magnitud"] == "4.5"


def test_fusionar_fases_deduplica_por_azimut():
    base = {
        "id_evento": "E1", "id_pick": "P1", "fase": "P",
        "llegada_us": "1", "azimut": "30",
    }
    duplicada = dict(base)
    distinta = dict(base, azimut="40")
    filas_por_base = {"seiscomp": [base, duplicada, distinta]}
    fusionadas = ex._fusionar_fases(filas_por_base, {"seiscomp": 0})
    assert len(fusionadas) == 2
    assert {f["azimut"] for f in fusionadas} == {"30", "40"}


# --------------------------------------------------------------------------
# _bases_a_consultar (sin "todas", que consultaría la red)
# --------------------------------------------------------------------------
def test_bases_a_consultar_nombre_puntual():
    assert ex._bases_a_consultar("seiscomp") == ["seiscomp"]
    assert ex._bases_a_consultar("SEISCOMP") == ["SEISCOMP"]
