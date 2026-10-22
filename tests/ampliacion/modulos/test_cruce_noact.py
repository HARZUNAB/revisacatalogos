#!/usr/bin/env python3
"""
Tests de cruce_noact.py
=======================
Cubre la clasificación de «No actualizados»: candidata única, fuentes
empatadas, una fuente claramente más cerca, duplicados públicos y los motivos
por los que no se puede evaluar.
"""

import datetime
import os

import cruce_noact as cn


def _fila(**cambios):
    fila = {
        "fecha_eventquery": "2026-09-05 00:00:00",
        "lat_eventquery": "-33.000", "lon_eventquery": "-71.000",
        "prof_eventquery": "30.0", "mag_eventquery": "5.0",
        "fecha_local": "2026-09-05 00:00:02",
        "lat_local": "-33.000", "lon_local": "-71.000",
        "prof_local": "30.0", "mag_local": "5.5",
        "dt_seg": "2.0", "dist_km": "0.0",
    }
    fila.update(cambios)
    return fila


def _anotar(fila, propias=None, otras=None, motivo=None):
    propias = [fila] if propias is None else propias
    otras = [] if otras is None else otras
    filas = [fila]
    cn.anotar(filas, propias, otras, "seiscomp", motivo)
    return fila


def test_candidata_unica_es_esta_fuente_y_alta():
    fila = _anotar(_fila())
    assert fila["publicacion_probable"] == "Esta fuente"
    assert fila["revision"] == "Alta"
    assert fila["revision_orden"] == 1


def test_ambas_fuentes_igual_de_cerca_es_compartida():
    propia = _fila()
    otra = _fila(mag_local="5.5")
    fila = _anotar(propia, propias=[propia], otras=[otra])
    assert fila["publicacion_probable"] == "Compartida"
    assert fila["revision"] == "Media"


def test_esta_fuente_mas_cerca_es_alta():
    propia = _fila(mag_local="5.0")
    otra = _fila(mag_local="5.5")
    fila = _anotar(propia, propias=[propia], otras=[otra])
    assert fila["publicacion_probable"] == "Esta fuente"
    assert fila["revision"] == "Alta"


def test_otra_fuente_mas_cerca_es_baja():
    propia = _fila(mag_local="5.5")
    otra = _fila(mag_local="5.0")
    fila = _anotar(propia, propias=[propia], otras=[otra])
    assert fila["publicacion_probable"] == "Otra fuente"
    assert fila["revision"] == "Baja"


def test_duplicado_publico_es_alta_aunque_falte_la_otra_atribucion():
    propia = _fila()
    duplicado = _fila(fecha_eventquery="2026-09-05 00:00:01",
                      lat_eventquery="-33.100", lon_eventquery="-71.100")
    fila = _anotar(propia, propias=[propia, duplicado], motivo="sin datos")
    assert fila["publicacion_probable"] == "Duplicado público"
    assert fila["revision"] == "Alta"


def test_misma_clave_publicada_en_las_dos_fuentes_no_es_duplicado():
    propia = _fila()
    otra = _fila(mag_local="5.5")
    fila = _anotar(propia, propias=[propia], otras=[otra])
    assert fila["publicacion_probable"] == "Compartida"


def test_misma_fila_con_coordenadas_levemente_distintas_no_es_duplicado():
    # Cada atribución puede redondear la fila de eventquery un poco distinto;
    # eso no convierte el mismo sismo en un duplicado público.
    propia = _fila()
    otra = _fila(lat_eventquery="-33.010", lon_eventquery="-71.010",
                 mag_local="5.5")
    fila = _anotar(propia, propias=[propia], otras=[otra])
    assert fila["publicacion_probable"] != "Duplicado público"


def test_motivo_sin_duplicado_es_no_evaluable():
    fila = _anotar(_fila(), motivo="falta la atribución de Seisan")
    assert fila["publicacion_probable"] == "No evaluable"
    assert fila["revision"] == "—"
    assert "falta" in fila["revision_motivo"]


def test_orden_de_revision_es_numerico():
    fila = _anotar(_fila(), motivo="sin datos")
    assert fila["revision_orden"] == 4


def test_cargar_otra_falta_atribucion(tmp_path):
    filas, motivo = cn.cargar_otra(str(tmp_path), "seiscomp")
    assert filas == []
    assert "falta" in motivo


def test_cargar_otra_catalogo_vacio(tmp_path):
    datos = tmp_path / "datos"
    datos.mkdir()
    (datos / "atribucion_seisan.csv").write_text(
        "fecha_local,lat_local,lon_local\n", encoding="utf-8")
    (datos / "salida_collect.csv").write_text(
        "Fecha_Hora,Latitud,Longitud\n", encoding="utf-8")
    filas, motivo = cn.cargar_otra(str(tmp_path), "seiscomp")
    assert filas == []
    assert "sin datos" in motivo


def test_cargar_otra_desactualizada(tmp_path):
    datos = tmp_path / "datos"
    datos.mkdir()
    catalogo = datos / "salida_collect.csv"
    atribucion = datos / "atribucion_seisan.csv"
    catalogo.write_text(
        "Fecha_Hora,Latitud,Longitud\n2026-01-01 00:00:00,-33.0,-71.0\n",
        encoding="utf-8")
    atribucion.write_text(
        "fecha_local,lat_local,lon_local\n", encoding="utf-8")
    os.utime(catalogo, (2000, 2000))
    os.utime(atribucion, (1000, 1000))
    filas, motivo = cn.cargar_otra(str(tmp_path), "seiscomp")
    assert filas == []
    assert "desactualizada" in motivo


def test_cargar_otra_vigente(tmp_path):
    datos = tmp_path / "datos"
    datos.mkdir()
    catalogo = datos / "salida_collect.csv"
    atribucion = datos / "atribucion_seisan.csv"
    catalogo.write_text(
        "Fecha_Hora,Latitud,Longitud\n2026-01-01 00:00:00,-33.0,-71.0\n",
        encoding="utf-8")
    atribucion.write_text(
        "fecha_local,lat_local,lon_local\n"
        "2026-01-01 00:00:02,-33.0,-71.0\n", encoding="utf-8")
    os.utime(catalogo, (1000, 1000))
    os.utime(atribucion, (2000, 2000))
    filas, motivo = cn.cargar_otra(str(tmp_path), "seiscomp")
    assert motivo is None
    assert len(filas) == 1


def test_clusters_publicados_solo_agrupa_dentro_de_la_ventana():
    a = _fila(fecha_eventquery="2026-09-05 00:00:00")
    b = _fila(fecha_eventquery="2026-09-05 00:00:02")
    c = _fila(fecha_eventquery="2026-09-05 00:00:06")

    grupos = cn._clusters_publicados([a, b, c])

    assert grupos[cn._clave_publicado(a)][1] == 2
    assert grupos[cn._clave_publicado(c)][1] == 1


def test_clusters_publicados_encadena_duplicados_transitivos():
    a = _fila(fecha_eventquery="2026-09-05 00:00:00")
    b = _fila(fecha_eventquery="2026-09-05 00:00:02")
    c = _fila(fecha_eventquery="2026-09-05 00:00:04")

    grupos = cn._clusters_publicados([a, b, c])

    assert grupos[cn._clave_publicado(a)][1] == 3
    assert grupos[cn._clave_publicado(b)][1] == 3
    assert grupos[cn._clave_publicado(c)][1] == 3


def test_clusters_publicados_separa_por_coordenada():
    a = _fila(fecha_eventquery="2026-09-05 00:00:00")
    b = _fila(fecha_eventquery="2026-09-05 00:00:00",
              lat_eventquery="-35.000")

    grupos = cn._clusters_publicados([a, b])

    assert grupos[cn._clave_publicado(a)][1] == 1
    assert grupos[cn._clave_publicado(b)][1] == 1


def test_clusters_publicados_no_compara_pares_fuera_de_ventana(monkeypatch):
    llamadas = []
    original = cn._mismo_publicado

    def contar(a, b):
        llamadas.append((a, b))
        return original(a, b)

    monkeypatch.setattr(cn, "_mismo_publicado", contar)
    inicio = datetime.datetime(2026, 1, 1)
    filas = [
        _fila(fecha_eventquery=(inicio + datetime.timedelta(days=i)).strftime(
            "%Y-%m-%d %H:%M:%S"))
        for i in range(50)
    ]

    cn._clusters_publicados(filas)

    # Con el barrido temporal alcanza con comparar el vecino siguiente; el
    # recorrido de todos los pares haría 1.225 comparaciones.
    assert len(llamadas) <= len(filas)


def test_anotar_prefiere_la_candidata_del_mismo_evento_local():
    propia = _fila(lat_local="-33.000", lon_local="-71.000",
                   dist_km="1.0", mag_local="5.5")
    alternativa = _fila(lat_local="-33.500", lon_local="-71.000",
                        dist_km="100.0", mag_local="5.5")
    otra = _fila(mag_local="5.5", dist_km="50.0")
    resultado = dict(propia)

    cn.anotar([resultado], [propia, alternativa], [otra], "seiscomp")

    assert resultado["publicacion_probable"] == "Esta fuente"
    assert resultado["revision"] == "Alta"
