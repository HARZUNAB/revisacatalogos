#!/usr/bin/env python3
"""
Tests de app.py — ventanas de consulta
======================================
Cubre la construcción y el comportamiento de las ventanas "No actualizados",
"Catálogos", "Eventos repetidos" y "No publicados". **Interfaz real** (ventana
y builders reales) con **datos sintéticos**; solo se sustituye el diálogo de
descarga (messagebox modal, bloqueante). Necesita `DISPLAY`.

No se cubren el filtro por texto ni el orden por encabezado: son callbacks
internos que solo se disparan con eventos Tk (poco confiables en tests).
"""

import tkinter as tk
from tkinter import ttk

import pytest

pytest.importorskip("ttkbootstrap")
pytest.importorskip("matplotlib")
import app as appmod

pytestmark = pytest.mark.gui


def _toplevel(raiz, titulo):
    for w in raiz.winfo_children():
        if isinstance(w, tk.Toplevel) and w.title() == titulo:
            return w
    return None


def _buscar(widget, tipo, predicado=None):
    for hijo in widget.winfo_children():
        if isinstance(hijo, tipo) and (predicado is None or predicado(hijo)):
            return hijo
        encontrado = _buscar(hijo, tipo, predicado)
        if encontrado is not None:
            return encontrado
    return None


def _tab_texts(cuaderno):
    return [cuaderno.tab(t, "text") for t in cuaderno.tabs()]


def _escribir(cwd, rel, texto):
    ruta = cwd / rel
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(texto, encoding="utf-8")
    return ruta


def _boton(top, texto):
    return _buscar(top, ttk.Button, lambda w: w.cget("text") == texto)


# --------------------------------------------------------------------------
# Fixtures de datos (formato real de cada archivo)
# --------------------------------------------------------------------------
_ATRIBUCION = (
    "n_fila_eventquery,fecha_eventquery,lat_eventquery,lon_eventquery,"
    "prof_eventquery,mag_eventquery,tipo_mag_eventquery,percibido,fecha_local,"
    "lat_local,lon_local,prof_local,mag_local,tipo_mag_local,analista,dt_seg,"
    "dlat,dlon,dist_km,n_candidatos,fuente\n"
    "0,2026-09-05 00:00:00,-33.000,-71.000,30.0,5.0,ML,S,"
    "2026-09-05 00:00:02,-33.000,-71.000,30.0,5.5,ML,ana,2.0,0.000,0.000,,1,"
    "seiscomp\n")

_SALIDA_COLLECT = (
    ",Fecha_Hora,Latitud,Longitud,Prof.,Mag.,Tipo_mag.,Analista\n"
    "0,2026-09-05  00:00:02,-33.000,-71.000,30.0,5.5,ML,ana\n")

_NEW2_EVENTQUERY = (
    ",Fecha_Hora,Latitud,Longitud,Prof.,Mag.,Tipo_mag.,Referencia,Percep.\n"
    "0,2026-09-05  00:00:00,-33.000,-71.000,30.0,5.0,ML,REF1,S\n")

_EVENTOS_SEISCOMP = (
    "id_evento,id_origen,ot_utc,magnitud,tipo_magnitud,fases,rms,azgap,"
    "latitud,longitud,profundidad_km,agencia,operador,region,estatus,"
    "base_datos\n"
    "E1,O1,2026-09-05 00:00:00,5.0,ML,12,0.30,45,-33.000,-71.000,30.0,CSN,ana,"
    "Region,reviewed,seiscomp\n")

_FASES_SEISCOMP = (
    "id_evento,id_origen,id_pick,red,estacion,loc,cha,fase,llegada_utc,"
    "llegada_us,correccion_s,residual_s,azimut,distancia,usada,peso,polaridad,"
    "modo_pick,pick_autor,pick_agencia,pick_metodo,snr,mag_estacion,"
    "tipo_mag_estacion,tiene_magnitud,mag_est_residuo,qc_estacion,est_lat,"
    "est_lon,est_elev,est_lugar,est_pais,base_datos\n")

_ENTRADA = ("time,lat,lon\n"
            "2026-09-10T00:00:00Z,-33.0,-71.0\n"
            "2026-09-20T00:00:00Z,-33.1,-71.1\n")


def _par_seiscomp(cwd, ini="20260901000000", fin="20260930235959"):
    base = "datos/seiscomp_%s_%s" % (ini, fin)
    _escribir(cwd, base + ".csv", _EVENTOS_SEISCOMP)
    _escribir(cwd, base + "_fases.csv", _FASES_SEISCOMP)
    _escribir(cwd, base + ".csv.completo",
              "ventana %s %s | eventos 1 | fases 0 | no_picadas 0 | bases "
              "seiscomp\n" % (ini, fin))


# --------------------------------------------------------------------------
# No actualizados
# --------------------------------------------------------------------------
def test_no_actualizados_estructura(app_factory, raiz_gui, cwd_tmp):
    _, inst = app_factory()
    inst._ver_no_actualizados()
    top = _toplevel(raiz_gui, "No actualizados")
    assert top is not None
    cuaderno = _buscar(top, ttk.Notebook)
    assert _tab_texts(cuaderno) == ["SeisComp", "Seisan"]


def test_no_actualizados_builder_real(app_factory, raiz_gui, cwd_tmp):
    _, inst = app_factory()
    _escribir(cwd_tmp, "datos/atribucion_seiscomp.csv", _ATRIBUCION)
    _escribir(cwd_tmp, "datos/atribucion_seisan.csv", _ATRIBUCION)

    inst._ver_no_actualizados()

    top = _toplevel(raiz_gui, "No actualizados")
    cuaderno = _buscar(top, ttk.Notebook)
    # La pestaña por defecto (SeisComp) arma la tabla real.
    marco = cuaderno.nametowidget(cuaderno.tabs()[0])
    assert _buscar(marco, ttk.Treeview) is not None

    # Cambiar a Seisan también construye su tabla (perezoso).
    cuaderno.select(cuaderno.tabs()[1])
    cuaderno.event_generate("<<NotebookTabChanged>>")
    raiz_gui.update()
    marco_seisan = cuaderno.nametowidget(cuaderno.tabs()[1])
    assert _buscar(marco_seisan, ttk.Treeview) is not None


# --------------------------------------------------------------------------
# Catálogos
# --------------------------------------------------------------------------
def test_catalogos_estructura_y_reuso(app_factory, raiz_gui, cwd_tmp):
    _, inst = app_factory()
    inst._ver_catalogos()
    top = _toplevel(raiz_gui, "Catálogos")
    assert top is not None
    assert inst.marco_catalogos is top
    assert inst.seiscomp_frame is not None
    assert inst.seisan_frame is not None
    assert inst.eventquery_frame is not None
    assert _tab_texts(_buscar(top, ttk.Notebook)) == \
        ["SeisComp", "Seisan", "eventquery"]
    assert top.protocol("WM_DELETE_WINDOW")

    inst._ver_catalogos()
    toples = [w for w in raiz_gui.winfo_children()
              if isinstance(w, tk.Toplevel) and w.title() == "Catálogos"]
    assert len(toples) == 1
    assert inst.marco_catalogos is top


def test_catalogos_seisan_real(app_factory, raiz_gui, cwd_tmp):
    _, inst = app_factory()
    _escribir(cwd_tmp, "datos/salida_collect.csv", _SALIDA_COLLECT)
    inst._ver_catalogos()
    inst._construir_catalogo("seisan")
    assert inst.catalogos["seisan"]["construido"] is True
    assert _buscar(inst.seisan_frame, ttk.Treeview) is not None


def test_catalogos_eventquery_real(app_factory, raiz_gui, cwd_tmp):
    _, inst = app_factory()
    _escribir(cwd_tmp, "datos/new_2_prueba.csv", _NEW2_EVENTQUERY)
    inst._ver_catalogos()
    inst._construir_catalogo("eventquery")
    assert inst.catalogos["eventquery"]["construido"] is True
    assert _buscar(inst.eventquery_frame, ttk.Treeview) is not None


def test_catalogos_seiscomp_real(app_factory, raiz_gui, cwd_tmp):
    _, inst = app_factory()
    _escribir(cwd_tmp, "entrada.csv", _ENTRADA)
    _par_seiscomp(cwd_tmp)
    inst._ver_catalogos()
    assert inst.catalogos["seiscomp"]["construido"] is True
    assert _buscar(inst.seiscomp_frame, ttk.Treeview) is not None


def _buscar_todos(widget, tipo, encontrados=None):
    if encontrados is None:
        encontrados = []
    for hijo in widget.winfo_children():
        if isinstance(hijo, tipo):
            encontrados.append(hijo)
        _buscar_todos(hijo, tipo, encontrados)
    return encontrados


# --------------------------------------------------------------------------
# Repetidos
# --------------------------------------------------------------------------
_INFORME_PUBLICA = (
    "fecha_hora\tlatitud\tlongitud\tprof\tmag\ttipomag\treferencia\tpercibido\n"
    "2026-01-01 00:00:00\t-30.000\t-71.000\t50.0\t4.5\tML\tR1\tS\n"
    "2026-01-01 00:00:02\t-30.001\t-71.001\t50.0\t4.5\tML\tR2\tS\n")


def test_repetidos_con_informe(app_factory, raiz_gui, cwd_tmp, monkeypatch):
    _, inst = app_factory()
    _escribir(cwd_tmp, "informes/rep_publica_amplio.txt", _INFORME_PUBLICA)

    descargado = {}

    def exportar_listado(filas, valores, columnas, cwd, etiqueta, padre=None,
                         formato=None):
        descargado["filas"] = [valores(f) for f in filas]
        descargado["columnas"] = [c[0] for c in columnas]
        descargado["etiqueta"] = etiqueta
        return "datos/descarga.csv"

    import revisa_seiscomp
    monkeypatch.setattr(revisa_seiscomp, "_exportar_listado", exportar_listado)

    inst._ver_repetidos()

    top = _toplevel(raiz_gui, "Eventos repetidos")
    tablas = _buscar_todos(top, ttk.Treeview)
    lista, tabla = tablas[0], tablas[1]
    assert len(lista.get_children()) == len(appmod.REP_FILES)
    # La primera fila (rep_publica_amplio) tiene 2 eventos (no cuenta cabecera).
    primera = lista.get_children()[0]
    assert lista.item(primera, "values")[1] == "2"
    # La tabla del informe trae sus columnas más los dos analistas probables.
    assert "fecha_hora" in tabla["columns"]
    assert "analista_seisan" in tabla["columns"]
    assert "analista_seiscomp" in tabla["columns"]
    assert len(tabla.get_children()) == 2

    # «Descargar» baja lo filtrado por el exportador común (CSV/TXT + nombre).
    _boton(top, "Descargar").invoke()
    assert descargado["etiqueta"] == "rep_publica_amplio"
    assert "analista_seisan" in descargado["columnas"]
    assert descargado["filas"][0][:2] == ["2026-01-01 00:00:00", "-30.000"]


def test_repetidos_sin_archivos(app_factory, raiz_gui, cwd_tmp):
    _, inst = app_factory()
    inst._ver_repetidos()
    top = _toplevel(raiz_gui, "Eventos repetidos")
    tablas = _buscar_todos(top, ttk.Treeview)
    # Solo la lista de archivos: sin informe seleccionado no hay tabla.
    assert len(tablas) == 1
    valores = [tablas[0].item(i, "values") for i in tablas[0].get_children()]
    assert len(valores) == len(appmod.REP_FILES)
    assert all(v[1] == "0" for v in valores)


def test_repetidos_formato_viejo_cae_a_texto(app_factory, raiz_gui, cwd_tmp):
    _, inst = app_factory()
    # Informe viejo: separado por espacios, no se puede partir en columnas.
    _escribir(cwd_tmp, "informes/rep_publica_amplio.txt", "uno\ndos\n")
    inst._ver_repetidos()
    top = _toplevel(raiz_gui, "Eventos repetidos")
    # Solo la lista: el informe crudo se muestra como texto, sin tabla.
    assert len(_buscar_todos(top, ttk.Treeview)) == 1


def test_repetidos_analistas_probables_cruzan():
    indice = {"2026-01-01 00:00:00": [
        {"fecha_eventquery": "2026-01-01 00:00:00",
         "lat_eventquery": "-30.000", "lon_eventquery": "-71.000",
         "fuente": "seisan", "analista": "jere", "dt_seg": "1.5"}]}
    filas = [{"fecha_hora": "2026-01-01 00:00:00", "latitud": "-30.000",
              "longitud": "-71.000"}]
    appmod._analistas_probables_repetidos(filas, [("seisan", indice)])
    assert filas[0]["analista_seisan"] == "jere"


def test_leer_informe_repetidos_tabulado(cwd_tmp):
    ruta = _escribir(cwd_tmp, "rep.txt", _INFORME_PUBLICA)
    filas, crudo = appmod._leer_informe_repetidos(str(ruta))
    assert crudo is None
    assert len(filas) == 2
    assert filas[0]["referencia"] == "R1"


def test_leer_informe_repetidos_espacios_cae_a_crudo(cwd_tmp):
    ruta = _escribir(cwd_tmp, "rep.txt", "fecha hora lat\nuno dos tres\n")
    filas, crudo = appmod._leer_informe_repetidos(str(ruta))
    assert filas is None
    assert crudo[0] == "fecha hora lat"


def test_repetidos_columnas_por_informe():
    assert [c[0] for c in appmod._repetidos_columnas("x/rep_publica_amplio.txt")][
        -2:] == ["analista_seisan", "analista_seiscomp"]
    assert [c[0] for c in appmod._repetidos_columnas("x/rep_seisan_amplio.txt")] \
        == ["fecha_hora", "latitud", "longitud", "prof", "mag", "tipomag",
            "analista"]
    assert [c[0] for c in appmod._repetidos_columnas(
        "x/rep_seisan_exclu.txt")] == ["fecha_hora", "analista"]


# --------------------------------------------------------------------------
# No publicados
# --------------------------------------------------------------------------
_CSV_NO_PUB = (
    ",Fecha_Hora,Latitud,Longitud,Prof.,Mag.,Tipo_mag.,Analista\n"
    "0,2026-01-01  00:00:00,-30.0,-71.0,10.0,4.5,ML,ana\n"
    "1,2026-01-02  00:00:00,-31.0,-72.0,20.0,3.0,ML,beto\n")


def test_no_publicados_tabla_y_descargar_todo(app_factory, raiz_gui, cwd_tmp,
                                              monkeypatch):
    _, inst = app_factory()
    _escribir(cwd_tmp, "datos/no_pub_desde_2_5_seiscomp_estricto.csv",
              _CSV_NO_PUB)
    descargado = {}

    def exportar_listado(filas, valores, columnas, cwd, etiqueta,
                         padre=None, formato=None):
        descargado["filas"] = [valores(f) for f in filas]
        descargado["etiqueta"] = etiqueta
        return "datos/descarga.csv"

    # La descarga de No publicados pasa por el exportador del revisor.
    import revisa_seiscomp as rsv
    monkeypatch.setattr(rsv, "_exportar_listado", exportar_listado)

    inst._ver_no_publicados()

    top = _toplevel(raiz_gui, "No publicados")
    assert _tab_texts(_buscar(top, ttk.Notebook)) == ["SeisComp", "Seisan"]
    arbol = _buscar(top, ttk.Treeview)
    assert len(arbol.get_children()) == 2
    assert not _boton(top, "Descargar").instate(["disabled"])

    _boton(top, "Descargar todo").invoke()
    assert len(descargado["filas"]) == 2
    assert descargado["etiqueta"] == "no publicados seiscomp"


def test_no_publicados_sin_csv(app_factory, raiz_gui, cwd_tmp):
    _, inst = app_factory()
    inst._ver_no_publicados()
    top = _toplevel(raiz_gui, "No publicados")
    arbol = _buscar(top, ttk.Treeview)
    assert len(arbol.get_children()) == 0
    assert _boton(top, "Descargar").instate(["disabled"])


def test_no_publicados_tiene_aplicar(app_factory, raiz_gui, cwd_tmp):
    _, inst = app_factory()
    _escribir(cwd_tmp, "datos/no_pub_desde_2_5_seiscomp_estricto.csv",
              _CSV_NO_PUB)
    inst._ver_no_publicados()
    top = _toplevel(raiz_gui, "No publicados")
    boton = _boton(top, "Aplicar")
    assert boton is not None
    # Aplicar re-filtra sin error.
    boton.invoke()
    raiz_gui.update()
