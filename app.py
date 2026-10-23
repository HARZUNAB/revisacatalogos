#!/usr/bin/env python3
"""
app.py
======
Aplicación de escritorio (ttkbootstrap) que unifica el menú del supervisor con
el flujo de análisis y revisión. La ventana principal gira alrededor de un solo
botón, «Procesar catálogos», que con los catálogos ya descargados:

  - Corre el análisis (proc_query -> revisaselect -> revisacollect ->
    compara -> [atribución a SeisComp] -> cruce de no publicados ->
    [revisaexcluidos/repetidosexclu] -> repetidos) mostrando el registro (log)
    en vivo.
  - Genera el JSON de todas las fuentes (Seisan / eventquery / SeisComp / No
    publicados de seisan / No publicados de SeisComp) y arma las pestañas de
    catálogo. Las fuentes que ya están al día se omiten.
  - Deja toda la información disponible para consultar en sus pestañas, sin
    tener que pulsar un botón por salida.

Al abrir, la aplicación reconoce qué hay en el directorio de ejecución y deja
cada pestaña en su estado (con datos, pendiente de procesar o sin datos). Los
paneles pendientes se generan en segundo plano al abrir su pestaña.

La barra lateral se organiza en Procesar / Consultar / Re-exportar. «Consultar»
reúne «Repetidos» y los listados de «No publicados» y «No actualizados»; los
dos últimos abren una ventana con una pestaña por fuente (SeisComp primero).
«Re-exportar» solo habilita el catálogo que falta o que cambió; si la
extracción inicial no pudo con uno, la app lo avisa y deja re-obtenerlo ahí
mismo.

  - Revisar los datos de SeisComp: la exportación de la ventana la deja la
    solicitud de catálogos y la revisión se abre en su pestaña, junto con los
    catálogos de Seisan y eventquery.
  - Atribuir los publicados a SeisComp: la misma comparación, corrida sobre las
    soluciones preferred en vez de las de Seisan, deja en
    informes/no_act_seiscomp_estricto.txt qué publicado quedó desactualizado y
    a qué analista le corresponde. Se saltea sola si no hay exportación.
  - Ver los reportes de eventos repetidos.

Recibe como argumentos el archivo de entrada ($1) y el de salida temporal
($2), igual que el antiguo supervisor.sh. Opcionalmente un tercer argumento
($3) con un JSON de estado que deja solicita_catalogos.py: el período y qué
catálogos no se pudieron obtener. Las salidas se organizan por contenido en el
directorio de ejecución (ver rutas.py).

Uso:
    python3 app.py <archivo_entrada.csv> <archivo_salida.dat> [estado.json]
"""

import csv
import datetime
import json
import os
import shutil
import sys
import queue
import threading
import traceback
import subprocess
import webbrowser

import rutas

import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.scrolled import ScrolledText
from ttkbootstrap.dialogs import Messagebox
from ttkbootstrap.widgets import DateEntry

try:
    from dateutil import parser as _dateparser
except Exception:  # sin dateutil se cae al formato estricto
    _dateparser = None

import agencias as agencias_mod
import ajuste
import descargas
import traer_catalogos as tc

import matplotlib
matplotlib.use("TkAgg")  # las figuras de detalle comparten la raíz Tk de la app

from tkinter import BooleanVar, Menu, TclError, Toplevel

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable

REP_FILES = [
    ("Repetidos publicados (eventquery) (amplio)",
     "informes/rep_publica_amplio.txt"),
    ("Repetidos publicados (eventquery) (estricto)",
     "informes/rep_publica_estricto.txt"),
    ("Repetidos seisan (amplio)", "informes/rep_seisan_amplio.txt"),
    ("Repetidos seisan (estricto)", "informes/rep_seisan_estricto.txt"),
    ("Repetidos excluidos seisan", "informes/rep_seisan_exclu.txt"),
    ("Repetidos SeisComp (amplio)", "informes/rep_seiscomp_amplio.txt"),
    ("Repetidos SeisComp (estricto)", "informes/rep_seiscomp_estricto.txt"),
]

# Tamaño con el que abre la ventana. Es solo el punto de partida: la ventana
# crece sola con lo que pidan las pestañas (ver _ajustar_ventana y ajuste.py),
# sin pasar nunca de lo que admite la pantalla.
TAMANIO_INICIAL = (980, 820)

# De qué archivo se arma cada pestaña de «Catálogo». El de eventquery es el
# concatenado de los new_2_*.csv, que arma _concatenar_eventquery; el de Seisan
# es el collect del análisis; el de SeisComp no entra aquí porque lo elige
# _par_seiscomp_para_catalogo por cobertura.
ARCHIVO_CATALOGO = {
    "seisan": "salida_collect.csv",
    "eventquery": "todos_eventquery.csv",
}


def _repetidos_columnas(ruta):
    """
    Columnas de la tabla de «Ver repetidos» para un informe, según su nombre.

    Los publicados suman dos columnas de analista probable: eventquery no
    informa responsable, así que el nombre sale de cruzar cada evento con Seisan
    y con SeisComp (ver _analistas_probables_repetidos).
    """
    import repetidos
    base = os.path.basename(ruta)
    if base.startswith("rep_publica"):
        return list(repetidos.COLUMNAS_PUBLICA) + [
            ("analista_seisan", "Analista probable (Seisan)", 185, False),
            ("analista_seiscomp", "Analista probable (SeisComp)", 205, False),
        ]
    if base.startswith("rep_seisan_exclu"):
        return list(repetidos.COLUMNAS_EXCLU)
    return list(repetidos.COLUMNAS_SEISAN)


def _leer_informe_repetidos(ruta):
    """
    (filas, crudo) de un informe de repetidos.

    'filas' es una lista de dicts (una por evento) si el informe está tabulado;
    si no, 'filas' es None y 'crudo' trae las líneas para mostrarlas tal cual.
    Los informes viejos venían separados por espacios y no se pueden partir en
    columnas sin ambigüedad, así que se degradan a texto.
    """
    if not os.path.isfile(ruta):
        return [], None
    with open(ruta, encoding="utf-8", errors="replace") as f:
        lineas = [linea.rstrip("\n") for linea in f]
    lineas = [linea for linea in lineas if linea.strip()]
    if not lineas:
        return [], None
    cabecera = lineas[0].split("\t")
    if len(cabecera) < 2:
        return None, lineas
    filas = []
    for linea in lineas[1:]:
        partes = linea.split("\t")
        if len(partes) != len(cabecera):
            return None, lineas
        filas.append(dict(zip(cabecera, partes)))
    return filas, None


def _indices_atribucion():
    """[(fuente, indice)] de datos/atribucion_*.csv, para el cruce de analistas."""
    try:
        import generajson as gj
    except Exception:
        return []
    indices = []
    for fuente in ("seiscomp", "seisan"):
        indice = gj._cargar_atribucion(fuente)
        if indice:
            indices.append((fuente, indice))
    return indices


def _analistas_probables_repetidos(filas, indices):
    """
    Agrega 'analista_<fuente>' a cada fila cruzando el evento con los catálogos.

    'indices' es [(fuente, indice), ...], donde 'indice' es lo que devuelve
    generajson._cargar_atribucion. Se reusa la misma lógica que el catálogo de
    eventquery para que la pantalla y la viñeta no puedan decir cosas distintas.
    """
    if not indices:
        return
    try:
        import generajson as gj
    except Exception:
        return
    for fila in filas:
        fecha = fila.get("fecha_hora", "")
        try:
            lat = float(fila.get("latitud"))
            lon = float(fila.get("longitud"))
        except (TypeError, ValueError):
            lat = lon = None
        for fuente, indice in indices:
            encontradas = gj._analistas_para_evento(indice, fecha, lat, lon)
            nombres = []
            for entrada in encontradas or ():
                nombres.extend(entrada.get("analistas") or [])
            fila["analista_" + fuente] = ", ".join(nombres)


def _derivado_al_dia(destino, entradas, carpeta):
    """
    True si 'destino' es más nuevo que todos los archivos de 'entradas'.

    Sirve para los archivos que son un derivado puro de otros (el concatenado
    de los new_2_*.csv, por ejemplo): si la salida es posterior a todas las
    entradas, no hay forma de que esté vieja y se puede saltear el trabajo.

    Ante cualquier duda devuelve False. Preferir rehacer un archivo a mostrar
    datos de la corrida anterior.
    """
    try:
        if not os.path.isfile(destino):
            return False
        marca = os.path.getmtime(destino)
    except OSError:
        return False
    for nombre in entradas:
        try:
            if os.path.getmtime(os.path.join(carpeta, nombre)) > marca:
                return False
        except OSError:
            return False
    return True

# Una vista por panel de análisis. 'clave' es, a la vez, el nombre base en
# disco (eventos_<clave>.json, conteo_perfiles_<clave>.json) y la clave de la
# pestaña. 'fuente' decide cómo se lee el CSV y cómo se comporta el panel;
# 'entrada' es el CSV del que sale el JSON: mientras el JSON sea más nuevo que
# este archivo, la vista ya está procesada y no hace falta rehacerla.
# 'tab' es el texto corto del botón de la pestaña: el grupo al que pertenece
# (GRUPOS_PESTANAS) ya pone el contexto, así que alcanza con la fuente.
VISTAS = [
    {"clave": "seisan", "fuente": "seisan",
     "tab": "Seisan", "etiqueta": "Seisan",
     "entrada": os.path.join("datos", "salida_collect.csv")},
    {"clave": "eventquery", "fuente": "eventquery",
     "tab": "eventquery", "etiqueta": "Eventquery",
     "entrada": os.path.join("datos", "todos_eventquery.csv")},
    {"clave": "seiscomp", "fuente": "seiscomp",
     "tab": "SeisComp", "etiqueta": "SeisComp",
     "entrada": os.path.join("datos", "seiscomp_parametros.csv")},
    {"clave": "seisan_nopub", "fuente": "seisan",
     "tab": "Seisan", "etiqueta": "No publicados de seisan",
     "entrada": os.path.join("datos", "no_pub_desde_2_5_estricto.csv")},
    {"clave": "seiscomp_nopub", "fuente": "seiscomp",
     "tab": "SeisComp",
     "etiqueta": "No publicados de SeisComp",
     "entrada": os.path.join("datos",
                             "no_pub_desde_2_5_seiscomp_estricto.csv")},
    # Paneles de «No actualizados»: la solución local con la publicada anidada
    # (ver generajson.py --pares). Entra por el atribucion_<fuente>.csv.
    {"clave": "seisan_noact", "fuente": "seisan",
     "tab": "Seisan", "etiqueta": "No actualizados de Seisan",
     "entrada": os.path.join("datos", "atribucion_seisan.csv")},
    {"clave": "seiscomp_noact", "fuente": "seiscomp",
     "tab": "SeisComp", "etiqueta": "No actualizados de SeisComp",
     "entrada": os.path.join("datos", "atribucion_seiscomp.csv")},
]
VISTAS_POR_CLAVE = {v["clave"]: v for v in VISTAS}

# Las pestañas se agrupan en filas: encabezado arriba, fuentes abajo. Se
# agrupa en lugar de ponerlas todas en una sola tira porque nueve pestañas en
# línea piden 947 px de ancho (más los 232 px de la barra lateral) y la
# ventana no llegaba, así que los nombres quedaban cortados. Con los nombres
# cortos que aporta el grupo, la barra entera mide ~256 px.
#
# 'titulo' en None es una fila sin encabezado: la de "Registro", que sola se
# explica con su propio botón. El orden de las páginas dentro de cada grupo es
# el que usa el cuaderno.
#
# Cada pestaña de este cuaderno es un panel de análisis (prefijo panel:); el
# catálogo crudo y el listado de no actualizados ya no van aquí: se consultan
# desde los botones «Catálogos» y «No actualizados» de la barra lateral.
GRUPOS_PESTANAS = [
    {"titulo": None, "pestanas": ["log"]},
    {"titulo": "Panel de mapas y perfiles",
     "pestanas": ["panel:seisan", "panel:eventquery", "panel:seiscomp"]},
    {"titulo": "No publicados",
     "pestanas": ["panel:seisan_nopub", "panel:seiscomp_nopub"]},
    {"titulo": "No actualizados",
     "pestanas": ["panel:seisan_noact", "panel:seiscomp_noact"]},
]

# De "fuente" (lo que se clickea en la barra) a la vista del panel.
FUENTE_A_VISTA = {
    "seisan": "seisan",
    "eventquery": "eventquery",
    "seiscomp": "seiscomp",
    "nopub": "seisan_nopub",
    "nopub_seiscomp": "seiscomp_nopub",
    "noact": "seisan_noact",
    "noact_seiscomp": "seiscomp_noact",
}
VISTA_A_FUENTE = {v: k for k, v in FUENTE_A_VISTA.items()}


def _script(nombre):
    return os.path.join(SCRIPT_DIR, nombre)


MARCA_PROGRESO = "@@PROGRESO@@"

# Plan de etapas por tarea. 'scripts' mapea el subproceso (basename) que
# activa cada etapa; 'peso' reparte la barra (suman 1.0).
ANALISIS_PLAN = [
    {"nombre": "Procesando query",
     "scripts": ("proc_query_harz_2.py",), "peso": 0.10},
    {"nombre": "Revisando select",
     "scripts": ("revisaselect.py",), "peso": 0.15},
    {"nombre": "Revisando collect",
     "scripts": ("revisacollect.py",), "peso": 0.15},
    {"nombre": "Comparando publicados v/s procesados",
     "scripts": ("compara.py",), "peso": 0.20},
    {"nombre": "Atribuyendo publicados a SeisComp",
     "scripts": ("compara.py",), "peso": 0.10,
     "discriminador": "seiscomp_parametros.csv"},
    {"nombre": "Cruzando no publicados con la otra fuente",
     "scripts": ("cruza_nopub.py",), "peso": 0.01},
    {"nombre": "Revisando excluidos",
     "scripts": ("revisaexcluidos.py", "repetidosexclu.py"), "peso": 0.10},
    {"nombre": "Revisando repetidos",
     "scripts": ("repetidos.py",), "peso": 0.19},
]

FUENTE_PLAN = {
    "seisan": [
        {"nombre": "Generando JSON (seisan)", "scripts": ("generajson.py",),
         "peso": 1.0},
    ],
    "nopub": [
        {"nombre": "Generando JSON (no publicados)",
         "scripts": ("generajson.py",), "peso": 1.0},
    ],
    "noact": [
        {"nombre": "Generando panel de no actualizados",
         "scripts": ("generajson.py",), "peso": 1.0},
    ],
    "noact_seiscomp": [
        {"nombre": "Generando panel de no actualizados de SeisComp",
         "scripts": ("generajson.py",), "peso": 1.0},
    ],
    "eventquery": [
        {"nombre": "Concatenando eventquery", "scripts": (), "peso": 0.15},
        {"nombre": "Generando JSON (eventquery)", "scripts": ("generajson.py",),
         "peso": 0.85},
    ],
    "seiscomp": [
        {"nombre": "Convirtiendo SeisComp",
         "scripts": ("seiscomp_a_parametros.py",), "peso": 0.35},
        {"nombre": "Generando JSON (seiscomp)", "scripts": ("generajson.py",),
         "peso": 0.65},
    ],
}

# Plan del botón maestro «Procesar catálogos». El análisis va primero (con la
# conversión de SeisComp en el lugar real donde corre: antes de su atribución,
# ver _asegurar_parametros_seiscomp) y después la generación de los paneles.
# Los pesos suman 1.0. Las corridas de generajson.py se distinguen con
# 'discriminador' (su archivo de entrada, o el nombre de la vista en el modo
# --pares), porque con el nombre del script solo se ganaría siempre la primera.
PROCESAR_PLAN = [
    {"nombre": "Procesando query",
     "scripts": ("proc_query_harz_2.py",), "peso": 0.075},
    {"nombre": "Revisando select",
     "scripts": ("revisaselect.py",), "peso": 0.11},
    {"nombre": "Revisando collect",
     "scripts": ("revisacollect.py",), "peso": 0.11},
    {"nombre": "Comparando publicados v/s procesados",
     "scripts": ("compara.py",), "peso": 0.15},
    {"nombre": "Convirtiendo SeisComp",
     "scripts": ("seiscomp_a_parametros.py",), "peso": 0.04},
    {"nombre": "Atribuyendo publicados a SeisComp",
     "scripts": ("compara.py",), "peso": 0.075,
     "discriminador": "seiscomp_parametros.csv"},
    {"nombre": "Cruzando no publicados con la otra fuente",
     "scripts": ("cruza_nopub.py",), "peso": 0.01},
    {"nombre": "Revisando excluidos",
     "scripts": ("revisaexcluidos.py", "repetidosexclu.py"), "peso": 0.075},
    {"nombre": "Revisando repetidos",
     "scripts": ("repetidos.py",), "peso": 0.105},
    {"nombre": "Generando panel de Seisan",
     "scripts": ("generajson.py",), "peso": 0.045,
     "discriminador": "salida_collect.csv"},
    {"nombre": "Generando panel de eventquery",
     "scripts": ("generajson.py",), "peso": 0.045,
     "discriminador": "todos_eventquery.csv"},
    {"nombre": "Generando panel de SeisComp",
     "scripts": ("generajson.py",), "peso": 0.045,
     "discriminador": "seiscomp_parametros.csv"},
    {"nombre": "Generando panel de no publicados",
     "scripts": ("generajson.py",), "peso": 0.03,
     "discriminador": "no_pub_desde_2_5_estricto.csv"},
    {"nombre": "Generando panel de no publicados de SeisComp",
     "scripts": ("generajson.py",), "peso": 0.03,
     "discriminador": "no_pub_desde_2_5_seiscomp_estricto.csv"},
    {"nombre": "Generando panel de no actualizados",
     "scripts": ("generajson.py",), "peso": 0.0275,
     "discriminador": "seisan_noact"},
    {"nombre": "Generando panel de no actualizados de SeisComp",
     "scripts": ("generajson.py",), "peso": 0.0275,
     "discriminador": "seiscomp_noact"},
]

# Agencias externas soportadas: nombre visible -> sufijo del CSV que deja
# consultaapi.py (consultaapi_<sufijo>.csv).
AGENCIAS_EXTERNAS = {"EMSC": "EMSC", "USGS": "NEIC", "GFZ": "GFZ"}

# Etapas del botón «Comparar agencias». consultaapi.py baja las agencias;
# generajson.py arma el JSON de cada una (perfil más cercano) y agencias.py
# compara contra nuestro publicado. Los pesos suman 1.0.
AGENCIAS_PLAN = [
    {"nombre": "Consultando agencias externas",
     "scripts": ("consultaapi.py",), "peso": 0.35},
    {"nombre": "Generando JSON de agencias",
     "scripts": ("generajson.py",), "peso": 0.45},
    {"nombre": "Comparando con lo publicado",
     "scripts": ("agencias.py",), "peso": 0.20},
]

# Minutos que se considera válida una comparación hecha en modo «hasta ahora»
# (tiempo real) antes de volver a consultar las APIs. Alinea con la latencia de
# EMSC/USGS, que es de minutos.
TTL_AGENCIAS_MIN = 15

# Etiqueta y estilo de cada estado de catálogo, para los chips y el aviso.
# - ok: al día.
# - fallo: la extracción falló (vino en la lista de fallantes).
# - falta: el archivo no está, sin una falla reportada (se borró o similar).
# - cambio: el insumo es más nuevo que el derivado.
ESTADOS_CATALOGO = {
    "ok": ("✓ OK", "success"),
    "fallo": ("✗ falló", "danger"),
    "falta": ("✗ falta", "danger"),
    "cambio": ("⚠ cambió", "warning"),
    "sin_datos": ("⚠ sin datos", "warning"),
}

# Ayuda de la columna «Estado» del listado de No publicados. Va aquí, y no en
# el manual, para que la explicación esté disponible desde la propia ventana.
def _linea_ayuda_estados(estado, texto):
    """Fila de la tabla de ayuda con la primera columna alineada."""
    return "%-24s | %s\n" % (estado, texto)


AYUDA_ESTADOS_NO_PUBLICADOS = (
    "Estados de No publicados\n\n"
    + _linea_ayuda_estados("Estado", "Significado")
    + "-" * 24 + "-+-" + "-" * 45 + "\n"
    + _linea_ayuda_estados(
        "Publicado en ...",
        "Coincidencia única: ≤6 s y ≤0,5°.")
    + _linea_ayuda_estados("", "Confiable.")
    + _linea_ayuda_estados(
        "Candidato en ...",
        "Solución cercana: ≤120 s y ≤2°, fuera de la")
    + _linea_ayuda_estados("", "confirmación. Revisar.")
    + _linea_ayuda_estados(
        "Ambiguo: N ...",
        "Varias soluciones cercanas; no se sabe cuál.")
    + _linea_ayuda_estados(
        "", "Se muestra la mejor por Δt y distancia.")
    + _linea_ayuda_estados(
        "Sin coincidencia",
        "Ninguna solución de la otra fuente en 120 s / 2°.")
    + _linea_ayuda_estados(
        "No evaluable",
        "No se pudo comparar: falta eventquery, datos de")
    + _linea_ayuda_estados(
        "", "la otra fuente, atribución vencida, comparación")
    + _linea_ayuda_estados("", "ausente o vencida.")
    + "\n«Publicado en» solo se completa con una confirmación única.\n"
    "Δt, Dist. y Analista otra fuente describen el candidato mostrado."
)

URL_CATALOGO_SISMOLOGIA = (
    "https://www.sismologia.cl/sismicidad/catalogo/%s/%s.html")


def _url_dia_sismologia(fecha):
    """
    URL del catálogo diario de sismologia.cl para la fecha de un evento.

    La fecha viene como 'AAAA-MM-DD HH:MM:SS' o ISO; se usa solo el día local
    del evento. Devuelve None si no se puede interpretar.
    """
    texto = str(fecha or "").strip()
    if not texto:
        return None
    parte = texto.replace("T", " ").split(" ", 1)[0]
    for formato in ("%Y-%m-%d", "%Y/%m/%d"):
        try:
            dia = datetime.datetime.strptime(parte, formato)
        except ValueError:
            continue
        return URL_CATALOGO_SISMOLOGIA % (
            dia.strftime("%Y/%m"), dia.strftime("%Y%m%d"))
    return None


def _anchos_columnas_por_contenido(columnas, filas, valores,
                                   minimo=50, maximo=420, holgura=18):
    """
    Ajusta el ancho de cada columna al máximo entre su encabezado y sus datos.

    Se usa en listados con columnas de texto muy dispares (por ejemplo Estado
    en No publicados), donde un ancho fijo grande deja la tabla más ancha que
    la ventana. Devuelve las mismas columnas con el ancho recalculado.
    """
    try:
        import tkinter.font as tkfont
        fuente_datos = tkfont.nametofont("TkDefaultFont")
        fuente_titulo = tkfont.nametofont("TkHeadingFont")
    except Exception:
        return columnas

    filas_valores = [valores(fila) for fila in filas]
    ajustadas = []
    for indice, columna in enumerate(columnas):
        clave, titulo, _ancho = columna[:3]
        medido = fuente_titulo.measure(str(titulo))
        for valores_fila in filas_valores:
            medido = max(medido, fuente_datos.measure(
                str(valores_fila[indice])))
        ancho = max(minimo, min(maximo, medido + holgura))
        ajustadas.append((clave, titulo, ancho) + tuple(columna[3:]))
    return ajustadas


class App:
    def __init__(self, raiz, archivo, salida, estado=None):
        self.raiz = raiz
        self.archivo = archivo
        self.salida = salida
        self.base = os.path.basename(archivo) if archivo else ""
        self.cwd = os.getcwd()
        # Estado que dejó solicita_catalogos.py: período y catálogos que no se
        # pudieron obtener. Puede venir vacío (modo antiguo o arranque directo).
        estado = estado or {}
        self.periodo = (estado.get("inicio"), estado.get("fin"))
        self.catalogos_faltantes = set(estado.get("faltantes", []))
        self.detalles_faltantes = estado.get("detalles", {}) or {}
        self.avisos_catalogos = estado.get("avisos", []) or []
        self._avisos_sin_datos_mostrados = set()
        self._seiscomp_sin_eventos = False
        self.cola = queue.Queue()
        # Trazabilidad de plotear.py: sus mensajes (avisos, mapa sin perfil)
        # quedan en informes/app.log con hora, igual que el resto de la app.
        try:
            import plotear
            plotear.fijar_logger(self._log)
        except Exception:
            pass
        self.ocupado = False
        self.analisis_hecho = False
        self.analisis_en_curso = False
        self.botones = []
        self.botones_fuente = []
        # Botones con una condición propia: (widget, ¿se puede?, motivo).
        # La compuerta general solo sabe de análisis hecho/no hecho, así que
        # para lo que depende de un archivo puntual hace falta esto.
        self.condiciones = []
        # Con «Forzar actualización» los botones de re-exportar se habilitan
        # aunque el catálogo figure al día, para poder rebajarlo y reprocesar.
        self.forzar_actualizacion = BooleanVar(value=False)
        # Tamaño que se sabe que tiene la ventana. Tk contesta 200x200 a todo
        # antes de que esté mapeada (ver ajuste.py), así que el "solo crecer"
        # se apoya en este valor y no en preguntarle a la ventana.
        self._tamanio = TAMANIO_INICIAL
        # Panel de cada vista: {"frame", "placeholder", "construido"}.
        self.paneles = {}
        self.ultima_fuente = None
        self.plan_etapas = None
        self.etapa_base = 0.0
        self.etapa_ancho = 1.0
        self.etapa_nombre = ""

        # Ids de los after pendientes, para cancelarlos al salir y que Tk no
        # intente ejecutarlos con la raíz ya destruida (bgerror en la consola).
        self._after_drenar = None
        self._after_msg = None
        self._construir()
        self._autodetectar_estado()
        self.raiz.protocol("WM_DELETE_WINDOW", self._salir_app)
        self._after_drenar = self.raiz.after(100, self._drenar)
        # La exportación de SeisComp la deja la solicitud de catálogos antes
        # de llegar aquí, y su pestaña se llena al procesar los catálogos,
        # igual que las de Seisan y eventquery.

    def _salir_app(self):
        """Cierra las figuras de matplotlib y luego la ventana principal."""
        # Cancelar los after pendientes ANTES de destruir la raíz: si no, Tk
        # intenta ejecutarlos cuando el intérprete ya no existe y ensucia la
        # consola con un bgerror ("invalid command name ..._drenar").
        for ident in (self._after_drenar, self._after_msg):
            if ident is not None:
                try:
                    self.raiz.after_cancel(ident)
                except Exception:
                    pass
        self._after_drenar = None
        self._after_msg = None
        try:
            import matplotlib.pyplot as plt
            plt.close("all")
        except Exception:
            pass
        try:
            self.raiz.destroy()
        except Exception:
            pass

    # ------------------------------------------------------------------ UI
    def _construir(self):
        self.raiz.title("Revisión de eventos · supervisor")
        self.raiz.geometry("%dx%d" % TAMANIO_INICIAL)
        self.raiz.minsize(860, 600)

        cab = ttk.Frame(self.raiz, padding=(12, 10, 12, 4))
        cab.pack(side=TOP, fill=X)
        ttk.Label(cab, text="Revisión de eventos sísmicos",
                  font=("", 15, "bold")).pack(side=LEFT)

        # La carpeta de ejecución va en su propia fila, a la derecha. Antes la
        # entrada compartía línea con el título y, al ser la ruta completa, los
        # dos textos se pisaban: la cabecera pedía 1001 px en una ventana de
        # 980. El archivo de entrada no se pierde: queda en el Registro cuando
        # se ejecuta el análisis, porque _popen registra la línea de comando.
        carpeta = ttk.Frame(self.raiz, padding=(12, 0, 12, 4))
        carpeta.pack(side=TOP, fill=X)
        ttk.Label(carpeta, text="Carpeta: %s" % self.cwd,
                  bootstyle="secondary").pack(side=RIGHT)

        cuerpo = ttk.Frame(self.raiz, padding=(12, 4, 12, 12))
        cuerpo.pack(side=TOP, fill=BOTH, expand=YES)

        # --- Barra lateral ---
        barra = ttk.Frame(cuerpo)
        barra.pack(side=LEFT, fill=Y, padx=(0, 12))

        self._encabezado(barra, "PROCESAR")
        self.boton_analisis = self._boton(barra, "Procesar catálogos",
                                          self._accion_procesar,
                                          bootstyle="primary")
        self.botones.remove(self.boton_analisis)
        self.etiqueta_estado = ttk.Label(barra, text="",
                                         bootstyle="warning")
        self.etiqueta_estado.pack(anchor=W, pady=(2, 2))
        # Aviso del estado de los catálogos (se refresca en
        # _actualizar_estado_catalogos): dice cuáles están OK, cuáles fallaron,
        # cuáles faltan y cuáles cambiaron.
        self.aviso_catalogos = ttk.Label(barra, text="", bootstyle="secondary",
                                         wraplength=230, justify=LEFT)
        self.aviso_catalogos.pack(anchor=W, pady=(0, 6))

        self._separador(barra)
        self._encabezado(barra, "CONSULTAR")
        # Catálogos y los listados son ventanas de consulta, no los paneles del
        # cuaderno. Las de no publicados/no actualizados abren una pestaña por
        # fuente (SeisComp primero).
        self._boton(barra, "Catálogos", self._ver_catalogos, gated=True)
        self._boton(barra, "Repetidos", self._ver_repetidos, gated=True)
        self._boton(barra, "No publicados", self._ver_no_publicados, gated=True)
        self._boton(barra, "No actualizados", self._ver_no_actualizados,
                    gated=True)
        self._boton(barra, "Comparar agencias", self._comparar_agencias,
                    gated=True)

        self._separador(barra)
        self._encabezado(barra, "DESCARGAS")
        # Abre la carpeta donde caen los archivos que uno se lleva. Sin 'gated'
        # a propósito: no depende del análisis, la carpeta existe siempre y
        # sirve incluso antes de correr.
        self._boton(barra, "Abrir carpeta", self._abrir_descargas)

        self._separador(barra)
        self._encabezado(barra, "RE-EXPORTAR")
        # Con el tilde puesto, los botones de abajo se habilitan aunque el
        # catálogo figure al día: re-importar fuerza el análisis (los datos
        # cruzan entre catálogos).
        self.chk_forzar = ttk.Checkbutton(
            barra, text="Forzar actualización",
            variable=self.forzar_actualizacion, command=self._actualizar_gate,
            bootstyle="round-toggle")
        self.chk_forzar.pack(fill=X, pady=(2, 4))
        # Cada fila: el botón del catálogo y, a la derecha, un chip con su
        # estado. Solo se habilita el botón del catálogo que falló, falta o
        # cambió; el chip explica el estado de los tres.
        self.botones_reexportar = {}
        self.chips_catalogo = {}
        for catalogo in ("Seisan", "eventquery", "SeisComp"):
            fila = ttk.Frame(barra)
            fila.pack(fill=X)
            chip = ttk.Label(fila, text="", width=9, anchor=E)
            chip.pack(side=RIGHT)
            b = self._boton(
                fila, catalogo,
                lambda c=catalogo: self._re_exportar(c),
                condicion=(lambda c=catalogo: self._puede_re_exportar(c),
                           lambda c=catalogo: self._motivo_re_exportar(c)))
            self.botones_reexportar[catalogo] = b
            self.chips_catalogo[catalogo] = chip

        self._separador(barra)
        self._boton(barra, "Salir", self._salir_app, bootstyle="danger")

        # --- Contenido (pestañas) ---
        # La barra lateral va a la izquierda; a su derecha, un frame con la
        # barra de pestañas agrupadas arriba y el cuaderno abajo.
        derecha = ttk.Frame(cuerpo)
        derecha.pack(side=LEFT, fill=BOTH, expand=YES)

        self._boton_pestana = {}
        self.cuaderno = ttk.Notebook(derecha)

        marco_log = ttk.Frame(self.cuaderno)
        self.marco_log = marco_log
        self.cuaderno.add(marco_log, text="Registro")
        self.txt = ScrolledText(marco_log, padding=4, autohide=True)
        self.txt.pack(fill=BOTH, expand=YES)
        self.txt.text.configure(state=DISABLED, font=("Consolas", 9))

        # Un panel por vista. El marco de la pestaña ES el contenedor del
        # panel, sin un nivel más en el medio, porque es lo que hay que
        # pasarle a select() después.
        for vista in VISTAS:
            marco = ttk.Frame(self.cuaderno)
            self.cuaderno.add(marco, text=vista["tab"])
            etiqueta = ttk.Label(
                marco, justify=CENTER,
                text="No hay datos de esta fuente para mostrar.\n\nPulse "
                     "«Procesar catálogos» para generarlos.")
            etiqueta.pack(expand=YES)
            self.paneles[vista["clave"]] = {
                "frame": marco,
                "etiqueta": etiqueta,
                "construido": False,
            }

        # Catálogos crudos (sin análisis de perfiles): una pestaña por fuente.
        # Ya no viven en el cuaderno principal: se abren desde el botón
        # «Catálogos» de la barra lateral, en su propia ventana (ver
        # _ver_catalogos). Los frames se crean ahí a demanda; hasta entonces
        # quedan en None y _construir_catalogo no se llama.
        self.catalogos = {}
        for clave, titulo in (("seiscomp", "SeisComp"), ("seisan", "Seisan"),
                              ("eventquery", "eventquery")):
            self.catalogos[clave] = {"frame": None, "titulo": titulo,
                                     "construido": False, "firma": None}
        # Ventana y cuaderno de catálogos (se crean al pulsar «Catálogos»).
        self.marco_catalogos = None
        self.cuaderno_catalogos = None
        # Atajos que usan _abrir_revisor y _abrir_catalogo; se apuntan al crear
        # la ventana de catálogos.
        self.seiscomp_frame = None
        self.seisan_frame = None
        self.eventquery_frame = None

        # Ventana de «No actualizados» y sus pestañas. Se crea una sola vez y
        # se oculta al cerrar; cada pestaña guarda su firma para rehacerse solo
        # cuando cambian los archivos de entrada.
        self.no_actualizados = {}
        for clave, titulo in (("seiscomp", "SeisComp"), ("seisan", "Seisan")):
            self.no_actualizados[clave] = {
                "frame": None, "titulo": titulo, "construido": False,
                "firma": None}
        self.marco_no_actualizados = None
        self.cuaderno_no_actualizados = None

        # Ahora que ya existen todas las páginas, se arma la barra de pestañas
        # agrupadas y solo después se empaqueta el cuaderno: la barra va
        # primero (side=TOP) para quedar arriba, y el cuaderno ocupa el resto.
        self._construir_barra_pestanas(derecha)
        self.cuaderno.pack(side=LEFT, fill=BOTH, expand=YES)

        # Se anula el layout de la pestaña nativa del cuaderno PRINCIPAL para que
        # no se vea la tira que dibuja el cuaderno: las pestañas se eligen desde
        # la barra de grupos de arriba. Se hace sobre un estilo propio
        # ("Principal.TNotebook") y NO sobre "TNotebook.Tab": anular ese era un
        # cambio GLOBAL al proceso y dejaba sin pestañas a otros cuadernos, como
        # el de la ventana de Estaciones, que sí necesita mostrar las suyas.
        self.raiz.style.layout("Principal.TNotebook.Tab", [])
        self.cuaderno.configure(style="Principal.TNotebook")

        # --- Barra de progreso (inferior, persistente) ---
        barra_marco = ttk.Frame(self.raiz, padding=(12, 4, 12, 8))
        barra_marco.pack(side=TOP, fill=X)
        self.barra = ttk.Progressbar(barra_marco, maximum=1000, value=0,
                                     bootstyle="info")
        self.barra.pack(side=LEFT, fill=X, expand=YES)
        self.barra_texto = ttk.Label(barra_marco, text="Esperando tarea…",
                                     bootstyle="secondary", width=46)
        self.barra_texto.pack(side=LEFT, padx=(10, 0))
        self.barra_valor = 0

        # Al abrir una pestaña de panel se construye/reusa el panel de esa
        # vista (ver _al_cambiar_pestana).
        self.cuaderno.bind("<<NotebookTabChanged>>", self._al_cambiar_pestana)

        self._log("Listo. Directorio de trabajo: %s" % self.cwd)
        # La primera pestaña se ve al arrancar: se marca desde el inicio para
        # que no quede ningún botón de la barra sin resaltar.
        self._marcar_pestana_activa()
        # Y se baja la barra para que «Registro» quede a la altura de
        # «Procesar catálogos». Se mide al mapear la ventana (ver _alinear).
        self.raiz.bind("<Map>", self._alinear_pestanas, add="+")
        # Con el contenido del registro el tamaño inicial alcanza y la ventana
        # no se toca; el ajuste importa cuando aparece algo más ancho, como el
        # panel de análisis o un catálogo.
        self._ajustar_ventana()
        self._avisar_entorno_grafico()

    def _avisar_entorno_grafico(self):
        """
        Avisa en el registro si el entorno gráfico puede congelar la sesión.

        Un grab de X sobre una pila gráfica frágil (nvidia con fallas de modeset,
        AnyDesk inyectando entrada) puede dejar la sesión entera bloqueada hasta
        matar el proceso. Es best-effort: jamás rompe el arranque.
        """
        try:
            anydesk = False
            for pid in os.listdir("/proc"):
                if not pid.isdigit():
                    continue
                try:
                    with open(os.path.join("/proc", pid, "comm"),
                              "r") as archivo:
                        if archivo.read().strip() == "anydesk":
                            anydesk = True
                            break
                except OSError:
                    continue
            if anydesk:
                self._log("aviso: AnyDesk está activo; si la pantalla se "
                          "congela, ciérralo (la sesión gráfica y nvidia "
                          "pueden interferir).")
        except Exception:
            pass
        try:
            salida = subprocess.run(
                ["journalctl", "-k", "--since", "-2 hours", "--no-pager",
                 "--quiet"],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                universal_newlines=True, timeout=10)
            if "Failed to grab modeset" in (salida.stdout or ""):
                self._log("aviso: el kernel reportó fallas de modeset de "
                          "nvidia en las últimas 2 horas; si la pantalla se "
                          "congela, reinicia la sesión gráfica.")
        except Exception:
            pass

    def _ajustar_ventana(self):
        """
        Agranda la ventana si el contenido no entra, y solo lo necesario.

        El tamaño que ya tiene se pasa como piso, que es lo que hace que la
        ventana **solo crezca**: preguntar el tamaño actual a Tk no sirve
        porque antes de estar mapeada contesta 200x200 (ver ajuste.py), y con
        ese dato la ventana se encogería al abrir en vez de crecer.

        El tope lo pone ajuste.py: nunca se pasa de la pantalla ni de 1920x1080.
        """
        nuevo = ajuste.ajustar(self.raiz, minimo=self._tamanio)
        if tuple(nuevo) == tuple(self._tamanio):
            return
        self._tamanio = tuple(nuevo)
        self._log("Ventana ajustada a %dx%d px." % nuevo)

    def _ajustar_catalogos(self, minimo=(1000, 600)):
        """Agranda la ventana de catálogos a su contenido, si está creada."""
        if self.marco_catalogos is None:
            return
        try:
            ajuste.ajustar(self.marco_catalogos, minimo=minimo)
        except Exception:
            pass

    def _ajustar_popup(self, top, minimo):
        """
        Agranda una ventana secundaria a su contenido, sin achicarla.

        'minimo' es el tamaño con el que abrió. Se combina con el tamaño
        actual para que un cambio de pestaña o de informe solo pueda hacerla
        crecer; si la pantalla no alcanza, ajuste.py la acota y las tablas
        conservan su barra horizontal.
        """
        try:
            top.update_idletasks()
            ancho = max(int(minimo[0]), top.winfo_width())
            alto = max(int(minimo[1]), top.winfo_height())
            ajuste.ajustar(top, minimo=(ancho, alto))
        except Exception:
            self._log("[error ajuste] " + traceback.format_exc())

    def _alinear_pestanas(self, _evento=None):
        """Baja la barra de pestañas hasta la altura del botón de procesar.

        «Registro» arrancaba en el tope del área de contenido, arriba de donde
        arranca la barra lateral, y quedaba desfasado respecto de «Procesar
        catálogos». Se mide el desfasaje real en vez de escribir un número fijo
        para que siga valiendo si cambia el tema o la fuente; el cálculo es
        idempotente, así que un re-mapeo de la ventana no lo descoloca.
        """
        desfasaje = (self.boton_analisis.winfo_rooty()
                     - self.marco_pestanas.winfo_rooty())
        if desfasaje > 0:
            self.marco_pestanas.pack_configure(pady=(desfasaje, 0))

    def _construir_barra_pestanas(self, padre):
        """Dibuja la barra de pestañas agrupadas en filas.

        Va arriba del cuaderno, que muestra su propia tira oculta (ver
        _construir). Cada grupo es un encabezado con la fila de fuentes debajo.
        Los botones se indexan por FRAME y no por texto: "SeisComp" aparece en
        tres grupos distintos y el nombre no los distingue.
        """
        self.marco_pestanas = ttk.Frame(padre)
        self.marco_pestanas.pack(side=TOP, fill=X)

        for grupo in GRUPOS_PESTANAS:
            marco_grupo = ttk.Frame(self.marco_pestanas)
            marco_grupo.pack(fill=X, pady=(0, 4))
            titulo = grupo.get("titulo")
            if titulo:
                ttk.Label(marco_grupo, text=titulo, bootstyle="secondary",
                          font=("", 9, "bold")).pack(anchor=W)
            fila = ttk.Frame(marco_grupo)
            fila.pack(anchor=W)
            for clave in grupo["pestanas"]:
                marco = self._marco_de(clave)
                texto = self._texto_de(clave)
                boton = ttk.Button(
                    fila, text=texto,
                    command=lambda m=marco: self._ir_a_pestana(m),
                    bootstyle="secondary-outline")
                boton.pack(side=LEFT, padx=(0, 4))
                self._boton_pestana[marco] = boton

    def _marco_de(self, clave):
        """El frame del cuaderno que corresponde a una clave de pestaña."""
        if clave == "log":
            return self.marco_log
        tipo, _, nombre = clave.partition(":")
        panel = self.paneles.get(nombre)
        return panel["frame"] if panel else None

    def _texto_de(self, clave):
        """El texto corto del botón de esa pestaña."""
        if clave == "log":
            return "Registro"
        tipo, _, nombre = clave.partition(":")
        vista = VISTAS_POR_CLAVE.get(nombre)
        return vista["tab"] if vista else nombre

    def _ir_a_pestana(self, marco):
        # Se marca el botón al toque y no solo por el evento del cuaderno: el
        # <<NotebookTabChanged>> se entrega encolado, y con el evento solo el
        # resaltado llegaba un paso tarde (visible al hacer clic rápido).
        self.cuaderno.select(marco)
        self._marcar_pestana_activa()

    def _marcar_pestana_activa(self):
        """Pinta cuál es la pestaña activa en la barra de grupos.

        Se apoya en el evento <<NotebookTabChanged>>, así que los select()
        programáticos (abrir panel, abrir catálogo) actualizan el resaltado
        solos y no hay que acordarse de llamarlo en cada uno.
        """
        actual = self.cuaderno.select()
        for marco, boton in self._boton_pestana.items():
            activo = str(marco) == actual
            boton.configure(bootstyle="primary" if activo
                            else "secondary-outline")

    def _encabezado(self, marco, texto):
        """Rótulo de un bloque de la barra lateral."""
        ttk.Label(marco, text=texto, bootstyle="secondary").pack(
            anchor=W, pady=(0, 4))

    def _separador(self, marco):
        ttk.Separator(marco, orient=HORIZONTAL).pack(fill=X, pady=10)

    def _boton(self, marco, texto, fn, bootstyle=DEFAULT, disabled=False,
               gated=False, condicion=None):
        b = ttk.Button(marco, text=texto, command=fn, bootstyle=bootstyle,
                       width=26)
        b.pack(fill=X, pady=2)
        if disabled:
            b.configure(state=DISABLED)
        elif gated:
            self.botones_fuente.append(b)
        elif condicion is not None:
            self.condiciones.append((b,) + tuple(condicion))
            self._tooltip(b, condicion[1])
        else:
            self.botones.append(b)
        return b

    # ------------------------------------------------------------- logging
    def _log(self, texto):
        # Además del cuadro Tk, queda en informes/app.log con hora: sin esto,
        # un cuelgue deja todo en la nada (el texto Tk se pierde al cerrar).
        try:
            ruta = os.path.join("informes", "app.log")
            if os.path.isfile(ruta) and os.path.getsize(ruta) > 5 * 1024 * 1024:
                anterior = ruta + ".1"
                if os.path.isfile(anterior):
                    os.remove(anterior)
                os.rename(ruta, anterior)
            with open(ruta, "a", encoding="utf-8") as f:
                f.write("[%s] %s\n"
                        % (datetime.datetime.now().strftime("%H:%M:%S"), texto))
        except OSError:
            pass
        self.cola.put(("log", texto))

    def _drenar(self):
        try:
            while True:
                tipo, dato = self.cola.get_nowait()
                if tipo == "log":
                    self.txt.text.configure(state=NORMAL)
                    self.txt.text.insert(END, dato + "\n")
                    self.txt.text.see(END)
                    self.txt.text.configure(state=DISABLED)
                elif tipo == "fin":
                    self._set_ocupado(False)
                    if callable(dato):
                        try:
                            dato()
                        except Exception:
                            self._log("[error] " + traceback.format_exc())
                    try:
                        self._aplicar_progreso(1.0, "Listo")
                    except Exception:
                        self._log("[error progreso] "
                                  + traceback.format_exc())
                elif tipo == "prog":
                    self._aplicar_progreso(dato[0], dato[1])
                elif tipo == "msg":
                    Messagebox.show_info(dato, "Información",
                                         parent=self.raiz)
        except queue.Empty:
            pass
        except Exception:
            # Si el drenaje revienta, la app quedaría muda para siempre: se
            # anota y se sigue. El after se re-agenda en finally, pase lo que
            # pase.
            self._log("[error drenar] " + traceback.format_exc())
        finally:
            self._after_drenar = self.raiz.after(100, self._drenar)

    def _set_ocupado(self, valor):
        self.ocupado = valor
        estado = DISABLED if valor else NORMAL
        for b in self.botones:
            b.configure(state=estado)
        self._actualizar_gate()

    def _actualizar_gate(self):
        if self.ocupado:
            estado_fuente = DISABLED
        else:
            estado_fuente = NORMAL if self.analisis_hecho else DISABLED
        # «Procesar catálogos» solo se habilita si están los insumos mínimos
        # (el CSV de eventquery y select.out). Si falta alguno, se avisa en la
        # barra y se re-exporta.
        self.boton_analisis.configure(
            state=DISABLED if (self.ocupado or not self._puede_procesar())
            else NORMAL)
        for b in self.botones_fuente:
            b.configure(state=estado_fuente)
        for b, puede, _ in self.condiciones:
            b.configure(state=(NORMAL if puede() and not self.ocupado
                               else DISABLED))
        self._actualizar_estado_catalogos()

    # ----------------------------------------------------------- catálogos
    def _puede_procesar(self):
        """Si están los insumos mínimos para correr el análisis."""
        if not self.archivo or not os.path.isfile(self.archivo):
            return False
        return os.path.isfile(os.path.join("select.out"))

    def _analisis_obsoleto(self):
        """
        True si el análisis quedó viejo respecto de sus catálogos de entrada.

        Se re-exportó el select (o el CSV de eventquery) después del último
        análisis: los paneles no deben mostrar los datos viejos como si fueran
        actuales.
        """
        salida = os.path.join("datos", "salida_collect.csv")
        if not os.path.isfile(salida):
            return False
        try:
            mtime = os.path.getmtime(salida)
        except OSError:
            return False
        select = os.path.join("select.out")
        if os.path.isfile(select) and os.path.getmtime(select) > mtime:
            return True
        new2 = os.path.join("datos", "new_2_" + self.base)
        if (self.archivo and os.path.isfile(self.archivo)
                and os.path.isfile(new2)
                and os.path.getmtime(self.archivo) > os.path.getmtime(new2)):
            return True
        return False

    def _periodo(self):
        """(inicio, fin) en 14 dígitos, del estado o inferido de los nombres."""
        inicio, fin = self.periodo
        if inicio and fin:
            return inicio, fin
        import glob
        import re
        for patron in ("select_*_*.out", "eventquery_*_*.csv"):
            for ruta in sorted(glob.glob(patron)):
                m = re.match(r".*_(\d{14})_(\d{14})\.[^.]+$",
                             os.path.basename(ruta))
                if m:
                    return m.group(1), m.group(2)
        return None, None

    def _estado_catalogo(self, catalogo):
        """Estado del catálogo pedido para los chips y el botón de re-exportar."""
        if catalogo == "Seisan":
            insumo = "select.out"
            derivado = os.path.join("datos", "salida_collect.csv")
            tiene_datos = (os.path.isfile(insumo)
                           and tc.select_tiene_eventos(insumo))
        elif catalogo == "eventquery":
            insumo = self.archivo
            derivado = os.path.join("datos", "new_2_" + self.base)
            tiene_datos = bool(insumo) and rutas.csv_tiene_filas(insumo)
        elif catalogo == "SeisComp":
            par = self._par_seiscomp_para_catalogo(silencioso=True)
            insumo = par["eventos"] if par is not None else None
            derivado = os.path.join("datos", "seiscomp_parametros.csv")
            tiene_datos = bool(insumo) and rutas.csv_tiene_filas(insumo)
        else:
            return "ok"
        if not insumo or not os.path.isfile(insumo):
            # No está: si la extracción de esta sesión lo reportó como fallante,
            # fue un fallo; si no, simplemente no está (se borró o similar).
            return "fallo" if catalogo in self.catalogos_faltantes else "falta"
        if not tiene_datos:
            return "sin_datos"
        # Sin derivado todavía, el análisis no corrió: el catálogo está, no hay
        # nada que re-exportar. Solo es "cambio" si el insumo es más nuevo que
        # un derivado que ya existía.
        if not os.path.isfile(derivado):
            return "ok"
        if not rutas.csv_tiene_filas(derivado):
            return "sin_datos"
        try:
            return ("cambio" if os.path.getmtime(insumo)
                    > os.path.getmtime(derivado) else "ok")
        except OSError:
            return "ok"

    def _puede_re_exportar(self, catalogo):
        # Con «Forzar actualización» se habilita aunque el catálogo esté al día.
        if self.forzar_actualizacion.get():
            return True
        return self._estado_catalogo(catalogo) != "ok"

    def _motivo_re_exportar(self, catalogo):
        estado = self._estado_catalogo(catalogo)
        if estado == "fallo":
            return ("La extracción de %s falló. Use este botón para volver a "
                    "intentarlo." % catalogo)
        if estado == "falta":
            return ("El catálogo de %s no está (¿se borró?). Use este botón "
                    "para volver a obtenerlo." % catalogo)
        if estado == "cambio":
            return ("%s cambió desde el último procesamiento. Re-expórtelo y "
                    "vuelva a procesar." % catalogo)
        if estado == "sin_datos":
            return ("El catálogo de %s no tiene eventos en la ventana; puede "
                    "estar fuera de cobertura. Use este botón para "
                    "re-exportarlo." % catalogo)
        return ("El catálogo de %s está al día; no hace falta re-exportarlo."
                % catalogo)

    def _actualizar_estado_catalogos(self):
        """Refresca los chips por catálogo y el aviso resumen."""
        for catalogo, chip in self.chips_catalogo.items():
            texto, estilo = ESTADOS_CATALOGO[self._estado_catalogo(catalogo)]
            chip.configure(text=texto, bootstyle=estilo)
        partes = []
        for catalogo in ("Seisan", "eventquery", "SeisComp"):
            estado = self._estado_catalogo(catalogo)
            if estado == "ok":
                continue
            texto, _ = ESTADOS_CATALOGO[estado]
            partes.append("%s: %s" % (texto, catalogo))
        if not partes:
            self.aviso_catalogos.configure(text="✓ Catálogos OK.",
                                           bootstyle="success")
            return
        estilo = "danger" if any("✗" in p for p in partes) else "warning"
        self.aviso_catalogos.configure(text=" · ".join(partes),
                                       bootstyle=estilo)

    def _re_exportar(self, catalogo):
        """Re-importa un catálogo y, siempre, vuelve a correr el análisis.

        Re-importar uno solo ya obliga a reprocesar, porque los datos cruzan
        entre catálogos (comparación, atribución a SeisComp, repetidos, No
        publicados, mapas y perfiles). Por eso el aviso previo lo dice y, al
        terminar la descarga, el análisis corre solo.
        """
        if self.ocupado:
            return
        if not self._confirmar_reimportar(catalogo):
            self._log("Re-exportación cancelada.")
            return
        if catalogo == "SeisComp":
            radio = self._pedir_radio(self._radio_seiscomp_actual())
            if radio is None:
                self._log("Re-exportación cancelada.")
                return
            inicio, fin = self._periodo()
            if inicio and fin and not self._confirmar_tamano_seiscomp(
                    radio, inicio, fin):
                self._log("Re-exportación cancelada por el tamaño estimado.")
                return

            def tarea():
                self._tarea_re_exportar_seiscomp(radio)
                # Refresca el panel con la exportación que se acaba de escribir.
                self._procesar_fuente("seiscomp")
        else:
            contrasena = self._pedir_contrasena()
            if not contrasena:
                self._log("Re-exportación cancelada.")
                return
            tarea = (lambda c=catalogo, p=contrasena:
                     self._tarea_re_exportar_red(c, p))

        def al_terminar():
            self.catalogos_faltantes.discard(catalogo)
            if self._seiscomp_sin_eventos:
                # Al reprocesar, el panel de SeisComp quedará sin datos. Se
                # vuelve a habilitar el aviso para que _al_terminar_procesar
                # lo muestre.
                self._seiscomp_sin_eventos = False
                self._avisos_sin_datos_mostrados.discard("SeisComp")
            self._actualizar_gate()
            # El popup previo ya avisó que se reprocesa: se hace sin preguntar
            # de nuevo.
            self._accion_procesar(confirmar=False)

        self._iniciar(tarea, on_fin=al_terminar, plan=None)

    def _confirmar_reimportar(self, catalogo):
        """
        Aviso previo a re-importar: al hacerlo se fuerza el análisis.

        No es solo un cambio de archivo: lo que entrega la app cruza datos
        entre catálogos, así que re-importar uno obliga a reprocesar todo.
        """
        texto = (
            "Vas a re-importar el catálogo de %s.\n\n"
            "La información que entrega la app cruza datos entre los catálogos "
            "(comparación publicados vs procesados, atribución a SeisComp, "
            "revisión de repetidos, No publicados, mapas y perfiles), así que "
            "al re-importarlo se forzará el análisis y se reprocesarán los "
            "catálogos actuales (Seisan, Eventquery y SeisComp).\n\n"
            "Puede tardar unos minutos. ¿Continuar?" % catalogo)
        return Messagebox.show_question(
            texto, "Re-importar y reprocesar", parent=self.raiz,
            buttons=["Forzar y reprocesar:primary",
                     "Cancelar"]) == "Forzar y reprocesar"

    def _tarea_re_exportar_seiscomp(self, radio):
        inicio, fin = self._periodo()
        if not (inicio and fin):
            self._log("No se pudo determinar el período a exportar.")
            return
        self._log("***** Re-exportando SeisComp (%s - %s, radio %.0f km) *****"
                  % (inicio, fin, radio))
        if self._popen([_script("verifica_entorno.py")]):
            self._log("El entorno no está listo; no se exportó SeisComp.")
            return
        exportador = _script("exporta_ventana_seiscomp.py")
        # Sin --reusar: re-exportar es forzar, así que se reconsulta la base.
        if self._popen([exportador, "--radio-km", "%g" % radio,
                        inicio, fin]):
            self._log("La exportación de SeisComp falló (ver el registro).")
            return
        marca = os.path.join(
            "datos", "seiscomp_%s_%s.csv.completo" % (inicio, fin))
        try:
            import exporta_ventana_seiscomp as ev
            eventos = ev._eventos_de_la_marca(marca)
        except Exception:
            eventos = None
        self._seiscomp_sin_eventos = (eventos == 0)
        if self._seiscomp_sin_eventos:
            self._log("[Aviso] SeisComp no tiene eventos en la ventana; "
                      "puede estar fuera de la cobertura de las bases.")
        self._log("SeisComp re-exportado.")

    def _tarea_re_exportar_red(self, catalogo, contrasena):
        import traer_catalogos as tc
        inicio, fin = self._periodo()
        if not (inicio and fin):
            self._log("No se pudo determinar el período a re-exportar.")
            return
        self._log("***** Re-exportando %s (%s - %s) *****"
                  % (catalogo, inicio, fin))
        with tc.Conexion(contrasena, log=self._log) as conexion:
            tc.verificar_conexion(conexion, log=self._log,
                                  progreso=self._progreso_local)
            if catalogo == "Seisan":
                ruta = tc.traer_seisan(inicio, fin, conexion, cwd=self.cwd,
                                       log=self._log,
                                       progreso=self._progreso_local,
                                       forzar=True)
                # copy2 preserva la fecha del select que se acaba de bajar;
                # copyfile la pondría en "ahora" y select.out parecería más
                # nuevo.
                shutil.copy2(ruta, os.path.join(self.cwd, "select.out"))
                self._log("select.out actualizado desde %s"
                          % os.path.basename(ruta))
            else:
                tc.traer_eventquery(inicio, fin, conexion, cwd=self.cwd,
                                    log=self._log,
                                    progreso=self._progreso_local,
                                    forzar=True)
        self._log("%s re-exportado." % catalogo)

    def _pedir_contrasena(self):
        """Diálogo simple para la contraseña del servidor remoto."""
        top = Toplevel(self.raiz)
        top.title("Contraseña del servidor")
        top.transient(self.raiz)
        top.grab_set()
        marco = ttk.Frame(top, padding=12)
        marco.pack(fill=BOTH, expand=YES)
        ttk.Label(marco, text="Contraseña del servidor remoto:").pack(anchor=W)
        entrada = ttk.Entry(marco, show="*", width=28)
        entrada.pack(fill=X, pady=(4, 10))
        entrada.focus_set()
        resultado = {"valor": None}

        def aceptar(_evento=None):
            resultado["valor"] = entrada.get()
            top.destroy()

        def cancelar(_evento=None):
            top.destroy()

        botones = ttk.Frame(marco)
        botones.pack(fill=X)
        ttk.Button(botones, text="Aceptar", command=aceptar,
                   bootstyle="primary").pack(side=RIGHT)
        ttk.Button(botones, text="Cancelar", command=cancelar,
                   bootstyle="secondary").pack(side=RIGHT, padx=(0, 6))
        entrada.bind("<Return>", aceptar)
        top.bind("<Escape>", cancelar)
        self.raiz.wait_window(top)
        return resultado["valor"]

    def _pedir_radio(self, defecto):
        """Diálogo para el radio (km) de estaciones sin arribos de SeisComp."""
        top = Toplevel(self.raiz)
        top.title("Radio de estaciones SeisComp")
        top.transient(self.raiz)
        top.grab_set()
        marco = ttk.Frame(top, padding=12)
        marco.pack(fill=BOTH, expand=YES)
        ttk.Label(marco, text="Radio de búsqueda de estaciones sin arribos"
                             " (km, solo SeisComp):").pack(anchor=W)
        entrada = ttk.Entry(marco, width=12)
        entrada.insert(0, "%g" % defecto)
        entrada.pack(anchor=W, pady=(4, 10))
        entrada.focus_set()
        entrada.selection_range(0, END)
        resultado = {"valor": None}

        def aceptar(_evento=None):
            try:
                valor = float(entrada.get().strip().rstrip("kKmM"))
            except ValueError:
                return
            if valor <= 0:
                return
            resultado["valor"] = valor
            top.destroy()

        def cancelar(_evento=None):
            top.destroy()

        botones = ttk.Frame(marco)
        botones.pack(fill=X)
        ttk.Button(botones, text="Aceptar", command=aceptar,
                   bootstyle="primary").pack(side=RIGHT)
        ttk.Button(botones, text="Cancelar", command=cancelar,
                   bootstyle="secondary").pack(side=RIGHT, padx=(0, 6))
        entrada.bind("<Return>", aceptar)
        top.bind("<Escape>", cancelar)
        self.raiz.wait_window(top)
        return resultado["valor"]

    def _radio_seiscomp_actual(self):
        """El radio de la exportación vigente, o el valor por defecto.

        Se lee de la marca de fin, que anota con qué radio se calculó la lista
        de estaciones. Si no hay exportación o no se puede leer, cae al valor
        por defecto del exportador.
        """
        try:
            import exporta_ventana_seiscomp as ev
            defecto = ev.RADIO_ESTACIONES_KM
        except Exception:
            ev = None
            defecto = 400.0
        inicio, fin = self._periodo()
        if ev is not None and inicio and fin:
            marca = os.path.join("datos", "seiscomp_%s_%s.csv.completo"
                                 % (inicio, fin))
            radio = ev._radio_de_la_marca(marca)
            if radio is not None:
                return radio
        return defecto

    def _confirmar_tamano_seiscomp(self, radio, inicio, fin):
        """Pide confirmación si la exportación de SeisComp quedaría enorme.

        El archivo de no picadas crece con los eventos y con el radio, y en el
        histórico pasa de un gigabyte. Si la exportación se va a reutilizar (el
        radio coincide con la marca) no hay nada que estimar. Ante cualquier
        error se sigue sin preguntar: es un aviso, no un requisito.
        """
        try:
            from datetime import datetime
            import exporta_ventana_seiscomp as ev
        except Exception:
            return True
        marca = os.path.join("datos", "seiscomp_%s_%s.csv.completo"
                             % (inicio, fin))
        radio_marca = ev._radio_de_la_marca(marca)
        if radio_marca is not None and abs(radio_marca - round(radio)) < 0.5:
            return True
        try:
            ini_dt = datetime.strptime(inicio, "%Y%m%d%H%M%S")
            fin_dt = datetime.strptime(fin, "%Y%m%d%H%M%S")
            bases = ev._bases_a_consultar(None)
            _filas, mb = ev.estimar_no_picadas(bases, ini_dt, fin_dt, radio)
        except Exception:
            return True
        if mb < ev.AVISO_NO_PICADAS_MB:
            return True
        texto = ("Con radio %.0f km esta ventana generaría alrededor de %.0f MB"
                 " de estaciones sin arribos. El revisor lo escanea al abrir y"
                 " puede tardar.\n\n¿Continuar?" % (radio, mb))
        return Messagebox.show_question(
            texto, "Exportación grande", parent=self.raiz,
            buttons=["Continuar:primary", "Cancelar"]) == "Continuar"

    def _tooltip(self, widget, motivo):
        """
        Tooltip mínimo que sale solo con el botón apagado.

        ttkbootstrap.tooltip no se puede usar aquí: usa typing.Literal, que
        existe desde Python 3.8, y la app corre en 3.7. Por eso son veinte
        líneas de Toplevel en vez de un import.

        El motivo se evalúa al entrar, no al crear el widget: depende del
        estado de los archivos y cambia con el correr del tiempo. Se acepta
        tanto una función como un texto fijo, para que un motivo constante (o
        vacío) no se intente llamar como función.
        """
        if not callable(motivo):
            fijo = motivo
            motivo = lambda: fijo

        def entrar(_evento=None):
            if widget.instate(["disabled"]):
                texto = motivo()
                if texto:
                    self._mostrar_ayuda(widget, texto)

        def salir(_evento=None):
            self._ocultar_ayuda(widget)

        widget.bind("<Enter>", entrar, add="+")
        widget.bind("<Leave>", salir, add="+")

    def _mostrar_ayuda(self, widget, texto):
        self._ocultar_ayuda()
        # Toplevel de tkinter y NO de ttkbootstrap: el de ttkbootstrap, en x11,
        # entra en wait_visibility() dentro de su __init__ (porque alpha viene
        # en 1.0 por defecto), que es un event loop anidado y bloqueante. Pasa
        # antes de que se pueda poner overrideredirect, así que el window
        # manager decide dónde queda la ventana: appeared en cualquier lado, y
        # además el anidamiento reentra al loop de la app justo en un evento de
        # mouse. Con tkinter la posición pedida se respeta.
        top = Toplevel(widget)
        top.overrideredirect(True)
        ttk.Label(top, text=texto, justify=LEFT, wraplength=240,
                  padding=6, background="#fff8dc").pack()
        top.update_idletasks()
        # Abajo del botón, y no encima: si el tooltip se superpone al widget,
        # el mouse "sale" de él, se borra el tooltip, vuelve a entrar y el
        # ciclo se repite en parpadeo.
        top.geometry("+%d+%d" % (widget.winfo_rootx(),
                                 widget.winfo_rooty() + widget.winfo_height()))
        self._ayuda = (widget, top)

    def _ocultar_ayuda(self, widget=None):
        """
        Cierra el tooltip.

        El widget se chequea porque al pasar de un botón a otro Tk no garantiza
        el orden de <Leave> y <Enter>: si entra en el nuevo antes de salir del
        anterior, el <Leave> del viejo borraría el tooltip del nuevo.
        """
        ayuda = getattr(self, "_ayuda", None)
        if ayuda is None:
            return
        duenio, top = ayuda
        if widget is not None and duenio is not widget:
            return
        try:
            top.destroy()
        except TclError:
            pass
        self._ayuda = None

    def _actualizar_estado(self):
        if self.analisis_en_curso:
            self.etiqueta_estado.configure(
                text="Catálogos: procesando…", bootstyle="warning")
        elif self.analisis_hecho:
            self.etiqueta_estado.configure(
                text="Catálogos: procesados", bootstyle="success")
        else:
            self.etiqueta_estado.configure(
                text="Catálogos: sin procesar", bootstyle="secondary")

    def _autodetectar_estado(self):
        """
        Reconoce en el directorio de ejecución qué pestañas pueden mostrarse.

        No genera nada: deja cada panel en su placeholder correcto (con datos,
        pendiente de procesar o sin datos) y registra el resumen. La generación
        de los pendientes es perezosa, al abrir su pestaña (ver
        _abrir_panel_si_puede).
        """
        obsoleto = self._analisis_obsoleto()
        self.analisis_hecho = (
            os.path.isfile(os.path.join("datos", "salida_collect.csv"))
            and not obsoleto)
        listas, pendientes = [], []
        for clave, vista in VISTAS_POR_CLAVE.items():
            if obsoleto:
                self._placeholder_panel(
                    clave, "Los catálogos cambiaron desde el último "
                           "análisis.\n\nPulse «Procesar catálogos» para "
                           "regenerar el panel de %s." % vista["etiqueta"])
            elif self._vista_procesada(clave):
                listas.append(clave)
                self._placeholder_panel(
                    clave, "Hay datos procesados de %s.\n\nAbra la pestaña "
                           "para verlos." % vista["etiqueta"])
            elif os.path.isfile(vista["entrada"]):
                pendientes.append(clave)
                self._placeholder_panel(
                    clave, "Hay datos sin procesar de %s.\n\nAl abrir esta "
                           "pestaña se genera el panel."
                           % vista["etiqueta"])
            else:
                self._placeholder_panel(
                    clave, "No hay datos de %s para mostrar.\n\nPulse "
                           "«Procesar catálogos» para generarlos."
                           % vista["etiqueta"])
        if obsoleto:
            self._log("El análisis quedó obsoleto (los catálogos son más "
                      "nuevos); vuelva a «Procesar catálogos».")
        if listas:
            self._log("Paneles ya procesados: %s." % ", ".join(listas))
        if pendientes:
            self._log("Paneles pendientes (se generan al abrir su pestaña): "
                      "%s." % ", ".join(pendientes))
        if self.analisis_hecho:
            self._log("Se detectaron resultados del análisis; fuentes "
                      "habilitadas.")
        mensajes = []
        if self.catalogos_faltantes:
            faltan = ", ".join(sorted(self.catalogos_faltantes))
            self._log("***** Faltan catálogos: %s. Use «Re-exportar». *****"
                      % faltan)
            mensajes.append("No se pudieron obtener: %s." % faltan)
        ya_avisados = {a.get("catalogo") for a in self.avisos_catalogos
                       if isinstance(a, dict)}
        sin_datos = []
        for catalogo in ("Seisan", "eventquery", "SeisComp"):
            if self._estado_catalogo(catalogo) != "sin_datos":
                continue
            sin_datos.append(catalogo)
            self._avisos_sin_datos_mostrados.add(catalogo)
            if catalogo not in ya_avisados:
                mensajes.append("%s no tiene eventos en la ventana."
                                % catalogo)
        if sin_datos:
            self._log("***** Catálogos sin datos: %s. *****"
                      % ", ".join(sin_datos))
        for aviso in self.avisos_catalogos:
            if not isinstance(aviso, dict):
                continue
            texto_aviso = aviso.get("mensaje")
            if texto_aviso and texto_aviso not in mensajes:
                mensajes.append(texto_aviso)
        if mensajes:
            texto = ("\n\n".join(mensajes) + "\n\nUse «Re-exportar» si "
                     "necesita volver a obtenerlos.")
            self._after_msg = self.raiz.after(
                300, lambda t=texto: Messagebox.show_warning(
                    t, "Avisos de catálogos", parent=self.raiz))
        self._actualizar_estado()
        self._actualizar_gate()

    def _placeholder_panel(self, clave, texto):
        """Deja el placeholder de un panel con el texto dado."""
        panel = self.paneles.get(clave)
        if panel is None:
            return
        for w in list(panel["frame"].winfo_children()):
            w.destroy()
        etiqueta = ttk.Label(panel["frame"], justify=CENTER, text=texto)
        etiqueta.pack(expand=YES)
        panel["etiqueta"] = etiqueta
        panel["construido"] = False

    def _vista_procesada(self, clave):
        """
        True si el JSON de la vista es más nuevo que su CSV de entrada.

        Es lo que decide si el botón de la fuente queda apagado: mientras el
        JSON siga siendo el resultado del CSV actual, reprocesar daría el mismo
        panel. Cuando el análisis reescribe el CSV, el botón se enciende solo.
        """
        if self._analisis_obsoleto():
            return False
        vista = VISTAS_POR_CLAVE.get(clave)
        if vista is None:
            return False
        json_path = os.path.join("datos", "eventos_%s.json" % clave)
        if not os.path.isfile(json_path):
            return False
        if clave == "eventquery":
            # El CSV derivado (todos_eventquery.csv) no lo refresca el análisis,
            # lo arma _concatenar_eventquery. La frescura hay que medirla contra
            # los new_2_*.csv, que sí cambian con cada análisis: si no, un JSON
            # viejo parecería al día y el panel quedaría con datos de menos.
            entradas = self._partes_eventquery()
            if not entradas:
                return False
            mas_nuevo = max(os.path.getmtime(r) for r in entradas)
            return os.path.getmtime(json_path) >= mas_nuevo
        entrada = vista["entrada"]
        if not os.path.isfile(entrada):
            return False
        return os.path.getmtime(json_path) >= os.path.getmtime(entrada)

    @staticmethod
    def _partes_eventquery(carpeta="datos"):
        """Rutas de los new_2_*.csv, ordenadas, o [] si no hay."""
        try:
            nombres = sorted(n for n in os.listdir(carpeta)
                             if n.startswith("new_2_") and n.endswith(".csv"))
        except OSError:
            return []
        return [os.path.join(carpeta, n) for n in nombres]

    # ------------------------------------------------------------- progreso
    def _aplicar_progreso(self, fraccion, texto):
        """Actualiza la barra (monótona) y la etiqueta con % + etapa."""
        frac = max(0.0, min(1.0, fraccion))
        val = int(round(frac * 1000))
        if val > self.barra_valor:
            self.barra_valor = val
            self.barra.configure(value=val)
        self.barra_texto.configure(
            text="%d %% · %s" % (round(frac * 100), texto))

    def _fijar_etapa(self, indice):
        """Posiciona la etapa actual según el plan y muestra su inicio."""
        if not self.plan_etapas:
            return
        indice = max(0, min(indice, len(self.plan_etapas) - 1))
        etapa = self.plan_etapas[indice]
        self.etapa_base = sum(p["peso"] for p in self.plan_etapas[:indice])
        self.etapa_ancho = etapa["peso"]
        self.etapa_nombre = etapa["nombre"]
        self.cola.put(("prog", (self.etapa_base, self.etapa_nombre)))

    def _progreso_local(self, fraccion):
        """Mapea la fracción [0,1] del script dentro del peso de la etapa."""
        frac = max(0.0, min(1.0, fraccion))
        global_v = self.etapa_base + self.etapa_ancho * frac
        self.cola.put(("prog", (global_v, self.etapa_nombre)))

    def _preparar_etapa_script(self, nombre_script, argumentos=()):
        try:
            nombre_script = os.path.basename(nombre_script)
        except TypeError:
            return
        etapas = self.plan_etapas or ()
        # Una etapa puede pedir un discriminador. Hace falta porque el mismo
        # script corre más de una vez en el plan con entradas distintas
        # (compara.py compara Seisan y después SeisComp) y con el nombre solo
        # no se sabe cuál de las dos es: se ganaría siempre la primera.
        for i, e in enumerate(etapas):
            marca = e.get("discriminador")
            # El script también tiene que coincidir: si no, un discriminator
            # como "salida_collect.csv" lo ganaría cualquier etapa cuyo script
            # reciba ese archivo (p. ej. compara.py), no solo la buscada.
            if (marca is not None
                    and nombre_script in e.get("scripts", ())
                    # any(...) y no `marca in argumentos`: los argumentos llegan
                    # como rutas completas ("datos/seiscomp_parametros.csv"),
                    # así que tiene que ser coincidencia parcial y no igualdad
                    # de elemento.
                    and any(marca in str(a) for a in argumentos)):
                self._fijar_etapa(i)
                return
        for i, e in enumerate(etapas):
            if nombre_script in e.get("scripts", ()):
                self._fijar_etapa(i)
                return

    # ------------------------------------------------------------ procesos
    def _popen(self, args, cwd=None):
        args = list(args)
        script = args[0] if args and args[0].endswith(".py") else None
        if script:
            args = [PY] + args
        self._log("$ " + " ".join(args))
        if script:
            self._preparar_etapa_script(script, args)
        env = dict(os.environ)
        env["RV_PROG"] = "1"
        try:
            p = subprocess.Popen(args, cwd=(cwd or self.cwd),
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT,
                                 universal_newlines=True, bufsize=1,
                                 env=env)
        except Exception as e:
            self._log("[error] no se pudo ejecutar: %s" % e)
            return 1
        for linea in p.stdout:
            linea = linea.rstrip("\n")
            if linea.startswith(MARCA_PROGRESO):
                partes = linea.split(None, 1)
                try:
                    self._progreso_local(float(partes[1]))
                except (IndexError, ValueError):
                    pass
                continue
            self._log(linea)
        p.wait()
        if p.returncode:
            self._log("[código de salida %d]" % p.returncode)
        return p.returncode

    def _iniciar(self, tarea, on_fin=None, plan=None):
        if self.ocupado:
            return
        self.plan_etapas = plan
        self.barra_valor = 0
        self.barra.configure(value=0)
        self.barra_texto.configure(text="0 % · Iniciando…")
        self._set_ocupado(True)

        def envolver():
            try:
                tarea()
            except Exception:
                self._log("[error] " + traceback.format_exc())
            finally:
                self.cola.put(("fin", on_fin))

        threading.Thread(target=envolver, daemon=True).start()

    # ------------------------------------------------------------ acciones
    def _procesar_analisis(self):
        """
        Pipeline pesado de análisis. Síncrono: corre dentro de una tarea.

        No pregunta nada ni toca el estado de la app; de eso se encargan los
        envoltorios (_accion_procesar y _accion_fuente).
        """
        self._log("***** Se comienza el análisis de los datos *****")
        # Borra derivados de ventanas anteriores para evitar mezclas en
        # _concatenar_eventquery (que junta TODOS los new_2_*.csv).
        carpeta_datos = "datos"
        try:
            for nombre in os.listdir(carpeta_datos):
                if nombre.startswith("new_") and nombre.endswith(".csv"):
                    os.remove(os.path.join(carpeta_datos, nombre))
        except OSError:
            pass
        self._popen([_script("proc_query_harz_2.py"),
                     self.archivo, self.salida])
        self._popen([_script("revisaselect.py")])
        self._popen([_script("revisacollect.py")])
        self._log("***** Comparando publicados v/s procesados *****")
        self._popen([_script("compara.py"),
                     os.path.join("datos", "new_2_" + self.base),
                     os.path.join("datos", "salida_collect.csv")])
        # La atribución a SeisComp es la misma comparación con las soluciones
        # preferred en vez de las de Seisan: deja en no_act_seiscomp_*.txt qué
        # publicado quedó desactualizado y a quién le corresponde. Se saltea si
        # no hay exportación, porque la ventana del catálogo puede no haberse
        # descargado nunca.
        parametros = os.path.join("datos", "seiscomp_parametros.csv")
        self._asegurar_parametros_seiscomp()
        if os.path.isfile(parametros) and os.path.getsize(parametros) > 0:
            self._log("***** Atribuyendo publicados a SeisComp *****")
            self._popen([_script("compara.py"),
                         os.path.join("datos", "new_2_" + self.base),
                         parametros, "seiscomp_"])
        else:
            self._log("Sin datos de SeisComp: se omite la atribución.")
        self._log("***** Cruzando no publicados con la otra fuente *****")
        self._popen([_script("cruza_nopub.py")])
        excl = os.path.join("informes", "excluidos.txt")
        if os.path.isfile(excl) and os.path.getsize(excl) > 0:
            self._log("***** Revisando excluidos *****")
            self._popen([_script("revisaexcluidos.py")])
            self._popen([_script("repetidosexclu.py"),
                         os.path.join("datos", "excluidos.csv"),
                         os.path.join("datos", "salida_collect.csv")])
        else:
            for f in (excl, os.path.join("trabajo", "excluidostmp1.txt")):
                try:
                    os.remove(f)
                except OSError:
                    pass
            self._log("No se excluyeron eventos del select.out")
        self._log("***** Se revisan repetidos *****")
        args_repetidos = [_script("repetidos.py"),
                          os.path.join("datos", "new_2_" + self.base),
                          os.path.join("datos", "salida_collect.csv")]
        # El catálogo de SeisComp se revisa con el mismo script: mismo layout de
        # 8 columnas, así que solo hay que pasarle el CSV.
        if os.path.isfile(parametros) and os.path.getsize(parametros) > 0:
            args_repetidos.append(parametros)
        self._popen(args_repetidos)
        try:
            os.remove(self.salida)
        except OSError:
            pass
        self._log("***** Análisis terminado *****")
        self._limpiar_trabajo_y_ploteo()

    def _accion_procesar(self, confirmar=True):
        """
        Botón maestro «Procesar catálogos».

        Corre el análisis y, con los mismos catálogos ya en disco, genera el
        JSON de todas las pestañas de panel y arma las de catálogo. Una sola
        pulsación deja toda la información disponible para consultar; las
        fuentes que ya estaban al día se omiten, así que volver a pulsarlo
        rehace solo lo vencido.

        Con 'confirmar=False' no pregunta: lo usa la re-exportación, que ya
        avisó en su popup previo que al re-importar se reprocesa.
        """
        if not self.archivo:
            self._log("No se especificó archivo de entrada.")
            return
        # Volver a ejecutarlo es una acción legítima pero son minutos de
        # trabajo, así que se pregunta antes. El botón queda habilitado
        # siempre, con la compuerta aprobando que se vuelva a pulsar. Si el
        # análisis quedó obsoleto (se re-exportó un catálogo), no se pregunta:
        # reprocesar es justamente lo que hay que hacer.
        if confirmar and self.analisis_hecho and not self._analisis_obsoleto():
            texto = ("Volver a procesar los catálogos va a regenerar los "
                     "datos de %s.\n\nLo que ya estaba procesado vuelve a "
                     "quedar para rehacer, porque su CSV de entrada "
                     "cambió.\n\n¿Continuar?"
                     % os.path.basename(self.archivo))
            if Messagebox.show_question(texto, "Volver a procesar catálogos",
                                        parent=self.raiz,
                                        buttons=["Procesar:primary",
                                                 "Cancelar"]) != "Procesar":
                self._log("Procesamiento cancelado.")
                return

        def tarea():
            self._procesar_analisis()
            # SeisComp primero: deja seiscomp_parametros.csv, que la atribución
            # de eventquery necesita. Si no hay exportación, _procesar_fuente lo
            # avisa y sigue.
            for fuente in ("seiscomp", "seisan", "eventquery", "nopub",
                           "nopub_seiscomp", "noact", "noact_seiscomp"):
                vista_clave = FUENTE_A_VISTA.get(fuente)
                if vista_clave and self._vista_procesada(vista_clave):
                    self._log("La fuente %s ya estaba procesada; se omite."
                              % vista_clave)
                    continue
                self._procesar_fuente(fuente)
            self._poblar_catalogos()
            self._log("***** Procesamiento terminado *****")

        self.analisis_en_curso = True
        self._actualizar_estado()
        self._iniciar(tarea, on_fin=self._al_terminar_procesar,
                      plan=PROCESAR_PLAN)

    def _al_terminar_procesar(self):
        self.analisis_en_curso = False
        self.analisis_hecho = os.path.isfile(
            os.path.join("datos", "salida_collect.csv"))
        if self.analisis_hecho:
            self._log("Procesamiento completado: las pestañas ya tienen sus "
                      "datos.")
        else:
            self._log("El procesamiento no generó datos/salida_collect.csv; "
                      "revise el registro.")
        self._actualizar_estado()
        self._actualizar_gate()
        self._avisar_sin_datos()

    def _avisar_sin_datos(self):
        """Avisa una sola vez por catálogo que quedó sin eventos."""
        nuevos = []
        for catalogo in ("Seisan", "eventquery", "SeisComp"):
            if (self._estado_catalogo(catalogo) == "sin_datos"
                    and catalogo not in self._avisos_sin_datos_mostrados):
                self._avisos_sin_datos_mostrados.add(catalogo)
                nuevos.append(catalogo)
        if not nuevos:
            return
        self._log("***** Catálogos sin datos: %s. *****" % ", ".join(nuevos))
        Messagebox.show_warning(
            "Sin eventos en la ventana: %s.\n\nPuede que la ventana quede "
            "fuera de la cobertura de la fuente. Use «Re-exportar» si "
            "necesita volver a obtenerlos." % ", ".join(nuevos),
            "Catálogos sin datos", parent=self.raiz)

    def _poblar_catalogos(self):
        """
        Llena las pestañas de catálogo al terminar «Procesar catálogos».

        Las tres salen del análisis: Seisan de salida_collect.csv, eventquery
        del concatenado de los new_2_*.csv y SeisComp de la exportación que
        dejó la solicitud de catálogos. No se cambia de pestaña para no sacar
        al usuario de donde está mirando.

        Va por _construir_catalogo, el mismo camino que usa la pestaña al
        abrirse, para que no haya dos formas de llenarla y se puedan
        desincronizar.
        """
        # El concatenado se rehace siempre que el análisis acaba de correr:
        # «Procesar catálogos» regenera los new_2_*.csv, así que el derivado
        # tiene que volver a armarse. forzar=True porque es el único punto
        # donde se garantiza que lo demás ya está en disco.
        self._concatenar_eventquery(forzar=True)
        if self.cuaderno_catalogos is None:
            # La ventana de catálogos todavía no se abrió. No se construyen
            # widgets Tk desde el hilo de trabajo: se invalidan y se arman al
            # abrirla (ver _ver_catalogos).
            for panel in self.catalogos.values():
                panel["construido"] = False
                panel["firma"] = None
            return
        for clave in ("seisan", "eventquery", "seiscomp"):
            self._construir_catalogo(clave, seleccionar=False)

    def _procesar_fuente(self, fuente):
        """
        Genera el JSON/panel de una fuente. Síncrono, sin envoltorio de tarea.

        Devuelve True si dejó el JSON en disco. Lo comparten el botón maestro
        («Procesar catálogos»), la re-exportación de SeisComp y la generación
        perezosa al abrir una pestaña, para que no haya dos caminos que puedan
        desincronizarse.
        """
        # Cada fuente escribe su propio eventos_<vista>.json: los no publicados
        # comparten parseo con su fuente, pero no archivo de salida, así que
        # procesarlos no pisa el panel de la fuente principal.
        vista_clave = FUENTE_A_VISTA.get(fuente)
        if vista_clave not in VISTAS_POR_CLAVE:
            return False
        if fuente == "seisan":
            self._popen([_script("generajson.py"),
                         os.path.join("datos", "salida_collect.csv"),
                         "seisan"])
        elif fuente == "eventquery":
            self._concatenar_eventquery()
            self._asegurar_parametros_seiscomp()
            self._atribuir_para_eventquery()
            self._popen([_script("generajson.py"),
                         os.path.join("datos", "todos_eventquery.csv"),
                         "eventquery"])
            # No se borra: es lo que lee la pestaña de catálogo de eventquery, y
            # regenerarlo cuesta una pasada más. Es un derivado de los new_2_*,
            # así que no puede quedar desactualizado sin que también lo estén
            # ellos.
        elif fuente == "seiscomp":
            par = self._par_seiscomp_para_catalogo()
            if par is None:
                self._log("No hay una exportación de SeisComp que cubra "
                          "este catálogo.")
                return False
            self._log("Usando %s" % os.path.basename(par["eventos"]))
            # Idempotente: si el análisis ya dejó seiscomp_parametros.csv al
            # día, no vuelve a convertir.
            self._asegurar_parametros_seiscomp()
            parametros = os.path.join("datos", "seiscomp_parametros.csv")
            if not (os.path.isfile(parametros)
                    and os.path.getsize(parametros) > 0):
                self._log("La conversión falló; no se genera el JSON.")
                return False
            self._popen([_script("generajson.py"), parametros, "seiscomp"])
        elif fuente in ("nopub", "nopub_seiscomp"):
            # Los dos "no publicados" salen del mismo compara.py, cada uno con
            # su prefijo, así que no se pisan entre ellos.
            if fuente == "nopub_seiscomp":
                archivo = os.path.join(
                    "datos", "no_pub_desde_2_5_seiscomp_estricto.csv")
                origen = "seiscomp"
            else:
                archivo = os.path.join("datos",
                                       "no_pub_desde_2_5_estricto.csv")
                origen = "seisan"
            if not os.path.isfile(archivo):
                self._log("No se encontró %s (procese los catálogos primero)."
                          % archivo)
                return False
            # --salida evita que el JSON de los no publicados pise el de la
            # fuente principal: comparten parseo, no archivo de salida.
            self._popen([_script("generajson.py"), archivo, origen,
                         "--salida=%s" % vista_clave])
        elif fuente in ("noact", "noact_seiscomp"):
            # Los «no actualizados» salen del atribucion_<fuente>.csv que dejó
            # compara.py: generajson arma el par local + publicado.
            origen = "seiscomp" if fuente == "noact_seiscomp" else "seisan"
            archivo = os.path.join("datos", "atribucion_%s.csv" % origen)
            if not os.path.isfile(archivo):
                self._log("No hay %s; no se genera el panel de no actualizados."
                          % archivo)
                return False
            self._popen([_script("generajson.py"), "--pares=%s" % origen,
                         "--salida=%s" % vista_clave])
        else:
            return False
        json_path = os.path.join("datos", "eventos_%s.json" % vista_clave)
        if os.path.isfile(json_path):
            self._log("JSON generado: %s" % json_path)
            return True
        self._log("No se generó %s." % json_path)
        return False

    def _accion_fuente(self, fuente):
        """Genera una fuente puntual en segundo plano (generación perezosa)."""
        vista_clave = FUENTE_A_VISTA.get(fuente)
        if vista_clave not in VISTAS_POR_CLAVE:
            return

        def tarea():
            if fuente == "eventquery":
                # La concatenación no tiene script que marque la etapa, así que
                # se fija a mano (es la primera de FUENTE_PLAN).
                self._fijar_etapa(0)
            self._procesar_fuente(fuente)

        def al_terminar():
            self._abrir_panel_en_tab(vista_clave)
            self._actualizar_gate()

        self._iniciar(tarea, on_fin=al_terminar,
                      plan=FUENTE_PLAN.get(fuente))

    def _firma_catalogo(self, clave):
        """
        Qué archivos definen el contenido de esa pestaña de catálogo.

        Devuelve una tupla de (ruta, mtime, tamaño) con la que se compara la
        firma guardada para saber si hay que volver a construir, o None si no
        hay datos con que construirla.

        Para eventquery se usan los new_2_*.csv y no el todos_eventquery.csv
        derivado, por dos razones: el derivado puede no existir todavía (lo
        arma _concatenar_eventquery al construir, así que antes de construir no
        hay nada que mirar), y si entra un new_2 nuevo hay que rehacer el
        catálogo aunque el derivado todavía sea el de la corrida anterior.
        """
        if clave == "seiscomp":
            par = self._par_seiscomp_para_catalogo()
            if par is None:
                return None
            rutas = (par["eventos"], par["fases"])
        elif clave == "eventquery":
            rutas = self._partes_eventquery()
            if not rutas:
                return None
        else:
            ruta = os.path.join("datos", "salida_collect.csv")
            if not os.path.isfile(ruta):
                return None
            rutas = [ruta]
        firma = []
        for ruta in rutas:
            if not os.path.isfile(ruta):
                return None
            try:
                st = os.stat(ruta)
            except OSError:
                return None
            firma.append((ruta, st.st_mtime, st.st_size))
        return tuple(firma)

    def _construir_catalogo(self, clave, seleccionar=False):
        """
        Construye (o reusa) el catálogo de una pestaña.

        La firma evita rehacer la tabla en cada visita, que con catálogos grandes
        se nota; y si cambió algún archivo de entrada se rehace sola, que es lo
        que pasa después de un análisis nuevo.
        """
        panel = self.catalogos.get(clave)
        if panel is None:
            return
        firma = self._firma_catalogo(clave)
        if firma is None:
            # No hay datos: se deja el placeholder, que explica qué hacer.
            return
        if (panel["construido"] and panel.get("firma") == firma
                and panel["frame"].winfo_children()):
            return
        if clave == "seiscomp":
            par = self._par_seiscomp_para_catalogo()
            if par is None:
                return
            self._abrir_revisor(par, seleccionar=seleccionar)
        else:
            self._abrir_catalogo(ARCHIVO_CATALOGO[clave], clave,
                                 seleccionar=seleccionar)
        if panel["frame"].winfo_children():
            panel["construido"] = True
            panel["firma"] = firma
        else:
            # _abrir_revisor borra los hijos antes de construir y no los repone
            # si algo falla, así que la pestaña quedaría en blanco. El mensaje
            # va siempre, haya estado construida antes o no.
            panel["construido"] = False
            ttk.Label(panel["frame"], justify=CENTER,
                      text=("No se pudo abrir el catálogo de %s."
                            % panel["titulo"])).pack(expand=YES)

    def _abrir_catalogo(self, nombre_archivo, etiqueta, seleccionar=True):
        """Muestra el catálogo crudo de una fuente en su pestaña."""
        rs = self._importar_revisor()
        if rs is None:
            return
        ruta = os.path.join("datos", nombre_archivo)
        marco = (self.seisan_frame if etiqueta == "seisan"
                 else self.eventquery_frame)
        if etiqueta == "eventquery" and (not os.path.isfile(ruta)
                                         or os.path.getsize(ruta) == 0):
            # El catálogo publicado es la unión de los new_2_*.csv, que arma
            # _concatenar_eventquery. Sin esto, consultar el catálogo por aquí
            # exigiría antes haber corrido «Datos de eventquery», que es un paso
            # extra que no tiene nada que ver con consultar: se arma aquí y se
            # abre en un solo paso, como el de Seisan.
            self._concatenar_eventquery()
        if not os.path.isfile(ruta):
            self._log("No se encontró %s. Pulse «Procesar catálogos» primero."
                      % ruta)
            return
        for w in list(marco.winfo_children()):
            w.destroy()
        atribuciones = (self._mapa_analistas_eventquery()
                        if etiqueta == "eventquery" else None)
        try:
            ok = rs.abrir_catalogo(marco, ruta, etiqueta, log=self._log,
                                    cwd=self.cwd, atribuciones=atribuciones)
        except Exception as e:
            self._log("[error] catálogo %s: %s" % (etiqueta, e))
            return
        if not ok:
            self._log("No se pudo abrir el catálogo de %s." % etiqueta)
            return
        if seleccionar and self.cuaderno_catalogos is not None:
            self.cuaderno_catalogos.select(marco)
        self._ajustar_catalogos()
        self._log("Catálogo abierto: %s" % os.path.basename(ruta))

    def _al_cambiar_pestana(self, _evento=None):
        """
        Construye (o reusa) el panel de la vista al abrir su pestaña.

        Hace falta porque el botón de una fuente ya procesada queda apagado, así
        que la pestaña es la única vía para volver a ver el panel (por ejemplo,
        al reabrir la aplicación sobre una carpeta ya analizada). Si el CSV de
        entrada existe pero el JSON no (o quedó viejo), se genera aquí en
        segundo plano.
        """
        self._marcar_pestana_activa()
        actual = self.cuaderno.select()
        for clave, panel in self.paneles.items():
            if str(panel["frame"]) != actual:
                continue
            self._abrir_panel_si_puede(clave)
            break

    def _abrir_panel_si_puede(self, clave):
        """
        Abre el panel de una vista, generándolo si hace falta.

        Si el JSON está al día, se muestra; si el CSV de entrada existe pero el
        JSON falta o quedó viejo, se procesa la fuente en segundo plano y el
        panel se abre al terminar. Si no hay entrada, se deja el placeholder.
        """
        if self._analisis_obsoleto():
            # Los catálogos son más nuevos que el análisis: no se muestra un
            # panel viejo como si fuera actual.
            self._placeholder_panel(
                clave, "Los catálogos cambiaron desde el último análisis.\n\n"
                       "Pulse «Procesar catálogos» para regenerar el panel.")
            return
        if self._vista_procesada(clave):
            self._abrir_panel_en_tab(clave)
            return
        vista = VISTAS_POR_CLAVE.get(clave)
        if vista is None or not os.path.isfile(vista["entrada"]):
            return
        # Sin esto, abrir la pestaña mientras corre otra tarea arrancaría un
        # segundo procesamiento que _iniciar descartaría sin dejar rastro.
        if self.ocupado:
            return
        self._placeholder_panel(
            clave, "Procesando esta fuente…\n\nSe genera el panel a partir de "
                   "%s." % os.path.basename(vista["entrada"]))
        self._accion_fuente(VISTA_A_FUENTE[clave])

    def _abrir_panel_en_tab(self, clave):
        """Construye (una sola vez) el panel de la vista y la selecciona."""
        vista = VISTAS_POR_CLAVE.get(clave)
        panel = self.paneles.get(clave)
        if vista is None or panel is None:
            return
        # Sin CSV de entrada vigente no se abre el panel, aunque el JSON exista:
        # podría ser el de una corrida anterior cuyo CSV se borró por quedar
        # vacío (ver _procesar_fuente y _borrar en compara.py). _vista_procesada
        # exige que el JSON sea igual o más nuevo que su entrada.
        if not self._vista_procesada(clave):
            self._log("No hay datos vigentes de %s; no se abre el panel."
                      % vista["etiqueta"])
            self._placeholder_panel(
                clave, "No hay datos de %s para mostrar.\n\nPulse «Procesar "
                       "catálogos» para generarlos." % vista["etiqueta"])
            return
        archivo = os.path.join("datos", "eventos_%s.json" % clave)
        mtime = os.path.getmtime(archivo)
        # Un panel ya construido con el mismo JSON se reusa tal cual: cambiar
        # de pestaña no debe rehacer perfiles ni redibujar. El frame tiene que
        # seguir teniendo algo dentro: si algún camino lo dejó vacío, el caché
        # lo daba por bueno y la pestaña quedaba muda, sin forma de recuperarla
        # con el botón de esa fuente ya deshabilitado por «ya procesada».
        if (panel["construido"] and panel.get("mtime") == mtime
                and panel["frame"].winfo_children()):
            self.cuaderno.select(panel["frame"])
            return
        for w in list(panel["frame"].winfo_children()):
            w.destroy()
        panel["construido"] = False
        try:
            import plotear
            ok = plotear.abrir_panel(panel["frame"], archivo, vista["fuente"],
                                     etiqueta_fuente=vista["etiqueta"],
                                     vista=clave)
        except Exception as e:
            ok = False
            self._log("[error] panel %s: %s" % (clave, e))
        if not ok:
            self._log("No se pudo abrir el panel de %s "
                      "(¿backend interactivo?)." % vista["etiqueta"])
            ttk.Label(panel["frame"], justify=CENTER,
                      text="No se pudo dibujar el panel.").pack(expand=YES)
            return
        panel["construido"] = True
        panel["mtime"] = mtime
        self.cuaderno.select(panel["frame"])
        # El panel es lo más ancho de la app: sin esto la figura y parte de la
        # tabla quedan fuera de la ventana.
        self._ajustar_ventana()
        self._log("Panel abierto (%s)." % clave)

    def _abrir_no_actualizados(self, fuente, contenedor):
        """
        Muestra el listado de eventos no actualizados de una fuente.

        No calcula nada: los datos salen de datos/atribucion_<fuente>.csv, que
        escribe la corrida del análisis, y se llenan en 'contenedor' (el marco de
        una pestaña de la ventana lateral «No actualizados»).

        Distingue los tres estados posibles, porque un mismo "no se puede
        mostrar" significa cosas distintas: que el análisis nunca corrió, que
        corrió sin encontrar cruces, o que hay datos.
        """
        if contenedor is None:
            return
        etiqueta = {"seisan": "Seisan", "seiscomp": "SeisComp"}[fuente]
        csv_noact = os.path.join("datos", "atribucion_%s.csv" % fuente)
        # El informe .txt se escribe siempre que corre la comparación (aunque
        # quede sin filas), así que dice si el análisis llegó a hacer el cruce.
        informe = os.path.join(
            "informes", "no_act_%sestricto.txt"
            % ("" if fuente == "seisan" else "seiscomp_"))

        for w in list(contenedor.winfo_children()):
            w.destroy()
        if not os.path.isfile(csv_noact):
            texto = ("Todavía no hay nada para mostrar.\n\nPulse "
                     "«Procesar catálogos» para generarlo."
                     if not os.path.isfile(informe) else
                     "La comparación se ejecutó, pero no encontró ningún "
                     "cruce entre %s y lo publicado.\n\nNo hay eventos "
                     "no actualizados." % etiqueta)
            ttk.Label(contenedor, justify=CENTER, text=texto).pack(
                expand=YES)
            return

        rs = self._importar_revisor()
        if rs is None:
            return
        try:
            ok = rs.abrir_no_actualizados(contenedor, fuente,
                                          log=self._log, cwd=self.cwd)
        except Exception as e:
            ok = False
            self._log("[error] no actualizados %s: %s" % (fuente, e))
        if not ok:
            ttk.Label(contenedor, justify=CENTER,
                      text="No se pudo leer el listado de %s." % etiqueta
                      ).pack(expand=YES)

    def _ver_no_actualizados(self):
        """
        Ventana con el listado de no actualizados, una pestaña por fuente.

        SeisComp va primero y por defecto; Seisan después. Cada pestaña se
        arma solo al seleccionarla y se reutiliza mientras su firma de archivos
        no cambie. Al cerrar se oculta, no se destruye.
        """
        def _firma(clave):
            rs = self._importar_revisor()
            if rs is None:
                return None
            return rs.firma_no_actualizados(self.cwd, clave)

        def _construir(clave):
            panel = self.no_actualizados[clave]
            firma = _firma(clave)
            if panel["construido"] and panel["firma"] == firma:
                return
            panel["construido"] = False
            self._abrir_no_actualizados(clave, contenedor=panel["frame"])
            panel["firma"] = firma
            # Si el builder no dejó contenido (por ejemplo, no pudo importar
            # el revisor), la próxima visita vuelve a intentarlo.
            panel["construido"] = bool(panel["frame"].winfo_children())
            self._ajustar_popup(self.marco_no_actualizados, (1000, 560))

        def _al_cambiar(_evento=None):
            actual = self.cuaderno_no_actualizados.select()
            for clave, panel in self.no_actualizados.items():
                if str(panel["frame"]) == actual:
                    _construir(clave)
                    break

        if self.marco_no_actualizados is None:
            top = ttk.Toplevel(title="No actualizados", master=self.raiz)
            top.geometry("1000x560")
            top.minsize(820, 480)
            cuaderno = ttk.Notebook(top)
            cuaderno.pack(fill=BOTH, expand=YES)
            self.marco_no_actualizados = top
            self.cuaderno_no_actualizados = cuaderno
            for clave, _titulo in (("seiscomp", "SeisComp"),
                                   ("seisan", "Seisan")):
                marco = ttk.Frame(cuaderno)
                cuaderno.add(marco,
                             text=self.no_actualizados[clave]["titulo"])
                ttk.Label(
                    marco, justify=CENTER,
                    text="Seleccione esta pestaña para ver el listado."
                ).pack(expand=YES)
                self.no_actualizados[clave]["frame"] = marco
            cuaderno.bind("<<NotebookTabChanged>>", _al_cambiar)
            top.protocol("WM_DELETE_WINDOW", top.withdraw)
            _construir("seiscomp")
        else:
            top = self.marco_no_actualizados
            top.deiconify()
            top.lift()
            actual = self.cuaderno_no_actualizados.select()
            for clave, panel in self.no_actualizados.items():
                if str(panel["frame"]) == actual:
                    _construir(clave)
                    break
            self._ajustar_popup(top, (1000, 560))

    def _ver_catalogos(self):
        """
        Abre (o trae al frente) la ventana con los catálogos crudos.

        Una pestaña por fuente (SeisComp, Seisan, eventquery; SeisComp por
        defecto). Cada pestaña se arma solo al seleccionarla, reutilizando
        _construir_catalogo con su caché por firma. Al cerrar se oculta
        (withdraw) en vez de destruirse, para conservar los frames y que
        _poblar_catalogos pueda rehacerlos tras un análisis nuevo.
        """
        if self.marco_catalogos is None:
            top = ttk.Toplevel(title="Catálogos", master=self.raiz)
            top.geometry("1300x650")
            top.minsize(900, 520)
            self.marco_catalogos = top
            cuaderno = ttk.Notebook(top)
            cuaderno.pack(fill=BOTH, expand=YES)
            self.cuaderno_catalogos = cuaderno
            for clave, titulo in (("seiscomp", "SeisComp"),
                                  ("seisan", "Seisan"),
                                  ("eventquery", "eventquery")):
                marco = ttk.Frame(cuaderno)
                cuaderno.add(marco, text=titulo)
                etiqueta = ttk.Label(
                    marco, justify=CENTER,
                    text=("No hay datos de %s para mostrar.\n\n"
                          "Pulse «Procesar catálogos» para generarlos."
                          % titulo))
                etiqueta.pack(expand=YES)
                self.catalogos[clave]["frame"] = marco
                self.catalogos[clave]["construido"] = False
            self.seiscomp_frame = self.catalogos["seiscomp"]["frame"]
            self.seisan_frame = self.catalogos["seisan"]["frame"]
            self.eventquery_frame = self.catalogos["eventquery"]["frame"]

            def _al_cambiar(_evento=None):
                actual = cuaderno.select()
                for clave, panel in self.catalogos.items():
                    if str(panel["frame"]) == actual:
                        self._construir_catalogo(clave)
                        break

            cuaderno.bind("<<NotebookTabChanged>>", _al_cambiar)
            top.protocol("WM_DELETE_WINDOW", top.withdraw)
            self._construir_catalogo("seiscomp")
        else:
            self.marco_catalogos.deiconify()
            self.marco_catalogos.lift()
            # Los datos pueden haber cambiado desde la última visita; la caché
            # por firma decide si hay que rehacer la pestaña activa.
            actual = self.cuaderno_catalogos.select()
            for clave, panel in self.catalogos.items():
                if panel["frame"] is not None and str(panel["frame"]) == actual:
                    self._construir_catalogo(clave)
                    break
        self._ajustar_catalogos()

    # ------------------------------------------------ comparar agencias
    def _periodo_iso(self, valor14):
        """'AAAAMMDDHHMMSS' -> 'AAAA-MM-DDTHH:MM:SS' (o el valor tal cual)."""
        try:
            return datetime.datetime.strptime(
                str(valor14), "%Y%m%d%H%M%S").strftime("%Y-%m-%dT%H:%M:%S")
        except (TypeError, ValueError):
            return str(valor14)

    def _ruta_estado_agencias(self):
        return os.path.join("datos", "agencias", "estado.json")

    def _leer_estado_agencias(self):
        try:
            with open(self._ruta_estado_agencias()) as f:
                return json.load(f)
        except (OSError, ValueError):
            return {}

    def _escribir_estado_agencias(self, minmag, agencias, modo, periodo_efectivo,
                                  referencia="eventquery", desde=None,
                                  hasta=None):
        """Guarda con qué modo, período, magnitud, agencias y referencia se comparó."""
        estado = {
            "consulta": {
                "modo": modo,
                "periodo": list(periodo_efectivo),
                "desde": desde,
                "hasta": hasta,
                "minmag": minmag,
                "agencias": list(agencias),
                "referencia": referencia,
                "timestamp": datetime.datetime.utcnow().strftime(
                    "%Y-%m-%d %H:%M:%S"),
            },
            "comparacion": {"minmag": minmag, "agencias": list(agencias),
                            "referencia": referencia,
                            "version_asociacion":
                                agencias_mod.VERSION_ASOCIACION},
        }
        ruta = self._ruta_estado_agencias()
        try:
            os.makedirs(os.path.dirname(ruta), exist_ok=True)
            with open(ruta, "w") as f:
                json.dump(estado, f, indent=2)
        except OSError as e:
            self._log("[error] no se pudo guardar el estado de agencias: %s" % e)

    def _dentro_de_ttl(self, consulta):
        """True si la consulta «hasta ahora» todavía está dentro del TTL."""
        ts = consulta.get("timestamp")
        if not ts:
            return False
        try:
            t = datetime.datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
        except (TypeError, ValueError):
            return False
        edad = (datetime.datetime.utcnow() - t).total_seconds()
        return edad < TTL_AGENCIAS_MIN * 60

    def _mas_nuevo_que(self, destino, entradas):
        """True si 'destino' existe y es más nuevo que todas las 'entradas'
        (que además tienen que existir)."""
        if not os.path.isfile(destino):
            return False
        try:
            marca = os.path.getmtime(destino)
        except OSError:
            return False
        for e in entradas:
            if not os.path.isfile(e) or os.path.getmtime(e) > marca:
                return False
        return True

    def _consulta_agencias_al_dia(self, minmag, agencias, modo, periodo_efectivo):
        """True si los CSV de agencia ya corresponden al modo, período y mag."""
        # El período efectivo lo pasa el llamador (ya resuelto con _periodo(),
        # que infiere del nombre de los archivos si no vino estado.json). No se
        # usa self.periodo: en el arranque en modo catálogo explícito está vacío.
        inicio, fin = periodo_efectivo
        consulta = (self._leer_estado_agencias().get("consulta") or {})
        if consulta.get("modo") != modo:
            return False
        if consulta.get("minmag") != minmag:
            return False
        if modo == "ventana":
            if (consulta.get("periodo") or [None, None]) != [inicio, fin]:
                return False
        elif not self._dentro_de_ttl(consulta):
            return False
        for ag in agencias:
            csv = os.path.join("datos", "agencias",
                               "consultaapi_%s.csv" % AGENCIAS_EXTERNAS[ag])
            if not os.path.isfile(csv):
                return False
        return True

    def _comparacion_al_dia(self, minmag, agencias, modo, referencia,
                            desde=None, hasta=None):
        """True si la comparación ya está hecha y no cambió ningún insumo."""
        # _periodo() (no self.periodo): infiere inicio/fin del nombre de los
        # archivos cuando se arrancó en modo catálogo explícito (sin
        # estado.json), que es justo el caso en que self.periodo está vacío y
        # la comparación se repetía siempre.
        inicio, fin = self._periodo()
        estado = self._leer_estado_agencias()
        comp = (estado.get("comparacion") or {})
        consulta = (estado.get("consulta") or {})
        if comp.get("version_asociacion") != agencias_mod.VERSION_ASOCIACION:
            return False
        if comp.get("minmag") != minmag:
            return False
        if sorted(comp.get("agencias") or []) != sorted(agencias):
            return False
        if comp.get("referencia") != referencia:
            return False
        if consulta.get("modo") != modo:
            return False
        if modo == "ventana":
            if (consulta.get("periodo") or [None, None]) != [inicio, fin]:
                return False
        elif desde is None:
            if not self._dentro_de_ttl(consulta):
                return False
        else:
            # Ventana elegida (Desde/Hasta): si cambia el inicio, rehacer. Si
            # el inicio coincide y el «Hasta» difiere, se admite el atajo del
            # TTL (evita re-bajar por segundos de diferencia cuando «hasta» es
            # «ahora»).
            if consulta.get("desde") != desde:
                return False
            if consulta.get("hasta") != hasta and not self._dentro_de_ttl(
                    consulta):
                return False
        entradas = [os.path.join("datos", "eventos_%s.json" % referencia)]
        entradas += [os.path.join("datos", "eventos_agencia_%s.json" % ag)
                     for ag in agencias]
        return self._mas_nuevo_que(
            os.path.join("datos", "comparacion_agencias.json"), entradas)

    @staticmethod
    def _fecha_desde14(valor14):
        """'AAAAMMDDHHMMSS' -> 'AAAA-MM-DD HH:MM:SS' (o '' si no es válido)."""
        try:
            return datetime.datetime.strptime(
                str(valor14), "%Y%m%d%H%M%S").strftime("%Y-%m-%d %H:%M:%S")
        except (TypeError, ValueError):
            return ""

    @staticmethod
    def _fecha_utc(texto):
        """Parsea 'AAAA-MM-DD HH:MM:SS[.ffffff]' (UTC) a datetime, o None."""
        if texto is None:
            return None
        limpio = str(texto).strip().replace("T", " ").replace("Z", "")
        for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.datetime.strptime(limpio, fmt)
            except ValueError:
                continue
        return None

    def _cobertura_agencias(self, agencias):
        """
        Ventana solicitada (común) y cobertura real por agencia de la última
        extracción de agencias.

        La solicitada sale del estado (período y magnitud guardados). La real,
        de min/max de 'Fecha_Hora' en datos/agencias/consultaapi_<AG>.csv: es
        el primer/último evento EFECTIVAMENTE reportado (no la cobertura total
        del catálogo). El rezago compara el último evento con el fin solicitado.

        Devuelve:
            {"solicitada": {"desde", "hasta", "minmag"},
             "agencias": [{"agencia", "eventos", "desde", "hasta", "rezago"}]}
        """
        consulta = (self._leer_estado_agencias().get("consulta") or {})
        periodo = consulta.get("periodo") or [None, None]
        sol_desde = self._fecha_desde14(periodo[0]) if periodo[0] else ""
        sol_hasta = self._fecha_desde14(periodo[1]) if periodo[1] else ""
        sol_hasta_dt = self._fecha_utc(sol_hasta)
        filas = []
        for ag in agencias:
            ruta = os.path.join("datos", "agencias",
                                "consultaapi_%s.csv" % AGENCIAS_EXTERNAS[ag])
            tiempos = []
            if os.path.isfile(ruta):
                try:
                    with open(ruta, encoding="utf-8-sig", newline="") as f:
                        for fila in csv.DictReader(f):
                            t = self._fecha_utc(fila.get("Fecha_Hora"))
                            if t is not None:
                                tiempos.append(t)
                except OSError:
                    pass
            desde = min(tiempos) if tiempos else None
            hasta = max(tiempos) if tiempos else None
            rezago = ""
            if sol_hasta_dt is not None and hasta is not None:
                dias = (sol_hasta_dt - hasta).total_seconds() / 86400.0
                if dias > 0.05:
                    rezago = "%.1f d" % dias
            filas.append({
                "agencia": ag,
                "eventos": len(tiempos),
                "desde": desde.strftime("%Y-%m-%d %H:%M:%S") if desde else "",
                "hasta": hasta.strftime("%Y-%m-%d %H:%M:%S") if hasta else "",
                "rezago": rezago,
            })
        return {
            "solicitada": {"desde": sol_desde, "hasta": sol_hasta,
                           "minmag": consulta.get("minmag")},
            "agencias": filas,
        }

    def _pedir_parametros_agencias(self):
        """Diálogo: magnitud, agencias y opción de reconsultar (últimos valores)."""
        comp = (self._leer_estado_agencias().get("comparacion") or {})
        mag_prev = comp.get("minmag")
        ags_prev = comp.get("agencias") or list(AGENCIAS_EXTERNAS)

        top = ttk.Toplevel(title="Comparar agencias", master=self.raiz)
        marco = ttk.Frame(top, padding=12)
        marco.pack(fill=BOTH, expand=YES)
        ttk.Label(marco, bootstyle="primary",
                  text="Se compara contra catálogo de eventos publicados "
                       "extraído (eventquery).",
                  font=("", 10, "bold"), wraplength=420, justify=LEFT
                  ).grid(row=0, column=0, columnspan=2, sticky=W, pady=(0, 8))

        ttk.Label(marco, text="Magnitud mínima:").grid(
            row=1, column=0, sticky=W, pady=(0, 6))
        ent_mag = ttk.Entry(marco, width=10)
        ent_mag.insert(0, "%g" % mag_prev if mag_prev is not None else "4.0")
        ent_mag.grid(row=1, column=1, sticky=W, pady=(0, 6))

        ttk.Label(marco, text="Agencias:").grid(row=2, column=0, sticky=NW)
        marco_ag = ttk.Frame(marco)
        marco_ag.grid(row=2, column=1, sticky=W)
        vars_ag = {}
        for ag in AGENCIAS_EXTERNAS:
            var = BooleanVar(value=(ag in ags_prev))
            vars_ag[ag] = var
            ttk.Checkbutton(marco_ag, text=ag, variable=var,
                            bootstyle="round-toggle").pack(anchor=W)

        var_ahora = BooleanVar(value=False)
        var_refrescar = BooleanVar(value=False)
        var_eventquery = BooleanVar(value=False)

        # Ventana «Desde/Hasta» (UTC): por defecto, el inicio del análisis (la
        # extracción anterior) hasta el instante en que se abre este diálogo.
        # Ambos extremos son editables.
        ini14 = self._periodo()[0]
        inicio_analisis = self._fecha_desde14(ini14) if ini14 else ""
        consulta_prev = (self._leer_estado_agencias().get("consulta") or {})
        desde_prev14 = consulta_prev.get("desde")
        desde_default = (self._fecha_desde14(desde_prev14)
                         if desde_prev14 else inicio_analisis)
        if not desde_default:
            desde_default = datetime.datetime.utcnow().strftime(
                "%Y-%m-%d 00:00:00")
        hasta_default = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        def _fecha_hora_campo(fila, etiqueta, valor_iso):
            """
            Fila con un selector de fecha (calendario DateEntry) y un campo de
            hora HH:MM:SS. Devuelve (dateentry, entry_hora).
            """
            ttk.Label(marco, text=etiqueta).grid(row=fila, column=0, sticky=W,
                                                 pady=(6, 0))
            cont = ttk.Frame(marco)
            cont.grid(row=fila, column=1, sticky=W, pady=(6, 0))
            partes = (valor_iso or "").split(" ")
            fecha_txt = partes[0] if partes and partes[0] else ""
            hora_txt = partes[1] if len(partes) > 1 and partes[1] else "00:00:00"
            try:
                startdate = datetime.datetime.strptime(fecha_txt, "%Y-%m-%d")
            except ValueError:
                startdate = datetime.datetime.utcnow()
                fecha_txt = startdate.strftime("%Y-%m-%d")
            de = DateEntry(cont, dateformat="%Y-%m-%d", startdate=startdate,
                           width=10, bootstyle="primary")
            de.pack(side=LEFT)
            de.entry.delete(0, END)
            de.entry.insert(0, fecha_txt)
            ent_hora = ttk.Entry(cont, width=9)
            ent_hora.insert(0, hora_txt)
            ent_hora.pack(side=LEFT, padx=(6, 0))
            return de, ent_hora

        de_desde, ent_desde = _fecha_hora_campo(5, "Desde (UTC):",
                                                desde_default)
        de_hasta, ent_hasta = _fecha_hora_campo(6, "Hasta (UTC):",
                                                hasta_default)

        def _poner_ahora(_evento=None):
            ahora = datetime.datetime.utcnow()
            de_hasta.entry.delete(0, END)
            de_hasta.entry.insert(0, ahora.strftime("%Y-%m-%d"))
            ent_hasta.delete(0, END)
            ent_hasta.insert(0, ahora.strftime("%H:%M:%S"))

        btn_ahora = ttk.Button(
            de_hasta.master, text="Ahora", bootstyle="secondary-outline",
            command=_poner_ahora, width=6)
        btn_ahora.pack(side=LEFT, padx=(6, 0))

        def _leer_fecha_hora(de, ent_hora):
            """datetime de un campo (calendario + hora), o None si es inválido."""
            fecha = de.entry.get().strip()
            hora = ent_hora.get().strip() or "00:00:00"
            fecha_dt = None
            if _dateparser is not None:
                try:
                    # dayfirst=True: convención chilena (DD/MM/AAAA); el ISO
                    # AAAA-MM-DD se interpreta igual.
                    fecha_dt = _dateparser.parse(fecha, dayfirst=True)
                except (ValueError, OverflowError):
                    fecha_dt = None
            if fecha_dt is None:
                try:
                    fecha_dt = datetime.datetime.strptime(fecha, "%Y-%m-%d")
                except ValueError:
                    return None
            try:
                hora_t = datetime.datetime.strptime(hora, "%H:%M:%S").time()
            except ValueError:
                return None
            return datetime.datetime.combine(fecha_dt.date(), hora_t)

        def _al_cambiar_ahora():
            # «Desde/Hasta» implica reconsultar agencias y actualizar el
            # eventquery; se marcan solas, pero el usuario puede destildarlas.
            activo = bool(var_ahora.get())
            if activo:
                var_refrescar.set(True)
                var_eventquery.set(True)
            estado_ctrl = "normal" if activo else "disabled"
            # Ojo: en DateEntry de ttkbootstrap hay que usar .configure()
            # (config() va al configure base y con "state" lanza TclError, que
            # dejaba el campo activo). Los ttk.Entry/Button aceptan cualquiera.
            for w in (de_desde, ent_desde, de_hasta, ent_hasta, btn_ahora):
                try:
                    w.configure(state=estado_ctrl)
                except TclError:
                    pass
            # Blindaje por si algún tema no propaga el estado al subwidget.
            for de in (de_desde, de_hasta):
                try:
                    de.entry.configure(state=estado_ctrl)
                    de.button.configure(state=estado_ctrl)
                except TclError:
                    pass

        ttk.Checkbutton(marco, text="Desde/Hasta",
                        variable=var_ahora, command=_al_cambiar_ahora,
                        bootstyle="round-toggle").grid(
            row=3, column=0, columnspan=2, sticky=W, pady=(8, 0))
        ttk.Label(marco, font=("", 9), wraplength=430, justify=LEFT,
                  text="Si no se marca, se usa la ventana del análisis. Si se "
                       "marca, se consulta el rango Desde/Hasta elegido (UTC). "
                       "Los datos muy recientes pueden ser preliminares; GFZ "
                       "llega con ~1 día."
                  ).grid(row=4, column=0, columnspan=2, sticky=W, pady=(4, 0))

        ttk.Checkbutton(marco, text="Volver a consultar las agencias",
                        variable=var_refrescar,
                        bootstyle="round-toggle").grid(
            row=7, column=0, columnspan=2, sticky=W, pady=(8, 0))
        ttk.Checkbutton(
            marco, text="Actualizar el catálogo publicado (eventquery)",
            variable=var_eventquery, bootstyle="round-toggle").grid(
            row=8, column=0, columnspan=2, sticky=W, pady=(4, 0))
        ttk.Label(marco, font=("", 9), wraplength=430, justify=LEFT,
                  text="Actualizar eventquery requiere la contraseña del "
                       "servidor y re-baja el catálogo hasta el «Hasta» "
                       "elegido. La referencia fresca es solo para esta "
                       "comparación; el resto del análisis sigue en la ventana "
                       "cargada."
                  ).grid(row=9, column=0, columnspan=2, sticky=W, pady=(2, 0))

        lbl_error = ttk.Label(marco, bootstyle="danger", text="",
                              wraplength=430, justify=LEFT)
        lbl_error.grid(row=10, column=0, columnspan=2, sticky=W, pady=(4, 0))

        resultado = {"valor": None}

        def aceptar(_evento=None):
            try:
                minmag = float(ent_mag.get().strip())
            except ValueError:
                lbl_error.config(text="La magnitud mínima no es un número.")
                return
            agencias = [ag for ag, v in vars_ag.items() if v.get()]
            if not agencias:
                lbl_error.config(text="Elige al menos una agencia.")
                return
            modo = "ahora" if var_ahora.get() else "ventana"
            desde14 = None
            hasta14 = None
            if modo == "ahora":
                dt_desde = _leer_fecha_hora(de_desde, ent_desde)
                dt_hasta = _leer_fecha_hora(de_hasta, ent_hasta)
                if dt_desde is None or dt_hasta is None:
                    lbl_error.config(
                        text="Fecha/hora inválida. Usa AAAA-MM-DD y HH:MM:SS.")
                    return
                if dt_desde >= dt_hasta:
                    lbl_error.config(
                        text="«Desde» debe ser anterior a «Hasta».")
                    return
                desde14 = dt_desde.strftime("%Y%m%d%H%M%S")
                hasta14 = dt_hasta.strftime("%Y%m%d%H%M%S")
            lbl_error.config(text="")
            resultado["valor"] = (minmag, agencias, bool(var_refrescar.get()),
                                  modo, bool(var_eventquery.get()), desde14,
                                  hasta14)
            top.destroy()

        def cancelar(_evento=None):
            top.destroy()

        botones = ttk.Frame(marco)
        botones.grid(row=11, column=0, columnspan=2, sticky=E, pady=(10, 0))
        ttk.Button(botones, text="Comparar", command=aceptar,
                   bootstyle="primary").pack(side=RIGHT)
        ttk.Button(botones, text="Cancelar", command=cancelar,
                   bootstyle="secondary").pack(side=RIGHT, padx=(0, 6))
        ent_mag.bind("<Return>", aceptar)
        top.bind("<Escape>", cancelar)
        _al_cambiar_ahora()  # estado inicial: «Desde/Hasta» deshabilitado
        self.raiz.wait_window(top)
        return resultado["valor"]

    def _actualizar_eventquery(self, contrasena, ini14, fin14):
        """
        Baja y reprocesa el eventquery para la ventana pedida.

        Todo el paso intermedio (descarga, proc_query) se hace en
        trabajo/agencias/ para que sus new_* / new_2_* NO caigan en datos/ y no
        los mezcle _concatenar_eventquery. Deja una referencia aislada en
        datos/eventos_eventquery_ahora.json (no toca el eventquery del análisis).
        Devuelve True si quedó lista.
        """
        import traer_catalogos as tc
        aislado = os.path.join("trabajo", "agencias")
        os.makedirs(aislado, exist_ok=True)
        try:
            with tc.Conexion(contrasena, log=self._log) as conexion:
                tc.verificar_conexion(conexion, log=self._log,
                                      progreso=self._progreso_local)
                ruta = tc.traer_eventquery(
                    ini14, fin14, conexion, cwd=aislado, log=self._log,
                    progreso=self._progreso_local, forzar=True)
        except Exception as e:
            self._log("[error] no se pudo bajar eventquery: %s" % e)
            return False
        if not ruta or not os.path.isfile(ruta):
            self._log("No se obtuvo el catálogo de eventquery.")
            return False
        dat = os.path.join(aislado, "eventquery_ahora.dat")
        # proc_query escribe sus new_* / new_2_* en <cwd>/datos; con cwd aislado,
        # quedan en trabajo/agencias/datos y no tocan los del análisis. Las rutas
        # van absolutas porque el proceso corre en otro cwd.
        if self._popen([_script("proc_query_harz_2.py"), os.path.abspath(ruta),
                        os.path.abspath(dat)], cwd=aislado):
            self._log("Falló el procesamiento de eventquery.")
            return False
        new2 = os.path.abspath(
            os.path.join(aislado, "datos", "new_2_" + os.path.basename(ruta)))
        if not os.path.isfile(new2):
            self._log("No se generó %s." % new2)
            return False
        # generajson con el cwd normal: necesita grillas/ y escribe el JSON en
        # datos/ (no en la carpeta aislada).
        if self._popen([_script("generajson.py"), new2, "eventquery",
                        "--salida=eventquery_ahora"]):
            self._log("Falló la generación del JSON de eventquery.")
            return False
        return os.path.isfile(
            os.path.join("datos", "eventos_eventquery_ahora.json"))

    def _comparar_agencias(self):
        """
        Consulta agencias externas (EMSC/USGS/GFZ) y las compara con nuestro
        publicado. Reutiliza lo ya procesado si ningún catálogo cambió; si no,
        corre solo las etapas necesarias. Al terminar abre la ventana.
        """
        inicio, fin = self._periodo()
        if not (inicio and fin):
            Messagebox.show_info(
                "No hay un período de análisis cargado. Abra la aplicación con "
                "una ventana de catálogos.", "Comparar agencias",
                parent=self.raiz)
            return
        params = self._pedir_parametros_agencias()
        if params is None:
            self._log("Comparación de agencias cancelada.")
            return
        minmag, agencias, refrescar, modo, actualizar, desde14, hasta14 = params

        # Referencia: la del análisis, o la que se acaba de bajar si se pide
        # actualizar eventquery en modo "hasta ahora".
        referencia = ("eventquery_ahora"
                      if (modo == "ahora" and actualizar) else "eventquery")

        # Camino rápido: ya está todo procesado y no se pidió refrescar.
        if not refrescar and self._comparacion_al_dia(minmag, agencias, modo,
                                                      referencia, desde14,
                                                      hasta14):
            self._log("La comparación de agencias ya está al día; se muestra "
                      "lo procesado.")
            self._ver_comparacion_agencias(reutilizada=True)
            return

        # La actualización de eventquery necesita la contraseña del servidor.
        contrasena = None
        if modo == "ahora" and actualizar:
            contrasena = self._pedir_contrasena()
            if not contrasena:
                self._log("Comparación de agencias cancelada (sin contraseña).")
                return

        def _ventana_efectiva():
            """(ini_iso, fin_iso, ini14, fin14): del análisis o 'Desde/Hasta'."""
            if modo == "ahora":
                # Ventana elegida por el usuario (UTC); respaldo: la del
                # análisis. El fin es el «Hasta» elegido (por defecto, el
                # instante en que se abrió el diálogo).
                ini_dt = datetime.datetime.strptime(
                    desde14 if desde14 else inicio, "%Y%m%d%H%M%S")
                fin_dt = datetime.datetime.strptime(
                    hasta14 if hasta14 else fin, "%Y%m%d%H%M%S")
                return (ini_dt.strftime("%Y-%m-%dT%H:%M:%S"),
                        fin_dt.strftime("%Y-%m-%dT%H:%M:%S"),
                        ini_dt.strftime("%Y%m%d%H%M%S"),
                        fin_dt.strftime("%Y%m%d%H%M%S"))
            return (self._periodo_iso(inicio), self._periodo_iso(fin),
                    inicio, fin)

        def tarea():
            nonlocal referencia
            ini_iso, fin_iso, ini14, fin14 = _ventana_efectiva()
            self._log("***** Comparando con agencias (%s a %s): referencia = "
                      "catálogo de eventos publicados extraído (eventquery) "
                      "*****" % (ini_iso, fin_iso))
            if modo == "ahora" and actualizar:
                self._log("Se actualiza el eventquery hasta el fin elegido; "
                          "solo afecta esta comparación.")
                if self._actualizar_eventquery(contrasena, ini14, fin14):
                    referencia = "eventquery_ahora"
                else:
                    referencia = "eventquery"
                    self._log("No se pudo actualizar eventquery; se comparará "
                              "contra el catálogo del análisis.")
            if refrescar or not self._consulta_agencias_al_dia(
                    minmag, agencias, modo, [ini14, fin14]):
                self._log("Consultando agencias externas…")
                self._popen([_script("consultaapi.py"), ini_iso, fin_iso,
                             "%g" % minmag])
            else:
                self._log("Se reutilizan los catálogos de agencias ya "
                          "consultados.")
            for ag in agencias:
                cs = os.path.join(
                    "datos", "agencias",
                    "consultaapi_%s.csv" % AGENCIAS_EXTERNAS[ag])
                js = os.path.join("datos", "eventos_agencia_%s.json" % ag)
                if not os.path.isfile(cs):
                    self._log("No se obtuvo el catálogo de %s; se omite." % ag)
                    continue
                if refrescar or not self._mas_nuevo_que(js, [cs]):
                    self._popen([_script("generajson.py"), cs, "agencia",
                                 "--agencia=%s" % ag,
                                 "--salida=agencia_%s" % ag])
                else:
                    self._log("Se reutiliza el JSON de %s." % ag)
            self._popen([_script("agencias.py"), "%g" % minmag]
                        + list(agencias)
                        + ["--referencia=%s" % referencia])
            self._escribir_estado_agencias(minmag, agencias, modo,
                                           [ini14, fin14], referencia,
                                           desde=desde14, hasta=hasta14)

        def al_terminar():
            self._log("Comparación de agencias terminada; mostrando "
                      "resultados.")
            try:
                self._actualizar_gate()
                self._ver_comparacion_agencias()
            finally:
                # Limpieza de trabajo/agencias/ tras la comparación: en
                # finally para que un error de la ventana no la deje tirada.
                try:
                    shutil.rmtree(rutas.p_trabajo("agencias"))
                    self._log("trabajo/agencias/ limpio.")
                except OSError:
                    pass

        self._iniciar(tarea, on_fin=al_terminar, plan=AGENCIAS_PLAN)

    def _leer_csv_datos(self, nombre):
        """Lee un CSV de datos/ como (encabezados, filas), o None si no hay."""
        ruta = os.path.join("datos", nombre)
        if not os.path.isfile(ruta):
            return None
        with open(ruta, encoding="utf-8-sig", newline="") as f:
            filas = list(csv.reader(f))
        if len(filas) < 2:
            return None
        return filas[0], filas[1:]

    def _descargar_comparacion(self, padre):
        """Baja los dos layouts de la comparación en un solo paso."""
        import descargas
        archivos = [("comparacion_agencias.csv", "comparacion agencias", ""),
                    ("comparacion_agencias_larga.csv",
                     "comparacion agencias larga", "_larga")]
        datos = []
        for nombre, etiqueta, sufijo in archivos:
            par = self._leer_csv_datos(nombre)
            if par is not None:
                datos.append((etiqueta, par[0], par[1], sufijo))
        # Se suma la cobertura (ventana solicitada y real por agencia) para que
        # quien procese el archivo fuera tenga de dónde salieron los datos.
        try:
            consulta = (self._leer_estado_agencias().get("consulta") or {})
            cobertura = self._cobertura_agencias(
                consulta.get("agencias") or list(AGENCIAS_EXTERNAS))
            filas_cob = [[f["agencia"], f["eventos"], f["desde"], f["hasta"],
                          f["rezago"]] for f in cobertura["agencias"]]
            sol = cobertura["solicitada"]
            filas_cob.append(["Solicitada", "", sol["desde"], sol["hasta"], ""])
            datos.append(("cobertura agencias",
                          ["Agencia", "Eventos", "Desde (UTC)", "Hasta (UTC)",
                           "Rezago"], filas_cob, "_cobertura"))
        except Exception:
            pass
        if not datos:
            self._log("No hay comparación para descargar.")
            return
        # Un solo diálogo para los tres archivos: el nombre base lo elige el
        # usuario y cada archivo agrega su sufijo según lo que contiene.
        sufijos = tuple(sufijo for *_resto, sufijo in datos)
        pedido = descargas.preguntar_descarga(padre, "comparacion agencias",
                                              sufijos=sufijos)
        if pedido is None:
            return
        formato, nombre_base, sobrescribir = pedido
        escritos = []
        for etiqueta, encab, filas, sufijo in datos:
            ruta = descargas.exportar_tabla(
                encab, filas, etiqueta, formato=formato,
                nombre=nombre_base + sufijo, sobrescribir=sobrescribir)
            if ruta:
                escritos.append(ruta)
        if escritos:
            descargas._avisar_exito(padre, escritos[0])
            self._log("Descargado: %s"
                      % ", ".join(os.path.basename(r) for r in escritos))

    def _descargar_sin_contraparte(self, padre):
        import descargas
        par = self._leer_csv_datos("agencias_sin_contraparte.csv")
        if par is None:
            self._log("No hay eventos de agencia sin contraparte para "
                      "descargar.")
            return
        descargas.descargar_tabla(padre, par[0], par[1],
                                  "agencias sin contraparte")

    def _armar_listado(self, padre, nombre_json, al_plotear):
        """Listado por evento (Treeview) con scroll, orden, tope y doble clic."""
        TOPE = 2000
        ruta = os.path.join("datos", nombre_json)
        try:
            with open(ruta, encoding="utf-8") as f:
                data = json.load(f)
            encab = data.get("encabezados") or []
            filas = data.get("filas") or []
        except (OSError, ValueError):
            encab, filas = [], []
        if not encab or not filas:
            ttk.Label(padre, text="No hay eventos para listar.",
                      bootstyle="secondary").pack(anchor=W, padx=6, pady=4)
            return
        if len(filas) > TOPE:
            ttk.Label(
                padre, bootstyle="warning", wraplength=900, justify=LEFT,
                text="Mostrando %d de %d eventos — usa «Descargar» para el "
                     "listado completo." % (TOPE, len(filas))
            ).pack(anchor=W, padx=6, pady=(4, 0))
            filas = filas[:TOPE]

        claves = ["c%d" % i for i in range(len(encab))]
        rs = self._importar_revisor()
        anchos = {"Fecha_Hora": 150, "Latitud": 80, "Longitud": 80,
                  "Prof.": 70, "Mag.": 60, "Agencias": 220, "Δmáx (km)": 90}
        barra_sel = ttk.Frame(padre)
        barra_sel.pack(side=TOP, fill=X, padx=6, pady=(2, 0))
        boton_sel = ttk.Button(
            barra_sel, text="Descargar seleccionados", state="disabled",
            bootstyle="secondary-outline")
        boton_sel.pack(side="right")
        estado_sel = ttk.Label(barra_sel, text="", bootstyle="secondary")
        estado_sel.pack(side="right", padx=(0, 8))
        marco = ttk.Frame(padre)
        marco.pack(fill=BOTH, expand=YES, padx=6, pady=4)
        arbol = ttk.Treeview(marco, columns=claves, show="headings", height=8)
        mostradas = list(filas)
        estado_orden = {"col": None, "desc": False}
        seleccion = {"sel": None}

        def _actualizar_boton_seleccion():
            sel = seleccion["sel"]
            cantidad = sel.contar() if sel is not None else 0
            boton_sel.configure(
                state="normal" if cantidad else "disabled",
                text=("Descargar seleccionados (%d)" % cantidad
                      if cantidad else "Descargar seleccionados"))
            estado_sel.config(text=("%d seleccionados" % cantidad
                                    if cantidad else ""))

        if rs is not None:
            seleccion["sel"] = rs.SeleccionTabla(
                arbol, al_cambiar=_actualizar_boton_seleccion)

        def _clave(fila, idx):
            cols = fila.get("cols") or []
            val = cols[idx] if idx < len(cols) else ""
            try:
                return (0, float(val), "")
            except (TypeError, ValueError):
                return (1, 0.0, str(val).lower())

        def _llenar():
            arbol.delete(*arbol.get_children())
            sel = seleccion["sel"]
            if sel is not None:
                sel.reiniciar()
            for i, fila in enumerate(mostradas):
                arbol.insert("", END, iid=str(i), values=fila.get("cols", []))
                if sel is not None:
                    sel.registrar(str(i), fila)
            _actualizar_boton_seleccion()

        def _ordenar(idx):
            if estado_orden["col"] == idx:
                estado_orden["desc"] = not estado_orden["desc"]
            else:
                estado_orden["col"] = idx
                estado_orden["desc"] = False
            mostradas.sort(key=lambda f: _clave(f, idx),
                           reverse=estado_orden["desc"])
            _llenar()

        def _plotear_sel(_evento=None):
            sel = arbol.selection()
            if not sel:
                return
            try:
                fila = mostradas[int(sel[0])]
            except (ValueError, IndexError):
                return
            al_plotear(fila)

        for i, (clave, titulo) in enumerate(zip(claves, encab)):
            arbol.heading(clave, text=titulo,
                          command=lambda i=i: _ordenar(i))
            arbol.column(clave, width=anchos.get(titulo, 100), minwidth=50,
                         stretch=False)
        barra_v = ttk.Scrollbar(marco, orient="vertical", command=arbol.yview)
        barra_h = ttk.Scrollbar(marco, orient="horizontal", command=arbol.xview)
        arbol.configure(yscrollcommand=barra_v.set, xscrollcommand=barra_h.set)
        barra_v.pack(side=RIGHT, fill=Y)
        barra_h.pack(side=BOTTOM, fill=X)
        arbol.pack(side=LEFT, fill=BOTH, expand=YES)
        def _descargar_seleccionados():
            sel = seleccion["sel"]
            if sel is None:
                return
            elegidas = sel.seleccionadas(filas)
            if not elegidas:
                estado_sel.config(text="No hay eventos seleccionados.")
                return
            encabezados = list(encab)
            filas_csv = [fila.get("cols") or [] for fila in elegidas]
            etiqueta = "seleccion_%s" % os.path.splitext(nombre_json)[0]
            descargas.descargar_tabla(
                padre.winfo_toplevel(), encabezados, filas_csv, etiqueta)

        boton_sel.configure(command=_descargar_seleccionados)
        arbol.bind("<Double-1>", _plotear_sel)
        _llenar()

    def _plotear_comparacion(self, fila):
        """Doble clic en el listado de comparación: plotea evento + agencias."""
        import plotear
        try:
            plotear.abrir_comparacion(fila.get("evento") or {}, "eventquery")
        except Exception as e:
            self._log("[error] no se pudo plotear la comparación: %s" % e)

    def _plotear_grupo(self, fila):
        """Doble clic en sin contraparte: plotea las agencias asociadas."""
        import plotear
        try:
            plotear.abrir_eventos(fila.get("eventos") or [], "agencia")
        except Exception as e:
            self._log("[error] no se pudo plotear el grupo de agencias: %s" % e)

    def _ver_comparacion_agencias(self, reutilizada=False):
        """Ventana con mapas y listado: comparación y sin contraparte con CSN."""
        ruta_cmp = os.path.join("datos", "comparacion_agencias.json")
        ruta_sp = os.path.join("datos", "agencias_sin_par.json")
        if not os.path.isfile(ruta_cmp):
            Messagebox.show_info("Todavía no hay resultados de comparación de "
                                 "agencias.", "Comparar agencias",
                                 parent=self.raiz)
            return
        self._log("Abriendo ventana «Comparar agencias»…")
        import plotear
        top = ttk.Toplevel(title="Comparar agencias", master=self.raiz)
        top.geometry("1040x700")

        # Cabecera: de dónde salió el resultado (reutilizado/ejecutado) y qué
        # ventana se pidió. La cobertura real por agencia va en el botón, para
        # no amontonar todo en una línea. Sin modal ni grab (misma cautela que
        # el aviso «Sin datos»).
        consulta = (self._leer_estado_agencias().get("consulta") or {})
        cobertura = self._cobertura_agencias(
            consulta.get("agencias") or list(AGENCIAS_EXTERNAS))
        cabecera = ttk.Frame(top, padding=(10, 8, 10, 0))
        cabecera.pack(side=TOP, fill=X)
        texto_estado = "%s · %s UTC" % (
            "Reutilizada" if reutilizada else "Ejecutada",
            consulta.get("timestamp") or "sin fecha")
        # Colores: el tema es claro (flatly), así que el gris 'secondary'
        # (fondo blanco) queda ilegible. La etiqueta de estado va como badge
        # azul oscuro (inverse-primary, texto blanco) y la ventana solicitada
        # en color de texto normal, en 10 pt, para que se distinga.
        ttk.Label(cabecera, text=texto_estado, bootstyle="inverse-primary",
                  font=("", 10, "bold")).pack(side=TOP, anchor=W)
        sol = cobertura["solicitada"]
        if sol["desde"] and sol["hasta"]:
            mag = (" · mag ≥ %g" % sol["minmag"]
                   if sol.get("minmag") is not None else "")
            fila_sol = ttk.Frame(cabecera)
            fila_sol.pack(side=TOP, anchor=W, pady=(4, 0))
            ttk.Label(fila_sol, text="Solicitada:", font=("", 10, "bold")
                      ).pack(side=LEFT)
            ttk.Label(fila_sol, font=("", 10), text=" %s → %s UTC%s"
                      % (sol["desde"], sol["hasta"], mag)).pack(side=LEFT)
        ttk.Button(cabecera, text="Cobertura por agencia",
                   bootstyle="primary-outline",
                   command=lambda: self._detalles_cobertura(top, cobertura)
                   ).pack(side=TOP, anchor=W, pady=(6, 4))
        ttk.Separator(top, orient="horizontal").pack(side=TOP, fill=X)

        cuaderno = ttk.Notebook(top)
        cuaderno.pack(fill=BOTH, expand=YES)

        def _agregar_tab(texto, ruta_json, fuente, vista, etiqueta,
                         nombre_listado_json, al_plotear, descargar):
            marco = ttk.Frame(cuaderno)
            cuaderno.add(marco, text=texto)
            barra = ttk.Frame(marco, padding=(4, 4))
            barra.pack(side=TOP, fill=X)
            ttk.Button(barra, text="Descargar", bootstyle="primary-outline",
                       command=descargar).pack(side=RIGHT)
            paned = ttk.PanedWindow(marco, orient=VERTICAL)
            paned.pack(side=TOP, fill=BOTH, expand=YES)
            panel = ttk.Frame(paned)
            listado = ttk.Frame(paned)
            paned.add(panel, weight=3)
            paned.add(listado, weight=1)
            abierto = False
            if os.path.isfile(ruta_json):
                try:
                    abierto = plotear.abrir_panel(panel, ruta_json, fuente,
                                                  etiqueta_fuente=etiqueta,
                                                  vista=vista)
                except Exception:
                    # Un panel que revienta no debe tumbar la ventana entera
                    # (ni el cleanup de trabajo/agencias/).
                    self._log("[error panel %s] %s"
                              % (texto, traceback.format_exc()))
            if not abierto:
                ttk.Label(panel, justify=CENTER,
                          text="No hay datos para mostrar en esta pestaña."
                          ).pack(expand=YES)
            self._armar_listado(listado, nombre_listado_json, al_plotear)

        _agregar_tab("Comparación", ruta_cmp, "eventquery",
                     "comparacion_agencias", "Comparación con agencias",
                     "comparacion_agencias_listado.json",
                     self._plotear_comparacion,
                     lambda: self._descargar_comparacion(top))
        _agregar_tab("Agencias sin contraparte con CSN", ruta_sp, "agencia",
                     "agencias_sin_par", "Agencias sin contraparte con CSN",
                     "agencias_sin_par_listado.json",
                     self._plotear_grupo,
                     lambda: self._descargar_sin_contraparte(top))

        # La ventana crece (solo lo necesario, acotado a la pantalla) para que
        # el mapa y el listado inferior entren enteros; si no, el listado queda
        # cortado hasta agrandar la ventana a mano.
        top.minsize(880, 480)
        try:
            ajuste.ajustar(top, minimo=(1040, 700))
        except Exception:
            self._log("[error ajuste] " + traceback.format_exc())
        self._log("Ventana «Comparar agencias» lista.")

    def _abrir_catalogo_comparado(self, padre, nombre):
        """Abre el listado de eventos de una agencia o de eventquery."""
        if nombre == "eventquery":
            ruta = os.path.join("datos", "todos_eventquery.csv")
            columnas = [
                ("Fecha_Hora", "Fecha y hora", 150, False),
                ("Latitud", "Latitud", 90, True),
                ("Longitud", "Longitud", 90, True),
                ("Prof.", "Prof. km", 80, True),
                ("Mag.", "Mag.", 70, True),
                ("Tipo_mag.", "Tipo mag.", 85, False),
                ("Referencia", "Referencia", 300, False),
                ("Percep.", "Percib.", 70, False),
            ]
            etiqueta = "eventquery"
        else:
            sufijo = AGENCIAS_EXTERNAS.get(nombre)
            ruta = (os.path.join("datos", "agencias",
                                 "consultaapi_%s.csv" % sufijo)
                    if sufijo else "")
            columnas = [
                ("Fecha_Hora", "Fecha y hora", 150, False),
                ("Latitud", "Latitud", 90, True),
                ("Longitud", "Longitud", 90, True),
                ("Prof.", "Prof. km", 80, True),
                ("Mag.", "Mag.", 70, True),
                ("Tipo Mag.", "Tipo mag.", 85, False),
                ("Referencia", "Referencia", 300, False),
                ("Agencia", "Agencia", 90, False),
            ]
            etiqueta = "catalogo_%s" % str(nombre).lower()

        if not ruta or not os.path.isfile(ruta):
            Messagebox.show_info(
                "No está el catálogo de %s.\n\n%s" % (nombre, ruta),
                "Catálogo %s" % nombre, parent=padre)
            return
        try:
            with open(ruta, encoding="utf-8-sig", newline="") as f:
                filas = list(csv.DictReader(f))
        except OSError as e:
            Messagebox.show_info("No se pudo leer el catálogo de %s:\n%s"
                                 % (nombre, e), "Catálogo %s" % nombre,
                                 parent=padre)
            return
        if not filas:
            Messagebox.show_info("El catálogo de %s no tiene eventos."
                                 % nombre, "Catálogo %s" % nombre,
                                 parent=padre)
            return

        rs = self._importar_revisor()
        if rs is None:
            return
        claves = [c[0] for c in columnas]

        def _valores(fila):
            return [str(fila.get(c, "") or "") for c in claves]

        top = ttk.Toplevel(title="Catálogo %s" % nombre, master=padre)
        top.withdraw()
        top.geometry("1100x560")
        top.minsize(820, 440)
        marco = ttk.Frame(top, padding=10)
        marco.pack(fill=BOTH, expand=YES)
        rs.abrir_tabla(
            marco, filas, columnas, _valores, cwd=self.cwd, log=self._log,
            filtros=("texto",), seleccionable=True,
            etiqueta=etiqueta, descarga_texto="Descargar", descarga_todo=True,
            descarga_bootstyle="primary-outline",
            texto_filtro="Filtrar:")
        self._ajustar_popup(top, (1100, 560))
        top.deiconify()
        try:
            descargas.encima_de(padre, top, modal=False)
        except Exception:
            pass

    def _detalles_cobertura(self, padre, cobertura):
        """
        Ventana de consulta (NO modal) con la ventana solicitada y la real por
        agencia. Se abre oculta, se arma entera y solo entonces se muestra (un
        solo mapeo, para no dejar un destello de caja fantasma).
        """
        top = ttk.Toplevel(title="Cobertura por agencia", master=padre)
        top.withdraw()
        top.geometry("780x340")
        marco = ttk.Frame(top, padding=12)
        marco.pack(fill=BOTH, expand=YES)
        sol = cobertura["solicitada"]
        mag = (" · mag ≥ %g" % sol["minmag"]
               if sol.get("minmag") is not None else "")
        ttk.Label(marco, bootstyle="primary", font=("", 10, "bold"),
                  text="Ventana solicitada (todas las agencias)"
                  ).pack(anchor=W)
        ttk.Label(marco, text="%s → %s UTC%s"
                  % (sol["desde"] or "—", sol["hasta"] or "—", mag)
                  ).pack(anchor=W, pady=(0, 8))
        cols = ("ag", "n", "desde", "hasta", "rezago")
        arbol = ttk.Treeview(marco, columns=cols, show="headings", height=6)
        for clave, texto, ancho in [("ag", "Agencia", 90),
                                    ("n", "Eventos", 70),
                                    ("desde", "Desde (UTC)", 175),
                                    ("hasta", "Hasta (UTC)", 175),
                                    ("rezago", "Rezago", 90)]:
            arbol.heading(clave, text=texto)
            arbol.column(clave, width=ancho, anchor=W)
        for f in cobertura["agencias"]:
            arbol.insert("", END, values=(
                f["agencia"], f["eventos"], f["desde"] or "—",
                f["hasta"] or "—", f["rezago"] or "—"))
        arbol.pack(fill=BOTH, expand=YES, pady=(0, 8))
        # Nota en color de texto normal (no el gris 'secondary', ilegible en
        # tema claro) y 9 pt.
        ttk.Label(marco, font=("", 9),
                  wraplength=740, justify=LEFT,
                  text="«Desde/Hasta (UTC)» son el primer y el último evento "
                       "reportado entre los devueltos (no la cobertura total "
                       "del catálogo). El rezago compara el último evento con "
                       "el fin solicitado.").pack(anchor=W)
        botones = ttk.Frame(marco)
        botones.pack(fill=X, pady=(8, 0))
        menu = Menu(top, tearoff=False)
        for fila in cobertura["agencias"]:
            agencia = fila["agencia"]
            sufijo = AGENCIAS_EXTERNAS.get(agencia)
            ruta = (os.path.join("datos", "agencias",
                                 "consultaapi_%s.csv" % sufijo)
                    if sufijo else "")
            menu.add_command(
                label="%s (%d eventos)" % (agencia, fila["eventos"]),
                command=lambda a=agencia: self._abrir_catalogo_comparado(top, a),
                state="normal" if ruta and os.path.isfile(ruta) else "disabled")
        menu.add_separator()
        ruta_eventquery = os.path.join("datos", "todos_eventquery.csv")
        menu.add_command(
            label="eventquery (referencia)",
            command=lambda: self._abrir_catalogo_comparado(top, "eventquery"),
            state="normal" if os.path.isfile(ruta_eventquery) else "disabled")
        ttk.Menubutton(
            botones, text="Catálogos", menu=menu,
            bootstyle="secondary-outline").pack(side=LEFT)
        ttk.Button(botones, text="Cerrar", command=top.destroy,
                   bootstyle="secondary").pack(side=RIGHT)
        top.deiconify()
        try:
            descargas.encima_de(padre, top, modal=False)
        except Exception:
            pass

    def _concatenar_eventquery(self, forzar=False):
        """
        Arma datos/todos_eventquery.csv con todos los new_2_*.csv.

        Es un derivado puro de esos archivos, así que se saltea si la salida es
        más nueva que todas las entradas: no hay forma de que esté desactualizada
        y el trabajo es una pasada completa sobre el archivo. Antes se rehacía
        siempre y por eso reabrir la app costaba una concatización entera.

        forzar=True lo usa «Procesar catálogos», que acaba de regenerar todo y
        quiere dejar el concatenado rehecho aunque las fechas den por bien.
        """
        carpeta = "datos"
        salida = os.path.join(carpeta, "todos_eventquery.csv")
        try:
            partes = sorted(n for n in os.listdir(carpeta)
                            if n.startswith("new_2_") and n.endswith(".csv"))
        except OSError:
            partes = []
        if (not forzar and partes
                and _derivado_al_dia(salida, partes, carpeta)):
            self._log("Reutilizado %s (ya estaba al día con %d new_2_*.csv)."
                      % (salida, len(partes)))
            return
        self._log("Concatenando %s/new_2_*.csv -> %s" % (carpeta, salida))
        primera = True
        with open(salida, "w") as destino:
            for nombre in partes:
                ruta = os.path.join(carpeta, nombre)
                with open(ruta) as origen:
                    for i, linea in enumerate(origen):
                        if i == 0 and not primera:
                            continue
                        destino.write(linea)
                primera = False

    def _asegurar_parametros_seiscomp(self):
        """
        Deja datos/seiscomp_parametros.csv al día desde la exportación.

        Ese archivo es el que permite atribuir los eventos de eventquery a un
        responsable de SeisComp (el operador de la solución preferred). Antes
        solo se generaba al pulsar «Datos de SeisComp»: si la exportación la
        había descargado la solicitud de catálogos, el cruce de eventquery
        quedaba solo contra Seisan y casi ningún evento mostraba responsable.

        Es idempotente: si el archivo es más nuevo que la exportación no hace
        nada. No necesita la base de SeisComp, solo el CSV exportado.
        """
        par = self._par_seiscomp_para_catalogo()
        if par is None:
            return
        destino = os.path.join("datos", "seiscomp_parametros.csv")
        try:
            if (os.path.isfile(destino)
                    and os.path.getmtime(destino)
                    >= os.path.getmtime(par["eventos"])):
                return
        except OSError:
            pass
        self._log("Generando la atribución de SeisComp desde %s..."
                  % os.path.basename(par["eventos"]))
        self._popen([_script("seiscomp_a_parametros.py"), par["eventos"]])

    def _mapa_analistas_eventquery(self):
        """
        {fecha_hora: "Seisan: Jere; SeisComp: mdur"} para la columna del
        catálogo de eventquery.

        eventquery no informa el responsable; el nombre se deduce cruzando cada
        evento publicado con las soluciones locales de Seisan y SeisComp. Se
        reusa la misma lógica del panel (generajson) para que la columna y la
        viñeta no puedan decir cosas distintas.
        """
        try:
            import generajson as gj
        except Exception as e:
            self._log("[aviso] no se pudo deducir el analista probable: %s" % e)
            return {}
        indices = []
        for nombre in ("seiscomp", "seisan"):
            indice = gj._cargar_atribucion(nombre)
            if indice:
                indices.append(indice)
        if not indices:
            return {}
        rs = self._importar_revisor()
        if rs is None:
            return {}
        ruta = os.path.join("datos", "todos_eventquery.csv")
        if not os.path.isfile(ruta):
            return {}
        etiqueta = {"seiscomp": "SeisComp", "seisan": "Seisan"}
        mapa = {}
        for fila in rs._leer_catalogo(ruta):
            fecha_hora = str(fila.get("Fecha_Hora", "")).strip()
            if not fecha_hora:
                continue
            try:
                lat = float(fila.get("Latitud"))
                lon = float(fila.get("Longitud"))
            except (TypeError, ValueError):
                continue
            partes = []
            for indice in indices:
                encontradas = gj._analistas_para_evento(indice, fecha_hora,
                                                        lat, lon)
                for e in encontradas or ():
                    nombres = ", ".join(e.get("analistas") or [])
                    partes.append("%s: %s"
                                  % (etiqueta.get(e.get("fuente"),
                                                  e.get("fuente")), nombres))
            if partes:
                mapa[fecha_hora] = "; ".join(partes)
        return mapa

    def _atribuir_para_eventquery(self):
        """
        Corre la atribución de Solutiones locales al catálogo publicado si hace
        falta, antes de generar el JSON de eventquery.

        Sin esto habría que repetir el análisis completo después de exportar
        SeisComp, porque la atribución vive dentro del plan principal y ahí se
        saltea si seiscomp_parametros.csv todavía no existe. Comparar
        mtime contra el archivo de salida es lo que hace que el flujo se
        autorrepare: si la exportación es más nueva que la atribución, esta
        está vieja y hay que rehacerla.

        Atribuir es un extra y no bloquea el panel, así que si falta una fuente
        se sigue igual. Lo que no se hace es seguir en silencio: queda escrito
        contra qué fuentes se atribuyó y contra cuáles no, con el motivo. Sin
        eso, un panel con la atribución casi vacía se ve igual que uno
        completo, y no hay forma de notar que falta el dato.
        """
        base = os.path.join("datos", "new_2_" + self.base)
        if not os.path.isfile(base):
            return
        try:
            mtime_base = os.path.getmtime(base)
        except OSError:
            return
        candidatos = (
            (os.path.join("datos", "seiscomp_parametros.csv"), "seiscomp"),
            (os.path.join("datos", "salida_collect.csv"), "seisan"),
        )
        usadas = []
        omitidas = []
        for entrada, etiqueta in candidatos:
            if not os.path.isfile(entrada) or os.path.getsize(entrada) == 0:
                omitidas.append((etiqueta, "no está %s" % entrada))
                continue
            # Está vencida si el catálogo o las soluciones locales son más
            # recientes que ella: si se reexporta SeisComp, el archivo local
            # cambia y el cruce hay que rehacerlo aunque el catálogo no se haya
            # tocado.
            mas_reciente = max(mtime_base, os.path.getmtime(entrada))
            salida = os.path.join("datos", "atribucion_%s.csv" % etiqueta)
            if (os.path.isfile(salida)
                    and os.path.getmtime(salida) >= mas_reciente):
                usadas.append(etiqueta)
                continue
            self._log("Actualizando la atribución a %s..." % etiqueta)
            comando = [_script("compara.py"), base, entrada]
            if etiqueta != "seisan":
                comando.append(etiqueta + "_")
            self._popen(comando)
            if os.path.isfile(salida):
                usadas.append(etiqueta)
        # Atribuir es un extra y no bloquea el panel, así que una fuente que
        # falta no es un error: pero SÍ tiene que quedar a la vista. El silencio
        # es lo peligroso aquí, porque el panel igual abre con todos los eventos
        # y parece completo, solo que casi ninguno muestra responsable.
        if usadas:
            self._log("Atribución de eventquery: %s."
                      % " y ".join(usadas))
        for etiqueta, motivo in omitidas:
            self._log("Sin atribución contra %s (%s). "
                      "Pulse «Procesar catálogos» si la quiere."
                      % (etiqueta, motivo))

    def _rm(self, ruta):
        try:
            os.remove(ruta)
        except OSError:
            pass

    def _limpiar_trabajo_y_ploteo(self):
        """Borra los intermedios de trabajo/ y los logs de ploteo/ para evitar acumulación.
        No toca el caché (datos/, informes/, catálogos crudos)."""
        # Limpieza de trabajo/
        try:
            shutil.rmtree(rutas.p_trabajo(""))
        except OSError:
            pass
        # Limpieza de logs de ploteo/
        for f in (rutas.p_ploteo("percibidos.txt"),
                  rutas.p_ploteo("resumen_sesion.log"),
                  rutas.p_ploteo("resumen_historico.log")):
            try:
                os.remove(f)
            except OSError:
                pass

    # --------------------------------------------------- ver repetidos
    def _abrir_descargas(self):
        """Abre la carpeta de descargas del directorio de trabajo."""
        carpeta = descargas.carpeta_descargas(self.cwd)
        if descargas.abrir_carpeta(carpeta):
            self._log("Descargas: %s" % carpeta)
        else:
            self._log("No se pudo abrir el explorador de archivos; la carpeta "
                      "de descargas es %s" % carpeta)

    def _agregar_boton_web(self, tabla, columna_fecha):
        """
        Agrega el acceso al catálogo diario de sismologia.cl a una tabla.

        'tabla' es el diccionario que devuelve revisa_seiscomp.abrir_tabla y
        'columna_fecha' la clave de la fila que contiene la fecha/hora local.
        El botón se habilita solo cuando hay una fila seleccionada con fecha
        válida; no modifica los datos ni las columnas de la tabla.
        """
        def _abrir_dia_web():
            fila = tabla["fila_actual"]()
            if fila is None:
                return
            url = _url_dia_sismologia(fila.get(columna_fecha))
            if url is None:
                tabla["etiqueta_estado"].config(
                    text=("El evento no tiene una fecha válida para abrir "
                          "la web."))
                return
            try:
                if not webbrowser.open(url, new=2):
                    self._log("No se pudo abrir el navegador: %s" % url)
                    tabla["etiqueta_estado"].config(
                        text="No se pudo abrir el navegador.")
            except Exception as e:
                self._log("[error] no se pudo abrir el navegador: %s" % e)
                tabla["etiqueta_estado"].config(
                    text="No se pudo abrir el navegador.")

        boton = ttk.Button(
            tabla["barra"], text="Abrir en sismologia.cl",
            bootstyle="secondary-outline", command=_abrir_dia_web,
            state="disabled")
        boton.pack(side="right", padx=(6, 0))

        def _actualizar_boton(_evento=None):
            fila = tabla["fila_actual"]()
            habilitado = (fila is not None
                          and _url_dia_sismologia(fila.get(columna_fecha))
                          is not None)
            boton.configure(state="normal" if habilitado else "disabled")

        tabla["arbol"].bind("<<TreeviewSelect>>", _actualizar_boton, add="+")
        _actualizar_boton()
        return boton

    def _ver_repetidos(self):
        rs = self._importar_revisor()
        if rs is None:
            return
        top = ttk.Toplevel(title="Eventos repetidos", master=self.raiz)
        top.geometry("920x580")
        top.minsize(760, 480)

        marco = ttk.Frame(top, padding=10)
        marco.pack(fill=BOTH, expand=YES)

        # Arriba, los informes disponibles con su conteo de eventos.
        cols = ("archivo", "eventos")
        arbol = ttk.Treeview(marco, columns=cols, show="headings", height=6)
        arbol.heading("archivo", text="Archivo")
        arbol.heading("eventos", text="Eventos")
        arbol.column("archivo", width=400, anchor=W)
        arbol.column("eventos", width=80, anchor=CENTER)
        arbol.pack(fill=X)

        # Abajo, el informe elegido como tabla ordenable (abrir_tabla le arma el
        # filtro, el orden por encabezado y las descargas).
        marco_tabla = ttk.Frame(marco)
        marco_tabla.pack(fill=BOTH, expand=YES, pady=(8, 0))

        rutas = {}
        titulos = {}
        iids = {}
        vistas = {}
        actual = {"ruta": None}

        def _contar_informe(ruta):
            if not os.path.isfile(ruta):
                return 0
            try:
                with open(ruta, encoding="utf-8", errors="replace") as f:
                    n = sum(1 for _ in f)
            except OSError:
                return 0
            return n - 1 if n > 0 else 0

        for titulo, ruta in REP_FILES:
            n = _contar_informe(ruta)
            if os.path.isfile(ruta):
                etiqueta = "%s  (%s)" % (titulo, os.path.basename(ruta))
            else:
                etiqueta = "%s  (no generado)" % titulo
            iid = arbol.insert("", END, values=(etiqueta, n))
            rutas[iid] = ruta
            titulos[ruta] = titulo
            iids[ruta] = iid

        # La atribución se carga una sola vez por ventana, y solo si se abre un
        # informe publicado (los otros ya traen su analista en el archivo).
        cache_indices = {"valor": None}

        def _indices():
            if cache_indices["valor"] is None:
                cache_indices["valor"] = _indices_atribucion()
            return cache_indices["valor"]

        def _valores(columnas):
            def valores(fila):
                salida = []
                for clave, _titulo, _ancho, es_num in columnas:
                    valor = fila.get(clave, "")
                    if es_num and clave in ("latitud", "longitud"):
                        salida.append(rs._numero(valor, 3))
                    elif es_num and clave in ("prof", "mag"):
                        salida.append(rs._numero(valor, 1))
                    else:
                        salida.append(rs._texto(valor))
                return salida
            return valores

        def _firma(ruta):
            try:
                st = os.stat(ruta)
            except OSError:
                return None
            return (getattr(st, "st_mtime_ns", st.st_mtime), st.st_size)

        def _actualizar_fila(ruta, n):
            iid = iids.get(ruta)
            if iid is None:
                return
            titulo = titulos.get(ruta, os.path.basename(ruta))
            if os.path.isfile(ruta):
                etiqueta = "%s  (%s)" % (titulo, os.path.basename(ruta))
            else:
                etiqueta = "%s  (no generado)" % titulo
                n = 0
            arbol.item(iid, values=(etiqueta, n))

        def _mostrar_crudo(contenedor, lineas):
            caja = ScrolledText(contenedor, padding=4, autohide=True,
                                height=14)
            caja.pack(fill=BOTH, expand=YES)
            caja.text.configure(state=NORMAL, font=("Consolas", 9))
            caja.text.insert(END, "\n".join(lineas))
            caja.text.configure(state=DISABLED)

        def _crear_vista(ruta):
            frame = ttk.Frame(marco_tabla)
            if not os.path.isfile(ruta):
                ttk.Label(frame, bootstyle="secondary",
                          text="El informe no está generado.").pack(
                              anchor="w", pady=(0, 4))
                return frame, 0
            filas, crudo = _leer_informe_repetidos(ruta)
            if filas is None:
                ttk.Label(
                    frame, bootstyle="secondary",
                    text="El informe está en el formato viejo (separado por "
                         "espacios); vuelva a procesar los catálogos para "
                         "verlo como tabla.").pack(anchor="w", pady=(0, 4))
                _mostrar_crudo(frame, crudo)
                return frame, _contar_informe(ruta)
            if not filas:
                ttk.Label(frame, bootstyle="secondary",
                          text="El informe no tiene eventos.").pack(anchor="w")
                return frame, 0
            columnas = _repetidos_columnas(ruta)
            if os.path.basename(ruta).startswith("rep_publica"):
                _analistas_probables_repetidos(filas, _indices())
            tabla = rs.abrir_tabla(
                frame, filas, columnas, _valores(columnas),
                cwd=self.cwd, log=self._log, seleccionable=True,
                etiqueta=os.path.splitext(os.path.basename(ruta))[0],
                descarga_texto="Descargar", descarga_todo=True,
                descarga_bootstyle="primary-outline",
                texto_filtro="Filtrar",
                texto_detalle="«Descargar»: lo filtrado. "
                              "«Descargar todo»: completo.")
            self._agregar_boton_web(tabla, "fecha_hora")
            return frame, len(filas)

        def _mostrar_vista(frame):
            for vista in vistas.values():
                if vista["frame"] is frame:
                    continue
                if vista["frame"].winfo_manager():
                    vista["frame"].pack_forget()
            if not frame.winfo_manager():
                frame.pack(fill=BOTH, expand=YES)
            self._ajustar_popup(top, (920, 580))

        def al_seleccionar(evento=None):
            sel = arbol.selection()
            if not sel:
                return
            ruta = rutas[sel[0]]
            firma = _firma(ruta)
            vista = vistas.get(ruta)
            if (vista is not None and vista["firma"] == firma
                    and vista["frame"].winfo_exists()):
                if actual["ruta"] != ruta:
                    _mostrar_vista(vista["frame"])
                    actual["ruta"] = ruta
                return
            if vista is not None:
                try:
                    vista["frame"].destroy()
                except TclError:
                    pass
            frame, n = _crear_vista(ruta)
            vistas[ruta] = {"frame": frame, "firma": firma}
            _actualizar_fila(ruta, n)
            _mostrar_vista(frame)
            actual["ruta"] = ruta

        arbol.bind("<<TreeviewSelect>>", al_seleccionar)
        hijos = arbol.get_children()
        if hijos:
            arbol.selection_set(hijos[0])
            al_seleccionar()

    def _ver_no_publicados(self, fuente=None):
        """
        Ventana con el listado de no publicados, una pestaña por fuente.

        SeisComp va primero y por defecto; Seisan después. Cada pestaña se
        arma solo al seleccionarla, para no construir las dos de golpe (el
        listado de Seisan se pide a demanda). Si se pasa 'fuente' se abre
        directo en esa pestaña, para no romper al generador de capturas.
        """
        top = ttk.Toplevel(title="No publicados", master=self.raiz)
        top.geometry("1100x620")
        top.minsize(900, 520)
        cuaderno = ttk.Notebook(top)
        cuaderno.pack(fill=BOTH, expand=YES)
        fuentes = (("seiscomp", "SeisComp"), ("seisan", "Seisan"))
        marcos, construido = {}, {}
        for clave, etiqueta in fuentes:
            marco = ttk.Frame(cuaderno)
            cuaderno.add(marco, text=etiqueta)
            marcos[clave] = marco
            construido[clave] = False

        def _construir(clave):
            if construido[clave]:
                return
            construido[clave] = True
            self._construir_tabla_no_publicados(marcos[clave], clave)
            self._ajustar_popup(top, (1100, 620))

        def _al_cambiar(_evento=None):
            actual = cuaderno.select()
            for clave, marco in marcos.items():
                if str(marco) == actual:
                    _construir(clave)
                    break

        cuaderno.bind("<<NotebookTabChanged>>", _al_cambiar)
        inicial = fuente if fuente in marcos else "seiscomp"
        if inicial != "seiscomp":
            cuaderno.select(marcos[inicial])
        _construir(inicial)

    def _construir_tabla_no_publicados(self, contenedor, fuente):
        """
        Listado de los eventos no publicados (mag >= 2.5) de una fuente.

        Complementa al panel/mapa: aquí se ve el conjunto completo en una tabla,
        sin tener que ir evento por evento en el ploteo.

        Se apoya en revisa_seiscomp.abrir_tabla: ordena por encabezado, filtra
        por texto con «Aplicar» y descarga con el filtro («Descargar») o entero
        («Descargar todo»).
        """
        ruta = os.path.join(
            "datos", "no_pub_desde_2_5_%sestricto.csv"
            % ("" if fuente == "seisan" else "seiscomp_"))
        filas = []
        if os.path.isfile(ruta):
            try:
                with open(ruta, encoding="utf-8-sig", newline="") as f:
                    filas = list(csv.DictReader(f))
            except OSError as e:
                self._log("[error] no publicados %s: %s" % (fuente, e))

        rs = self._importar_revisor()
        if rs is None:
            return

        # Profundidad, magnitud y coordenadas ordenan como número (es_num): por
        # texto un 9.0 quedaría después de un 10.0.
        columnas = [("Fecha_Hora", "Fecha y hora", 150, False),
                    ("Latitud", "Latitud", 90, True),
                    ("Longitud", "Longitud", 90, True),
                    ("Prof.", "Prof. km", 80, True),
                    ("Mag.", "Mag.", 70, True),
                    ("Tipo_mag.", "Tipo mag.", 80, False),
                    ("Analista", "Analista", 120, False),
                    ("Publicado_en", "Publicado en", 110, False),
                    ("Estado", "Estado", 360, False),
                    ("Dt_otra_seg", "Δt otra fuente (s)", 135, True),
                    ("Dist_otra_km", "Dist. otra fuente (km)", 165, True),
                    ("Analista_otra", "Analista otra fuente", 155, False)]
        claves = [c for c, _, _, _ in columnas]

        def _valores(fila):
            return [str(fila.get(c, "") or "") for c in claves]

        columnas = _anchos_columnas_por_contenido(columnas, filas, _valores)

        def _ver_mapa(_evento=None):
            """Abre planta+perfil del evento elegido (ploteo de un evento suelto)."""
            fila = tabla["fila_actual"]()
            if fila is None:
                return

            def _num(clave):
                try:
                    return float(str(fila.get(clave, "")).strip())
                except (TypeError, ValueError):
                    return None

            if _num("Latitud") is None or _num("Longitud") is None:
                tabla["etiqueta_estado"].config(
                    text="El evento no tiene coordenadas.")
                return
            evento = {
                "fecha hora": fila.get("Fecha_Hora", ""),
                "latitud": _num("Latitud"), "longitud": _num("Longitud"),
                "prof": _num("Prof."), "magnitud": fila.get("Mag.", ""),
                "tipo": fila.get("Tipo_mag.", ""),
                "analista": fila.get("Analista", ""),
            }
            try:
                import plotear
                plotear.abrir_evento(evento, fuente)
            except Exception as e:
                self._log("[error] no se pudo plotear: %s" % e)
                tabla["etiqueta_estado"].config(
                    text="No se pudo plotear el evento.")

        ayuda_estados = ttk.Frame(contenedor, padding=(10, 6, 10, 0))
        ayuda_estados.pack(fill=X)
        leyenda_estados = ttk.Label(
            ayuda_estados, bootstyle="secondary", justify="left",
            text=("Publicado en = confirmado · Candidato = revisar · "
                  "Ambiguo = varias soluciones · Sin coincidencia = no está · "
                  "No evaluable = faltan datos"))

        def _mostrar_ayuda_estados():
            try:
                descargas.mostrar_texto_mono(
                    contenedor.winfo_toplevel(),
                    "Criterios de clasificación de No publicados",
                    AYUDA_ESTADOS_NO_PUBLICADOS)
            except Exception as e:
                self._log("[error] no se pudo abrir la ayuda: %s" % e)

        boton_ayuda = ttk.Button(
            ayuda_estados, text="Criterios de clasificación",
            bootstyle="secondary-outline", command=_mostrar_ayuda_estados)
        boton_ayuda.pack(side="right", padx=(8, 0))
        leyenda_estados.pack(side="left", fill=X, expand=True)

        def _acomodar_leyenda(evento):
            leyenda_estados.configure(
                wraplength=max(260, evento.width - 260))

        ayuda_estados.bind("<Configure>", _acomodar_leyenda, add="+")

        marco = ttk.Frame(contenedor, padding=10)
        marco.pack(fill=BOTH, expand=YES)
        tabla = rs.abrir_tabla(
            marco, filas, columnas, _valores, cwd=self.cwd, log=self._log,
            filtros=("texto",), iid_por_id=False, seleccionable=True,
            etiqueta="no publicados %s" % fuente,
            descarga_texto="Descargar",
            descarga_bootstyle="primary-outline", descarga_todo=True,
            texto_filtro="Filtrar:", texto_detalle="Doble clic plotea",
            con_miniatura=True, ancho_lista=780, ancho_mini=300)

        self._agregar_boton_web(tabla, "Fecha_Hora")
        arbol = tabla["arbol"]

        def _evento_mapa(fila):
            def _num(clave):
                try:
                    return float(str(fila.get(clave, "")).strip())
                except (TypeError, ValueError):
                    return None
            return {
                "latitud": _num("Latitud"), "longitud": _num("Longitud"),
                "prof": _num("Prof."), "magnitud": fila.get("Mag.", ""),
                "tipo": fila.get("Tipo_mag.", ""),
                "fecha hora": fila.get("Fecha_Hora", ""),
                "analista": fila.get("Analista", ""),
            }

        zoom = {"control": None}

        def _accion_zoom(nombre):
            control = zoom["control"]
            if control is not None:
                control[nombre]()

        try:
            from matplotlib.figure import Figure
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
            import plotear
            mapa = {"fig": Figure(figsize=(3.6, 4.4), dpi=82)}
            ttk.Label(tabla["marco_mini"], text="Vista nacional",
                      bootstyle="secondary",
                      font=("", 9, "bold")).pack(anchor="w", padx=8,
                                                 pady=(4, 0))
            controles = ttk.Frame(tabla["marco_mini"])
            controles.pack(side="bottom", fill=X, padx=8, pady=(0, 4))
            ttk.Label(controles, text="Rueda: zoom · arrastrar: mover",
                      bootstyle="secondary",
                      font=("", 8)).pack(anchor="w")
            fila_controles = ttk.Frame(controles)
            fila_controles.pack(fill=X)
            for texto, accion, ancho in (
                    ("+", "zoom_in", 2), ("−", "zoom_out", 2),
                    ("Centrar", "centrar", None),
                    ("Restablecer", "reset", None)):
                opciones = {"bootstyle": "secondary-outline",
                            "command": lambda a=accion: _accion_zoom(a)}
                if ancho is not None:
                    opciones["width"] = ancho
                boton = ttk.Button(fila_controles, text=texto, **opciones)
                boton.pack(side="right", padx=(4, 0))
            lienzo = FigureCanvasTkAgg(mapa["fig"],
                                       master=tabla["marco_mini"])
            lienzo.get_tk_widget().pack(fill=BOTH, expand=YES,
                                        padx=(8, 0), pady=2)
        except Exception as e:
            self._log("[error] no se pudo crear el mapa nacional: %s" % e)
            ttk.Label(tabla["marco_mini"],
                      text="No se pudo crear el mapa.",
                      bootstyle="secondary").pack(expand=YES)
        else:
            def _dibujar_mapa(fila):
                fig_mapa = mapa["fig"]
                fig_mapa.clear()
                if fila is None:
                    ax = fig_mapa.add_subplot(111)
                    ax.text(0.5, 0.5, "Seleccione un evento\npara ubicarlo",
                            ha="center", va="center", fontsize=8,
                            color="#555555", transform=ax.transAxes)
                    ax.set_axis_off()
                    fig_mapa.canvas.draw_idle()
                    return
                evento = _evento_mapa(fila)
                if evento["latitud"] is None or evento["longitud"] is None:
                    ax = fig_mapa.add_subplot(111)
                    ax.text(0.5, 0.5, "El evento no tiene\ncoordenadas",
                            ha="center", va="center", fontsize=8,
                            color="#555555", transform=ax.transAxes)
                    ax.set_axis_off()
                    fig_mapa.canvas.draw_idle()
                    return
                try:
                    dibujado = plotear.dibujar_mini_mapa_evento(
                        fig_mapa, evento, fuente)
                    if dibujado:
                        extent = plotear.extent_mapa_nacional(evento)
                        centro = (evento["longitud"], evento["latitud"])
                        if zoom["control"] is None:
                            zoom["control"] = plotear.conectar_zoom_mapa(
                                fig_mapa, extent, centro=centro)
                        else:
                            zoom["control"]["actualizar"](extent, centro)
                except Exception as e:
                    self._log("[error] no se pudo dibujar el mapa nacional: "
                              "%s" % e)
                    fig_mapa.clear()
                    ax = fig_mapa.add_subplot(111)
                    ax.text(0.5, 0.5, "No se pudo dibujar\nel mapa",
                            ha="center", va="center", fontsize=8,
                            color="#555555", transform=ax.transAxes)
                    ax.set_axis_off()
                    fig_mapa.canvas.draw_idle()

            def _actualizar_mapa(_evento=None):
                _dibujar_mapa(tabla["fila_actual"]())

            arbol.bind("<<TreeviewSelect>>", _actualizar_mapa, add="+")
            _dibujar_mapa(None)

        arbol.bind("<Double-1>", _ver_mapa)
        arbol.bind("<Return>", _ver_mapa)
        self._log("No publicados de %s: %d eventos." % (fuente, len(filas)))

    # ----------------------------------------------------------- SeisComp
    # Todo lo de SeisComp se apoya en revisa_seiscomp.py, que ya sabe qué es
    # una exportación, cómo se lee la ventana del catálogo y cómo se dibuja la
    # revisión. Aquí solo se orquesta: qué se le pregunta al usuario, cuándo se
    # exporta y en qué pestaña se muestra.

    def _importar_revisor(self):
        """Carga revisa_seiscomp.py, o avisa por qué no pudo."""
        try:
            import revisa_seiscomp
            return revisa_seiscomp
        except Exception as e:
            self._log("[error] no se pudo cargar revisa_seiscomp.py: %s" % e)
            return None

    def _ventana_del_catalogo(self):
        """
        (desde, hasta) con las fechas del catálogo de entrada, o None.

        Se le pregunta al revisor y no se recalcula aquí: el formato del
        catálogo tiene variantes (con 'T' y 'Z', con espacio) y duplicar esa
        lógica haría que un día los dos caminos dejaran de coincidir.
        """
        if not self.archivo or not os.path.isfile(self.archivo):
            return None
        rs = self._importar_revisor()
        if rs is None:
            return None
        return rs._ventana_del_catalogo(self.archivo)

    def _pares_seiscomp(self):
        """
        Las exportaciones de SeisComp de datos/ que terminaron de escribirse.

        Se filtran por la marca '.completo' porque una exportación cortada a
        mitad deja el CSV de eventos a medias, y plotearla daría la impresión
        de que en esa ventana no hubo más eventos de los que hubo.
        """
        rs = self._importar_revisor()
        if rs is None:
            return []
        return [p for p in rs._pares_disponibles(self.cwd)
                if self._exportacion_completa(p["eventos"])
                and os.path.isfile(p["fases"] or "")]

    @staticmethod
    def _ruta_de_marca(ruta_eventos):
        """
        Ruta del archivo que marca que aquella exportación terminó.

        Esto devuelve una RUTA, no un sí/no. Por eso el predicado está aparte,
        en _exportacion_completa: usar esta ruta directamente como condición
        nunca avisó nada, porque una ruta no vacía siempre es verdadera y la
        marca dejó de filtrar exportaciones cortadas sin que se notara.
        """
        base, extension = os.path.splitext(ruta_eventos)
        return "%s%s.completo" % (base, extension or ".csv")

    @classmethod
    def _exportacion_completa(cls, ruta_eventos):
        """Si la exportación de esa ventana tiene la marca de que terminó."""
        return os.path.isfile(cls._ruta_de_marca(ruta_eventos))

    def _par_seiscomp_para_catalogo(self, silencioso=False):
        """
        El par exportado que mejor cubre la ventana del catálogo, o None.

        Va por cobertura y no por fecha de modificación a propósito: cuando se
        revisan varios períodos en la misma carpeta, la última exportación no
        es la que corresponde al catálogo que se está mirando ahora.

        Con 'silencioso' no avisa cuando hay exportaciones pero ninguna cubre la
        ventana. Lo necesita la compuerta del botón, que consulta esto en cada
        cambio de estado y llenaría el registro de ese mismo aviso.
        """
        rs = self._importar_revisor()
        if rs is None:
            return None
        pares = self._pares_seiscomp()
        if not pares:
            return None
        par = rs._elegir_par(pares, self._ventana_del_catalogo())
        if par is None and pares and not silencioso:
            # Sin cobertura no se elige el más reciente a ciegas: se avisa y
            # deja que el usuario elija, que es lo seguro.
            self._log("Hay exportaciones de SeisComp en datos/, pero ninguna "
                      "se superpone con la ventana de este catálogo.")
        return par

    def _anunciar_cobertura(self, par):
        """Deja en el registro cuánto de la ventana del catálogo se cubrió."""
        rs = self._importar_revisor()
        if rs is None:
            return
        ventana = self._ventana_del_catalogo()
        if ventana is None:
            return
        propia = rs._ventana_del_nombre(os.path.basename(par["eventos"]))
        inicio, fin, fraccion = rs._cobertura(propia, ventana)
        if fraccion <= 0:
            return
        if fraccion < 0.999:
            self._log("La exportación cubre el %.0f%% de la ventana del "
                      "catálogo (%s a %s)."
                      % (fraccion * 100,
                         inicio.strftime("%Y-%m-%d %H:%M"),
                         fin.strftime("%Y-%m-%d %H:%M")))

    def _abrir_revisor(self, par, seleccionar=True):
        """Muestra la revisión de SeisComp en su pestaña."""
        rs = self._importar_revisor()
        if rs is None:
            return
        for w in list(self.seiscomp_frame.winfo_children()):
            w.destroy()
        try:
            ok = rs.abrir_panel(self.seiscomp_frame, par["eventos"],
                                par["fases"], par.get("no_picadas"),
                                log=self._log, cwd=self.cwd)
        except Exception as e:
            self._log("[error] revisión de SeisComp: %s" % e)
            return
        if not ok:
            self._log("No se pudo abrir la revisión de SeisComp "
                      "(faltan archivos o no hay interfaz).")
            return
        if seleccionar and self.cuaderno_catalogos is not None:
            self.cuaderno_catalogos.select(self.seiscomp_frame)
        # La lista de eventos de SeisComp pide ~1340 px de ancho; se ajusta la
        # ventana de catálogos, que ahora es la que lo contiene.
        self._ajustar_catalogos()
        self._log("Revisión de SeisComp abierta (%s)."
                  % os.path.basename(par["eventos"]))
        self._anunciar_cobertura(par)


def main():
    if len(sys.argv) < 3:
        print("Uso: python3 app.py <archivo_entrada.csv> <archivo_salida.dat>"
              " [estado.json]")
        sys.exit(1)
    archivo = sys.argv[1]
    salida = sys.argv[2]
    estado = None
    if len(sys.argv) >= 4:
        try:
            estado = json.loads(sys.argv[3])
        except (TypeError, ValueError):
            estado = None
    raiz = ttk.Window(themename="flatly")
    App(raiz, archivo, salida, estado=estado)
    raiz.mainloop()


if __name__ == "__main__":
    main()
