#!/usr/bin/env python3
"""
Tests de cruza_nopub.py
=======================
Cubre la confirmación de publicación en la otra fuente, la ventana de revisión
para casos ambiguos y la escritura de las columnas en los CSV. Son funciones
puras y escritura de archivos: no necesitan pantalla, base ni red.
"""

import csv
import os

import cruza_nopub

ENCABEZADO_NO_PUB = ["", "Fecha_Hora", "Latitud", "Longitud", "Prof.", "Mag.",
                     "Tipo_mag.", "Analista"]
ENCABEZADO_ATRIBUCION = ["fecha_local", "lat_local", "lon_local", "analista"]


def _asegurar_carpeta(ruta):
    carpeta = os.path.dirname(ruta)
    if carpeta:
        os.makedirs(carpeta, exist_ok=True)


def _escribir_no_pub(ruta, filas):
    _asegurar_carpeta(ruta)
    with open(ruta, "w", newline="", encoding="utf-8") as archivo:
        escritor = csv.writer(archivo)
        escritor.writerow(ENCABEZADO_NO_PUB)
        for i, fila in enumerate(filas):
            escritor.writerow([i] + list(fila))


def _escribir_atribucion(ruta, filas):
    _asegurar_carpeta(ruta)
    with open(ruta, "w", newline="", encoding="utf-8") as archivo:
        escritor = csv.writer(archivo)
        escritor.writerow(ENCABEZADO_ATRIBUCION)
        escritor.writerows(filas)


def _escribir_catalogo(ruta, filas=None):
    _asegurar_carpeta(ruta)
    with open(ruta, "w", newline="", encoding="utf-8") as archivo:
        escritor = csv.writer(archivo)
        escritor.writerow(ENCABEZADO_NO_PUB)
        for i, fila in enumerate(filas or []):
            escritor.writerow([i] + list(fila))


def _fila_catalogo(fecha="2026-01-01  00:00:00", lat="-33.000",
                   lon="-71.000", analista="fuente"):
    return [fecha, lat, lon, "10.0", "3.0", "ML", analista]


def _escribir_informe(ruta):
    _asegurar_carpeta(ruta)
    with open(ruta, "w", encoding="utf-8") as archivo:
        archivo.write("fecha hora latitud longitud prof mag tipomag analista "
                      "percibido\n")


def _fijar_mtime(ruta, instante):
    os.utime(ruta, (instante, instante))


def _leer(ruta):
    with open(ruta, encoding="utf-8", newline="") as archivo:
        return list(csv.reader(archivo))


def _evento(fecha="2026-01-01  00:00:00", lat="-33.000", lon="-71.000"):
    return {"Fecha_Hora": fecha, "Latitud": lat, "Longitud": lon}


def _candidato(fecha="2026-01-01 00:00:00", lat="-33.000", lon="-71.000",
               analista="ana"):
    return {"fecha_local": fecha, "lat_local": lat, "lon_local": lon,
            "analista": analista}


def _evaluar(evento, filas, etiqueta="SeisComp"):
    candidatos = cruza_nopub.preparar_candidatos(filas)
    return cruza_nopub.evaluar_evento(evento, candidatos, etiqueta)


# --------------------------------------------------------------------------
# evaluar_evento: confirmación, revisión y estados
# --------------------------------------------------------------------------
def test_confirmacion_exacta():
    resultado = _evaluar(_evento(), [_candidato()])
    assert resultado["publicado_en"] == "SeisComp"
    assert resultado["estado"] == "Publicado en SeisComp"
    assert resultado["dt_seg"] == 0.0
    assert resultado["dist_km"] == 0.0
    assert resultado["analista"] == "ana"


def test_confirmacion_en_los_limites():
    # 6 s y 0.5° exactos confirman.
    en_limite = _candidato(fecha="2026-01-01 00:00:06", lat="-33.500")
    resultado = _evaluar(_evento(), [en_limite])
    assert resultado["publicado_en"] == "SeisComp"


def test_par_real_con_diferencia_de_0411_grados_confirma():
    # Caso real: mismo evento, 0.411° de diferencia en longitud.
    evento = _evento(lat="-41.550", lon="-73.853")
    candidato = _candidato(fecha="2026-01-01 00:00:03",
                           lat="-41.573", lon="-74.264")
    resultado = _evaluar(evento, [candidato])
    assert resultado["publicado_en"] == "SeisComp"


def test_fuera_de_confirmacion_pero_en_revision_es_candidato():
    # 6.1 s: sale de confirmación pero sigue en la ventana de revisión.
    resultado = _evaluar(_evento(), [
        _candidato(fecha="2026-01-01 00:00:06.1")])
    assert resultado["publicado_en"] == ""
    assert resultado["estado"] == "Candidato en SeisComp"
    assert resultado["dt_seg"] == 6.1

    # 0.5001°: mismo caso por espacio.
    resultado = _evaluar(_evento(), [_candidato(lat="-33.5001")])
    assert resultado["publicado_en"] == ""
    assert resultado["estado"] == "Candidato en SeisComp"


def test_fuera_de_revision_es_sin_coincidencia():
    resultado = _evaluar(_evento(), [
        _candidato(fecha="2026-01-01 00:02:01")])
    assert resultado["publicado_en"] == ""
    assert resultado["estado"] == "Sin coincidencia"
    assert resultado["dt_seg"] == ""
    assert resultado["dist_km"] == ""
    assert resultado["analista"] == ""


def test_varios_confirmados_es_ambiguo():
    resultado = _evaluar(_evento(), [
        _candidato(fecha="2026-01-01 00:00:02", lat="-33.100",
                   analista="segundo"),
        _candidato(fecha="2026-01-01 00:00:01", lat="-33.000",
                   analista="primero"),
    ])
    assert resultado["publicado_en"] == ""
    assert resultado["estado"] == "Ambiguo: 2 candidatos en SeisComp"
    # El diagnóstico sale del más cercano.
    assert resultado["dt_seg"] == 1.0
    assert resultado["analista"] == "primero"


def test_un_candidato_en_revision_es_candidato():
    resultado = _evaluar(_evento(), [
        _candidato(fecha="2026-01-01 00:00:30", lat="-33.300")])
    assert resultado["publicado_en"] == ""
    assert resultado["estado"] == "Candidato en SeisComp"
    assert resultado["dt_seg"] == 30.0
    assert resultado["dist_km"] > 0


def test_varios_en_revision_es_ambiguo():
    resultado = _evaluar(_evento(), [
        _candidato(fecha="2026-01-01 00:00:30", lat="-33.100"),
        _candidato(fecha="2026-01-01 00:00:20", lat="-33.200"),
    ])
    assert resultado["publicado_en"] == ""
    assert resultado["estado"] == "Ambiguo: 2 candidatos en SeisComp"
    assert resultado["dt_seg"] == 20.0


def test_deduplica_la_misma_solucion():
    # Dos filas del mismo cruce no convierten un caso único en ambiguo.
    fila = _candidato()
    resultado = _evaluar(_evento(), [fila, dict(fila)])
    assert resultado["publicado_en"] == "SeisComp"
    assert resultado["estado"] == "Publicado en SeisComp"


def test_preparar_candidatos_ignora_invalidos():
    candidatos = cruza_nopub.preparar_candidatos([
        {"fecha_local": "", "lat_local": "-33", "lon_local": "-71"},
        {"fecha_local": "2026-01-01 00:00:00", "lat_local": "",
         "lon_local": "-71"},
        _candidato(),
    ])
    assert len(candidatos) == 1


def test_evento_sin_datos_es_sin_coincidencia():
    resultado = _evaluar(
        {"Fecha_Hora": "", "Latitud": "-33", "Longitud": "-71"},
        [_candidato()])
    assert resultado["estado"] == "Sin coincidencia"


# --------------------------------------------------------------------------
# anotar
# --------------------------------------------------------------------------
def test_anotar_agrega_columnas_sin_tocar_las_existentes(cwd_tmp):
    ruta_no_pub = "datos/no_pub.csv"
    ruta_atr = "datos/atribucion_seiscomp.csv"
    ruta_catalogo = "datos/seiscomp_parametros.csv"
    _escribir_no_pub(ruta_no_pub, [
        ["2026-01-01  00:00:00", "-33.000", "-71.000", "30.0", "5.0",
         "ML", "seis"],
        ["2026-01-02  00:00:00", "-34.000", "-72.000", "20.0", "4.0",
         "ML", "otro"],
    ])
    _escribir_atribucion(ruta_atr, [
        ["2026-01-01 00:00:02", "-33.010", "-71.010", "ana"],
    ])
    _escribir_catalogo(ruta_catalogo, [_fila_catalogo()])
    _fijar_mtime(ruta_catalogo, 100)
    _fijar_mtime(ruta_atr, 200)

    resumen = cruza_nopub.anotar(ruta_no_pub, ruta_atr, "SeisComp",
                                 ruta_catalogo)
    assert resumen == {"total": 2, "publicados": 1, "ambiguos": 0,
                       "candidatos": 0, "sin_coincidencia": 1,
                       "no_evaluables": 0}

    filas = _leer(ruta_no_pub)
    assert filas[0][:8] == ENCABEZADO_NO_PUB
    assert filas[0][8:] == list(cruza_nopub.COLUMNAS_NUEVAS)
    # Las columnas originales conservan su orden y sus valores.
    assert filas[1][1:8] == ["2026-01-01  00:00:00", "-33.000", "-71.000",
                             "30.0", "5.0", "ML", "seis"]
    assert filas[1][8] == "SeisComp"
    assert filas[1][9] == "Publicado en SeisComp"
    assert filas[1][10] == "2.0"
    assert filas[1][11] != ""
    assert filas[1][12] == "ana"
    # El segundo evento no tiene coincidencia.
    assert filas[2][8:] == ["", "Sin coincidencia", "", "", ""]
    assert len(filas) == 3


def test_anotar_reporta_ambiguos_y_candidatos(cwd_tmp):
    ruta_no_pub = "datos/no_pub.csv"
    ruta_atr = "datos/atribucion_seiscomp.csv"
    ruta_catalogo = "datos/seiscomp_parametros.csv"
    _escribir_no_pub(ruta_no_pub, [
        ["2026-01-01  00:00:00", "-33.000", "-71.000", "30.0", "5.0",
         "ML", "seis"],
        ["2026-01-02  00:00:00", "-34.000", "-72.000", "20.0", "4.0",
         "ML", "otro"],
    ])
    _escribir_atribucion(ruta_atr, [
        ["2026-01-01 00:00:01", "-33.000", "-71.000", "uno"],
        ["2026-01-01 00:00:02", "-33.100", "-71.100", "dos"],
        ["2026-01-02 00:00:30", "-34.000", "-72.000", "tres"],
    ])
    _escribir_catalogo(ruta_catalogo, [_fila_catalogo()])
    _fijar_mtime(ruta_catalogo, 100)
    _fijar_mtime(ruta_atr, 200)

    resumen = cruza_nopub.anotar(ruta_no_pub, ruta_atr, "SeisComp",
                                 ruta_catalogo)
    assert resumen == {"total": 2, "publicados": 0, "ambiguos": 1,
                       "candidatos": 1, "sin_coincidencia": 0,
                       "no_evaluables": 0}


def test_anotar_es_idempotente(cwd_tmp):
    ruta_no_pub = "datos/no_pub.csv"
    ruta_atr = "datos/atribucion_seiscomp.csv"
    ruta_catalogo = "datos/seiscomp_parametros.csv"
    _escribir_no_pub(ruta_no_pub, [
        ["2026-01-01  00:00:00", "-33.000", "-71.000", "30.0", "5.0",
         "ML", "seis"],
    ])
    _escribir_atribucion(ruta_atr, [
        ["2026-01-01 00:00:01", "-33.000", "-71.000", "ana"],
    ])
    _escribir_catalogo(ruta_catalogo, [_fila_catalogo()])
    _fijar_mtime(ruta_catalogo, 100)
    _fijar_mtime(ruta_atr, 200)

    cruza_nopub.anotar(ruta_no_pub, ruta_atr, "SeisComp", ruta_catalogo)
    primera = _leer(ruta_no_pub)
    cruza_nopub.anotar(ruta_no_pub, ruta_atr, "SeisComp", ruta_catalogo)
    segunda = _leer(ruta_no_pub)

    assert primera == segunda
    for columna in cruza_nopub.COLUMNAS_NUEVAS:
        assert segunda[0].count(columna) == 1


def test_anotar_no_usa_atribucion_vieja(cwd_tmp):
    ruta_no_pub = "datos/no_pub.csv"
    ruta_atr = "datos/atribucion_seiscomp.csv"
    ruta_catalogo = "datos/seiscomp_parametros.csv"
    _escribir_no_pub(ruta_no_pub, [
        ["2026-01-01  00:00:00", "-33.000", "-71.000", "30.0", "5.0",
         "ML", "seis"],
    ])
    _escribir_atribucion(ruta_atr, [
        ["2026-01-01 00:00:01", "-33.000", "-71.000", "ana"],
    ])
    _escribir_catalogo(ruta_catalogo, [_fila_catalogo()])
    # La atribución es MÁS VIEJA que el catálogo: no se debe usar.
    _fijar_mtime(ruta_atr, 100)
    _fijar_mtime(ruta_catalogo, 200)

    resumen = cruza_nopub.anotar(ruta_no_pub, ruta_atr, "SeisComp",
                                 ruta_catalogo)
    assert resumen["publicados"] == 0
    assert resumen["no_evaluables"] == 1
    assert _leer(ruta_no_pub)[1][8:] == [
        "", "No evaluable: atribución de SeisComp desactualizada", "", "", ""]


def test_anotar_sin_atribucion_deja_sin_coincidencia(cwd_tmp):
    ruta_no_pub = "datos/no_pub.csv"
    _escribir_no_pub(ruta_no_pub, [
        ["2026-01-01  00:00:00", "-33.000", "-71.000", "30.0", "5.0",
         "ML", "seis"],
    ])
    resumen = cruza_nopub.anotar(ruta_no_pub, "datos/no_existe.csv",
                                 "Seisan")
    assert resumen["sin_coincidencia"] == 1
    filas = _leer(ruta_no_pub)
    assert filas[0][8:] == list(cruza_nopub.COLUMNAS_NUEVAS)
    assert filas[1][8:] == ["", "Sin coincidencia", "", "", ""]


def test_anotar_limpia_marcas_de_una_corrida_anterior(cwd_tmp):
    ruta_no_pub = "datos/no_pub.csv"
    _asegurar_carpeta(ruta_no_pub)
    with open(ruta_no_pub, "w", newline="", encoding="utf-8") as archivo:
        escritor = csv.writer(archivo)
        escritor.writerow(ENCABEZADO_NO_PUB + list(cruza_nopub.COLUMNAS_NUEVAS))
        escritor.writerow([0, "2026-01-01  00:00:00", "-33.000", "-71.000",
                           "30.0", "5.0", "ML", "seis", "Seisan",
                           "Publicado en Seisan", "1.0", "2.0", "viejo"])
    cruza_nopub.anotar(ruta_no_pub, "datos/no_existe.csv", "SeisComp")
    filas = _leer(ruta_no_pub)
    for columna in cruza_nopub.COLUMNAS_NUEVAS:
        assert filas[0].count(columna) == 1
    assert filas[1][8:] == ["", "Sin coincidencia", "", "", ""]


def test_anotar_sin_datos_de_la_otra_fuente(cwd_tmp):
    ruta_no_pub = "datos/no_pub.csv"
    ruta_atr = "datos/atribucion_seiscomp.csv"
    ruta_catalogo = "datos/seiscomp_parametros.csv"
    _escribir_no_pub(ruta_no_pub, [
        ["2026-01-01  00:00:00", "-33.000", "-71.000", "30.0", "5.0",
         "ML", "seis"],
    ])
    _escribir_atribucion(ruta_atr, [
        ["2026-01-01 00:00:01", "-33.000", "-71.000", "ana"],
    ])
    _escribir_catalogo(ruta_catalogo)  # solo encabezado
    _fijar_mtime(ruta_catalogo, 100)
    _fijar_mtime(ruta_atr, 200)

    resumen = cruza_nopub.anotar(ruta_no_pub, ruta_atr, "SeisComp",
                                 ruta_catalogo)
    assert resumen["no_evaluables"] == 1
    assert _leer(ruta_no_pub)[1][8:] == [
        "", "No evaluable: sin datos de SeisComp en la ventana", "", "", ""]


def test_anotar_sin_catalogo_publicado(cwd_tmp):
    ruta_no_pub = "datos/no_pub.csv"
    ruta_atr = "datos/atribucion_seiscomp.csv"
    ruta_catalogo = "datos/seiscomp_parametros.csv"
    ruta_publicado = "datos/new_2_prueba.csv"
    _escribir_no_pub(ruta_no_pub, [
        ["2026-01-01  00:00:00", "-33.000", "-71.000", "30.0", "5.0",
         "ML", "seis"],
    ])
    _escribir_atribucion(ruta_atr, [
        ["2026-01-01 00:00:01", "-33.000", "-71.000", "ana"],
    ])
    _escribir_catalogo(ruta_catalogo, [_fila_catalogo()])
    _escribir_no_pub(ruta_publicado, [])  # solo encabezado
    _fijar_mtime(ruta_catalogo, 100)
    _fijar_mtime(ruta_atr, 200)

    resumen = cruza_nopub.anotar(
        ruta_no_pub, ruta_atr, "SeisComp", ruta_catalogo,
        ruta_publicado=ruta_publicado)
    assert resumen["no_evaluables"] == 1
    assert _leer(ruta_no_pub)[1][8:] == [
        "", "No evaluable: sin catálogo publicado (eventquery)", "", "", ""]


def test_anotar_sin_comparacion_no_es_sin_coincidencia(cwd_tmp):
    ruta_no_pub = "datos/no_pub.csv"
    ruta_catalogo = "datos/seiscomp_parametros.csv"
    _escribir_no_pub(ruta_no_pub, [
        ["2026-01-01  00:00:00", "-33.000", "-71.000", "30.0", "5.0",
         "ML", "seis"],
    ])
    _escribir_catalogo(ruta_catalogo, [_fila_catalogo()])
    _fijar_mtime(ruta_catalogo, 100)

    resumen = cruza_nopub.anotar(
        ruta_no_pub, "datos/no_existe.csv", "SeisComp", ruta_catalogo,
        ruta_informe="informes/no_act_seiscomp_estricto.txt")
    assert resumen["no_evaluables"] == 1
    assert _leer(ruta_no_pub)[1][8:] == [
        "", "No evaluable: no se comparó SeisComp", "", "", ""]


def test_anotar_sin_atribucion_pero_comparacion_vigente_es_sin_coincidencia(
        cwd_tmp):
    ruta_no_pub = "datos/no_pub.csv"
    ruta_catalogo = "datos/seiscomp_parametros.csv"
    ruta_informe = "informes/no_act_seiscomp_estricto.txt"
    _escribir_no_pub(ruta_no_pub, [
        ["2026-01-01  00:00:00", "-33.000", "-71.000", "30.0", "5.0",
         "ML", "seis"],
    ])
    _escribir_catalogo(ruta_catalogo, [_fila_catalogo()])
    _escribir_informe(ruta_informe)
    _fijar_mtime(ruta_catalogo, 100)
    _fijar_mtime(ruta_informe, 200)

    resumen = cruza_nopub.anotar(
        ruta_no_pub, "datos/no_existe.csv", "SeisComp", ruta_catalogo,
        ruta_informe=ruta_informe)
    assert resumen["sin_coincidencia"] == 1
    assert _leer(ruta_no_pub)[1][8:] == ["", "Sin coincidencia", "", "", ""]


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------
def test_main_anota_los_dos_listados(cwd_tmp, capsys):
    _escribir_no_pub("datos/no_pub_desde_2_5_estricto.csv", [
        ["2026-01-01  00:00:00", "-33.000", "-71.000", "30.0", "5.0",
         "ML", "seis"],
    ])
    _escribir_no_pub("datos/no_pub_desde_2_5_seiscomp_estricto.csv", [
        ["2026-01-01  00:00:01", "-33.010", "-71.010", "30.0", "5.1",
         "ML", "comp"],
    ])
    # Para el listado de Seisan, la otra fuente es SeisComp.
    _escribir_atribucion("datos/atribucion_seiscomp.csv", [
        ["2026-01-01 00:00:01", "-33.010", "-71.010", "comp"],
    ])
    # Para el listado de SeisComp, la otra fuente es Seisan.
    _escribir_atribucion("datos/atribucion_seisan.csv", [
        ["2026-01-01 00:00:00", "-33.000", "-71.000", "seis"],
    ])
    for catalogo in ("datos/seiscomp_parametros.csv",
                     "datos/salida_collect.csv"):
        _escribir_catalogo(catalogo, [_fila_catalogo()])
        _fijar_mtime(catalogo, 100)
    _escribir_no_pub("datos/new_2_prueba.csv", [
        ["2026-01-01  00:00:01", "-33.010", "-71.010", "30.0", "5.1",
         "ML", "comp"],
    ])
    for atribucion in ("datos/atribucion_seiscomp.csv",
                       "datos/atribucion_seisan.csv"):
        _fijar_mtime(atribucion, 200)
    for informe in ("informes/no_act_seiscomp_estricto.txt",
                    "informes/no_act_estricto.txt"):
        _escribir_informe(informe)
        _fijar_mtime(informe, 200)

    cruza_nopub.main()

    seisan = _leer("datos/no_pub_desde_2_5_estricto.csv")
    seiscomp = _leer("datos/no_pub_desde_2_5_seiscomp_estricto.csv")
    assert seisan[1][8] == "SeisComp"
    assert seisan[1][9] == "Publicado en SeisComp"
    assert seisan[1][12] == "comp"
    assert seiscomp[1][8] == "Seisan"
    assert seiscomp[1][9] == "Publicado en Seisan"
    assert seiscomp[1][12] == "seis"
    salida = capsys.readouterr().out
    assert "1 publicados en SeisComp" in salida
    assert "1 publicados en Seisan" in salida
