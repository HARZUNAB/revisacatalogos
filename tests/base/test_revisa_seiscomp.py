#!/usr/bin/env python3
"""
Tests de revisa_seiscomp.py
===========================
Cubre los ayudantes puros del módulo: parseo de fechas, lectura/índice del CSV
de fases, formateo de celdas, agrupación por estación, filtros de listado y
elección de la exportación que corresponde a un catálogo.

No instancia ninguna ventana ni toca la base de datos.
"""

from datetime import datetime

import pytest

import revisa_seiscomp as r


# --------------------------------------------------------------------------
# _partir_fecha_hora / _campo_tiempo / _instante_de_evento
# --------------------------------------------------------------------------
@pytest.mark.parametrize("entrada, esperado", [
    ("2026-09-04 06:48:08", ("2026-09-04", "06:48:08")),
    ("2026-09-04T06:48:08", ("2026-09-04", "06:48:08")),
    ("2026-09-04  06:48:08", ("2026-09-04", "06:48:08")),
    ("2026-09-04 06:48:08.123", ("2026-09-04", "06:48:08")),
    ("2026-09-04", ("2026-09-04", r.VACIO)),
    ("", (r.VACIO, r.VACIO)),
    (None, (r.VACIO, r.VACIO)),
])
def test_partir_fecha_hora(entrada, esperado):
    assert r._partir_fecha_hora(entrada) == esperado


def test_campo_tiempo_por_nombre_de_columna():
    assert r._campo_tiempo({"ot_utc": "2026-09-04 06:48:08"}) \
        == "2026-09-04 06:48:08"
    assert r._campo_tiempo({"Fecha_Hora": "2026-09-04 06:48:08"}) \
        == "2026-09-04 06:48:08"
    assert r._campo_tiempo({"time": "2026-09-04T06:48:08"}) \
        == "2026-09-04T06:48:08"
    assert r._campo_tiempo({}) == ""


def test_instante_de_evento():
    ev = {"ot_utc": "2026-09-04 06:48:08"}
    assert r._instante_de_evento(ev) == datetime(2026, 9, 4, 6, 48, 8)
    assert r._instante_de_evento({}) is None
    assert r._instante_de_evento({"ot_utc": "basura"}) is None


# --------------------------------------------------------------------------
# _normalizar_catalogo
# --------------------------------------------------------------------------
def test_normalizar_catalogo():
    crudo = {
        "\ufeffFecha_Hora": "2026-09-04 06:48:08",
        "Latitud": "-26.155641555786133",
        "Longitud": "-70.5",
        "Prof.": "35.0",
        "Mag.": "4.2",
        "Tipo_mag.": "ML",
        "Analista": "AB",
        "Referencia": "ref-1",
        "Percep.": "S",
    }
    limpia = r._normalizar_catalogo(crudo)
    assert limpia["fecha"] == "2026-09-04"
    assert limpia["hora"] == "06:48:08"
    assert limpia["latitud"] == "-26.155641555786133"
    assert limpia["prof"] == "35.0"
    assert limpia["mag"] == "4.2"
    assert limpia["tipo"] == "ML"
    assert limpia["referencia"] == "ref-1"
    # Columna ausente -> vacío, sin romper.
    assert r._normalizar_catalogo({})["analista"] == ""


# --------------------------------------------------------------------------
# CSV de fases
# --------------------------------------------------------------------------
def test_indice_y_lectura_de_fases(tmp_path):
    ruta = tmp_path / "fases.csv"
    ruta.write_text(
        "id_evento,red,estacion,fase\n"
        "E1,IU,ABC,P\n"
        "E1,IU,ABC,S\n"
        "E2,IU,DEF,P\n",
        encoding="utf-8")
    indice, campos, total = r._indexar_fases(str(ruta))
    assert campos == ["id_evento", "red", "estacion", "fase"]
    assert total == 3
    assert set(indice) == {"E1", "E2"}

    filas = r._leer_fases_de_evento(str(ruta), indice, campos, "E1")
    assert len(filas) == 2
    assert filas[0]["fase"] == "P"
    assert filas[1]["fase"] == "S"
    # Evento inexistente -> lista vacía.
    assert r._leer_fases_de_evento(str(ruta), indice, campos, "E9") == []


def test_id_de_primera_columna():
    assert r._id_de_primera_columna(b'E1,IU,ABC\n') == "E1"
    assert r._id_de_primera_columna(b'"E,1",IU,ABC\n') == "E,1"


# --------------------------------------------------------------------------
# Formateo
# --------------------------------------------------------------------------
def test_texto_y_numero():
    assert r._texto(None) == r.VACIO
    assert r._texto("  hola ") == "hola"
    assert r._texto("   ") == r.VACIO
    assert r._numero(None) == r.VACIO
    assert r._numero("") == r.VACIO
    assert r._numero("3.14159", 2) == "3.14"
    assert r._numero("3.0") == "3"
    assert r._numero("no numérico") == "no numérico"


def test_texto_modo_y_plurales():
    assert r._texto_modo("manual") == "manual"
    assert r._texto_modo("AUTOMATIC") == "automática"
    assert r._texto_modo("") == r.VACIO
    assert r._n_manual(1) == "1 manual"
    assert r._n_manual(2) == "2 manuales"
    assert r._n_auto(1) == "1 automática"
    assert r._n_auto(2) == "2 automáticas"


def test_conteo_modo_y_desglose_uso():
    filas = [{"modo_pick": "manual"}, {"modo_pick": "automatic"},
             {"modo_pick": "manual"}]
    assert r._conteo_modo(filas) == (2, 1)

    resumen = {"con_modo": True, "usadas": 2, "no_usadas": 1,
               "usadas_manual": 1, "usadas_auto": 1,
               "sin_usar_manual": 1, "sin_usar_auto": 0}
    assert r._desglose_uso(resumen) == \
        "2 usadas (1 manual, 1 automática), 1 sin usar (1 manual, 0 automáticas)"

    # Exportación vieja sin columna de modo -> texto clásico.
    resumen_viejo = {"con_modo": False, "usadas": 3, "no_usadas": 0}
    assert r._desglose_uso(resumen_viejo) == "3 usadas, 0 sin usar"


# --------------------------------------------------------------------------
# Agrupación y órdenes
# --------------------------------------------------------------------------
def test_agrupar_por_estacion():
    filas = [
        {"red": "IU", "estacion": "ABC", "azimut": "120"},
        {"red": "IU", "estacion": "ABC", "azimut": "30"},
        {"red": "CX", "estacion": "XYZ", "azimut": "0"},
    ]
    grupos = r._agrupar_por_estacion(filas)
    assert [g[0] for g in grupos] == [("CX", "XYZ"), ("IU", "ABC")]
    assert grupos[0][1] == "CX XYZ"
    # Dentro de la estación, ordenado por azimut.
    assert [f["azimut"] for f in grupos[1][2]] == ["30", "120"]


def test_a_float():
    assert r._a_float("1.5") == 1.5
    assert r._a_float("") == float("inf")
    assert r._a_float(None) == float("inf")
    assert r._a_float("x") == float("inf")


# --------------------------------------------------------------------------
# Sin arribos
# --------------------------------------------------------------------------
def test_ruta_no_picadas():
    assert r._ruta_no_picadas("datos/eventos.csv") == "datos/eventos_no_picadas.csv"
    assert r._ruta_no_picadas("datos/eventos") == "datos/eventos_no_picadas.csv"


@pytest.mark.parametrize("fila, esperado", [
    ({"actividad_ventana": "3", "distancia_km": "10"}, "destacada"),
    ({"actividad_ventana": "3", "distancia_km": "100"}, "activa"),
    ({"actividad_ventana": "0", "distancia_km": "10"}, "cercana"),
    ({"actividad_ventana": "0", "distancia_km": "100"}, "normal"),
    ({"distancia_km": "10"}, "cercana"),
])
def test_etiqueta_no_picada(fila, esperado):
    assert r._etiqueta_no_picada(fila) == esperado


def test_valores_no_picada():
    fila = {"distancia_km": "12.345", "red": "IU", "estacion": "ABC",
            "streams_vigentes": 2, "est_elev": "1500"}
    valores = r._valores_no_picada(fila)
    assert len(valores) == len(r.COLUMNAS_NO_PICADA)
    assert valores[0] == "12.3"
    assert valores[1] == "IU"
    assert valores[5] == "2"
    assert valores[7] == "1500"


# --------------------------------------------------------------------------
# Resumen de fases y valores de árboles
# --------------------------------------------------------------------------
def _fases_ejemplo():
    return [
        {"red": "IU", "estacion": "ABC", "usada": "true", "modo_pick": "manual",
         "azimut": "30", "tiene_magnitud": "Si", "mag_estacion": "4.1",
         "tipo_mag_estacion": "ML", "mag_est_residuo": "0.1"},
        {"red": "IU", "estacion": "ABC", "usada": "false",
         "modo_pick": "automatic", "azimut": "40", "tiene_magnitud": "No",
         "mag_est_residuo": ""},
        {"red": "CX", "estacion": "XYZ", "usada": "true",
         "modo_pick": "automatic", "azimut": "10", "tiene_magnitud": "Si",
         "mag_estacion": "4.5", "tipo_mag_estacion": "ML",
         "mag_est_residuo": "0.2"},
    ]


def test_resumen_fases():
    r_ = r._resumen_fases(_fases_ejemplo())
    assert r_["fases"] == 3
    assert r_["estaciones"] == 2
    assert r_["usadas"] == 2
    assert r_["no_usadas"] == 1
    assert r_["con_magnitud"] == 2
    assert r_["con_residuo"] == 2
    assert r_["con_modo"] == 3
    assert r_["mag_promedio"] == pytest.approx(4.3)


def test_encabezado_estacion():
    texto = r._encabezado_estacion("IU ABC", _fases_ejemplo()[:2])
    assert texto.startswith("IU ABC")
    assert "2 llegadas" in texto
    assert "usadas 1" in texto


def test_valores_fase_orden_y_pegado_de_microsegundos():
    fila = {"fase": "P", "llegada_utc": "2026-09-04 06:48:08",
            "llegada_us": "123456", "usada": "true", "modo_pick": "manual"}
    valores = r._valores_fase(fila)
    assert len(valores) == len(r.COLUMNAS_FASE)
    assert valores[0] == "P"
    assert valores[1] == "2026-09-04 06:48:08.123456"
    assert valores[7] == "sí"
    assert valores[8] == "manual"

    con_est = r._valores_fase_con_estacion(
        {"red": "IU", "estacion": "ABC", "fase": "P"})
    assert con_est[0] == "IU ABC"
    assert len(con_est) == len(r.COLUMNAS_FASE) + 1


def test_valores_evento():
    ev = {"ot_utc": "2026-09-04 06:48:08", "id_evento": "E1",
          "magnitud": "4.2", "latitud": "-26.155641555786133",
          "longitud": "-70.5", "profundidad_km": "35.0"}
    valores = r._valores_evento(ev)
    assert len(valores) == len(r.COLUMNAS_EVENTO)
    assert valores[0] == "2026-09-04"
    assert valores[1] == "06:48:08"
    assert valores[2] == "E1"
    assert valores[6] == "-26.156"
    assert valores[7] == "-70.500"


def test_parametros_evento_en_linea():
    ev = {"ot_utc": "2026-09-04 06:48:08", "magnitud": "4.2",
          "tipo_magnitud": "ML", "profundidad_km": "35.0",
          "latitud": "-26.1556", "longitud": "-70.5", "region": "Costa",
          "agencia": "CSN"}
    linea = r._parametros_evento_en_linea(ev)
    assert "2026-09-04 06:48:08" in linea
    assert "M4.2 ML" in linea
    assert "Prof 35.0 km" in linea
    assert "Costa" in linea
    # El analista no va en esta línea (se muestra aparte).
    assert r._analista_del_evento({"operador": "AB"}) == "AB"


# --------------------------------------------------------------------------
# Filtrado
# --------------------------------------------------------------------------
def test_texto_filtrable_descarta_vacio():
    assert r._texto_filtrable(["Hola", r.VACIO, "Mundo"]) == "hola mundo"


@pytest.mark.parametrize("valor, token, esperado", [
    ("-26.999", "-26", True),
    ("-25.74", "-26", False),
    ("-25.9996", "-26", True),
    ("-26.155641555786133", "-26.156", True),
    ("-26.2", "-26.156", False),
    ("no numérico", "-26", False),
])
def test_banda_numero(valor, token, esperado):
    assert r._banda_numero(valor, token) is esperado


def _valores_simples(fila):
    return [fila.get("id_evento", ""), fila.get("region", "")]


def test_filtrar_listado_por_texto_y_magnitud():
    filas = [
        {"id_evento": "E1", "region": "Costa", "magnitud": "4.2",
         "latitud": "-26.15"},
        {"id_evento": "E2", "region": "Mar", "magnitud": "2.0",
         "latitud": "-33.0"},
        {"id_evento": "E3", "region": "Costa", "magnitud": "",
         "latitud": "-26.15"},
    ]
    sel = r._filtrar_listado(filas, _valores_simples, texto="costa")
    assert [f["id_evento"] for f in sel] == ["E1", "E3"]

    # mag_min descarta los eventos sin magnitud.
    sel = r._filtrar_listado(filas, _valores_simples, mag_min=3.0,
                             clave_mag="magnitud")
    assert [f["id_evento"] for f in sel] == ["E1"]

    # Latitud como banda de grado.
    sel = r._filtrar_listado(filas, _valores_simples, lat="-26")
    assert [f["id_evento"] for f in sel] == ["E1", "E3"]


def test_filtrar_listado_extra():
    filas = [{"id_evento": "E1", "agencia": "CSN"}]
    sel = r._filtrar_listado(filas, _valores_simples, texto="csn",
                             extra=("agencia",))
    assert len(sel) == 1


# --------------------------------------------------------------------------
# No actualizados
# --------------------------------------------------------------------------
def test_valores_no_actualizado_normaliza_menos_cero():
    fila = {"fecha_local": "2026-09-04 06:48:08", "lat_local": "-26.1",
            "dlat": "-0.0", "dist_km": "12.345"}
    valores = r._valores_no_actualizado(fila)
    assert len(valores) == len(r.COLUMNAS_NO_ACTUALIZADO)
    idx_dlat = [c[0] for c in r.COLUMNAS_NO_ACTUALIZADO].index("dlat")
    assert valores[idx_dlat] == "0"


def test_discrepancias():
    fila = {"lat_eventquery": "-26.0", "lon_eventquery": "-70.0",
            "prof_eventquery": "35.0", "mag_eventquery": "4.2",
            "lat_local": "-26.5", "lon_local": "-70.0",
            "prof_local": "35.0", "mag_local": "4.2"}
    assert r._discrepancias(fila) == ["lat"]


# --------------------------------------------------------------------------
# Fechas e elección de la exportación
# --------------------------------------------------------------------------
@pytest.mark.parametrize("texto, esperado", [
    ("2026-09-04T06:48:08", datetime(2026, 9, 4, 6, 48, 8)),
    ("2026-09-04 06:48:08", datetime(2026, 9, 4, 6, 48, 8)),
    ("2026-09-04T06:48:08Z", datetime(2026, 9, 4, 6, 48, 8)),
    ("basura", None),
    ("", None),
    (None, None),
])
def test_parsear_instante(texto, esperado):
    assert r._parsear_instante(texto) == esperado


def test_ventana_del_nombre():
    nombre = "seiscomp_20260901000000_20260930235959.csv"
    assert r._ventana_del_nombre(nombre) == (
        datetime(2026, 9, 1, 0, 0, 0), datetime(2026, 9, 30, 23, 59, 59))
    assert r._ventana_del_nombre("sinfecha.csv") is None
    assert r._ventana_del_nombre("a_b.csv") is None


def test_ventana_del_catalogo(tmp_path):
    ruta = tmp_path / "catalogo.csv"
    ruta.write_text(
        "time,lat,lon\n"
        "2026-09-05T00:00:00Z,-26.0,-70.0\n"
        "2026-09-01T00:00:00Z,-26.1,-70.1\n"
        "2026-09-30T12:00:00Z,-26.2,-70.2\n",
        encoding="utf-8")
    assert r._ventana_del_catalogo(str(ruta)) == (
        datetime(2026, 9, 1, 0, 0, 0), datetime(2026, 9, 30, 12, 0, 0))
    # Sin columna de tiempo -> None.
    otra = tmp_path / "sin_tiempo.csv"
    otra.write_text("a,b\n1,2\n", encoding="utf-8")
    assert r._ventana_del_catalogo(str(otra)) is None


def test_catalogo_disponible_ignora_seiscomp_y_datos(tmp_path):
    (tmp_path / "catalogo.csv").write_text(
        "time,lat\n2026-09-01T00:00:00Z,-26.0\n", encoding="utf-8")
    (tmp_path / "seiscomp_20260901000000_20260930235959.csv").write_text(
        "time,lat\n2026-09-01T00:00:00Z,-26.0\n", encoding="utf-8")
    (tmp_path / "datos").mkdir()
    (tmp_path / "datos" / "otro.csv").write_text(
        "time,lat\n2026-09-01T00:00:00Z,-26.0\n", encoding="utf-8")
    elegido = r._catalogo_disponible(str(tmp_path))
    assert elegido == str(tmp_path / "catalogo.csv")


def test_elegir_par_por_solapamiento():
    pares = [
        {"eventos": "seiscomp_20260801000000_20260831235959.csv"},
        {"eventos": "seiscomp_20260901000000_20260930235959.csv"},
    ]
    ventana = (datetime(2026, 9, 10), datetime(2026, 9, 20))
    elegido = r._elegir_par(pares, ventana)
    assert elegido["eventos"].startswith("seiscomp_20260901")

    # Sin solapamiento -> None (no cae a la más reciente).
    sin_choque = (datetime(2026, 1, 1), datetime(2026, 1, 31))
    assert r._elegir_par(pares, sin_choque) is None
    # Sin ventana -> el primero.
    assert r._elegir_par(pares, None) == pares[0]


def test_cobertura():
    cat = (datetime(2026, 9, 1), datetime(2026, 9, 30))
    par = (datetime(2026, 9, 10), datetime(2026, 10, 10))
    inicio, fin, fraccion = r._cobertura(par, cat)
    assert inicio == datetime(2026, 9, 10)
    assert fin == datetime(2026, 9, 30)
    assert fraccion == pytest.approx(20.0 / 29.0, abs=1e-3)
    # Sin par -> (None, None, 0.0).
    assert r._cobertura(None, cat) == (None, None, 0.0)
