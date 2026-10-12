#!/usr/bin/env python3
"""
consultaapi.py
==============
Consulta los catálogos de agencias sismológicas externas por FDSN/API y los
deja en CSV para compararlos con nuestras soluciones publicadas.

Agencias: EMSC, USGS (NEIC) y GFZ. Se consultan tres cuadrantes que cubren el
territorio continental e insular cercano, la Isla de Pascua (Rapa Nui) y el
Territorio Antártico Chileno.

Las 3 agencias × 3 cuadrantes se consultan EN PARALELO (hilos) para no encadenar
hasta nueve requests secuenciales, y se emite progreso (`prog.avance`) para que
la barra de la app avance durante la descarga.

Uso:
    python3 consultaapi.py <starttime> <endtime> <minmag>

    starttime/endtime : ISO ('2026-09-01T00:00:00' o '2026-09-01')
    minmag            : magnitud mínima

Salida (en datos/agencias/):
    consultaapi_EMSC.csv
    consultaapi_NEIC.csv
    consultaapi_GFZ.csv

Columnas: id, Fecha_Hora, Latitud, Longitud, Prof., Mag., Tipo Mag.,
Referencia, Agencia.
"""

import datetime
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import timezone
from io import StringIO

import pandas as pd
import requests

import prog

DIR_SALIDA = os.path.join("datos", "agencias")

BASE_URL_EMSC = "http://www.seismicportal.eu/fdsnws/event/1/query?"
BASE_URL_USGS = "https://earthquake.usgs.gov/fdsnws/event/1/query?"
BASE_URL_GFZ = "http://geofon.gfz.de/fdsnws/event/1/query?"

# Cuadrantes geográficos que cubren todo Chile: continental e insular cercano,
# Rapa Nui y el Territorio Antártico Chileno.
CUADRANTES_CHILE = [
    {"name": "Continental e Insular Cercano",
     "minlat": -56.0, "maxlat": -17.5, "minlon": -76.0, "maxlon": -66.0},
    {"name": "Chile Insular Oceánico (Rapa Nui)",
     "minlat": -28.0, "maxlat": -26.0, "minlon": -110.0, "maxlon": -108.0},
    {"name": "Territorio Antártico Chileno",
     "minlat": -90.0, "maxlat": -60.0, "minlon": -90.0, "maxlon": -53.0},
]

COLUMNAS = ['Fecha_Hora', 'Latitud', 'Longitud', 'Prof.', 'Mag.',
            'Tipo Mag.', 'Referencia', 'Agencia']


def _guardar(filas, agencia, archivo):
    """Escribe el CSV de una agencia (o avisa si no hubo eventos)."""
    if not filas:
        print("No se encontraron eventos en %s para los cuadrantes de Chile."
              % agencia)
        return
    df = pd.DataFrame(filas, columns=COLUMNAS)
    df['Fecha_Hora'] = pd.to_datetime(df['Fecha_Hora'])
    df = df.drop_duplicates().sort_values(by='Fecha_Hora').reset_index(drop=True)
    df.insert(0, 'id', range(1, len(df) + 1))
    os.makedirs(DIR_SALIDA, exist_ok=True)
    df.to_csv(os.path.join(DIR_SALIDA, archivo), index=False)
    print("Solicitud exitosa, eventos únicos encontrados en %s: %d"
          % (agencia, len(df)))


def _limpia_fecha_emsc(texto):
    """Convierte el 'time' de EMSC a 'YYYY-MM-DD HH:MM:SS'."""
    limpio = str(texto).strip().replace('Z', '')
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.datetime.strptime(limpio, fmt).strftime(
                "%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
    return None


def _limpia_fecha_usgs(valor):
    """Convierte el 'time' de USGS (epoch ms o ISO) a 'YYYY-MM-DD HH:MM:SS'."""
    if valor is None:
        return None
    if isinstance(valor, (int, float)):
        obj = datetime.datetime.fromtimestamp(valor / 1000.0, timezone.utc)
        return obj.strftime("%Y-%m-%d %H:%M:%S")
    limpio = str(valor).replace('Z', '')
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.datetime.strptime(limpio, fmt).strftime(
                "%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
    return None


def _emsc_cuadrante(cuadrante, starttime, endtime, minmag):
    filas = []
    parametros = {
        'starttime': starttime, 'endtime': endtime, 'minmag': minmag,
        'minlatitude': cuadrante['minlat'], 'maxlatitude': cuadrante['maxlat'],
        'minlongitude': cuadrante['minlon'], 'maxlongitude': cuadrante['maxlon'],
        'format': 'json',
    }
    try:
        respuesta = requests.get(BASE_URL_EMSC, params=parametros, timeout=30)
        if respuesta.status_code == 204:
            return filas
        respuesta.raise_for_status()
        texto = respuesta.text.strip()
        if not texto or texto.startswith("<html") or texto.startswith("<!DOCTYPE"):
            print("EMSC (%s): el servicio devolvió algo que no son datos."
                  % cuadrante['name'])
            return filas
        for evento in respuesta.json().get('features', []):
            props = evento.get('properties', {})
            fecha = _limpia_fecha_emsc(props.get('time'))
            if (fecha is None or props.get('lat') is None
                    or props.get('lon') is None):
                continue
            filas.append((fecha, round(props.get('lat'), 3),
                          round(props.get('lon'), 3), props.get('depth'),
                          props.get('mag'), props.get('magtype'),
                          props.get('flynn_region', ''),
                          props.get('auth', 'EMSC')))
    except Exception as e:
        print("EMSC (%s): error en la solicitud: %s"
              % (cuadrante['name'], e))
    return filas


def _usgs_cuadrante(cuadrante, starttime, endtime, minmag):
    filas = []
    parametros = {
        'starttime': starttime[:10], 'endtime': endtime[:10],
        'minmag': minmag,
        'minlatitude': cuadrante['minlat'], 'maxlatitude': cuadrante['maxlat'],
        'minlongitude': cuadrante['minlon'], 'maxlongitude': cuadrante['maxlon'],
        'format': 'geojson',
    }
    try:
        respuesta = requests.get(BASE_URL_USGS, params=parametros, timeout=30)
        respuesta.raise_for_status()
        for evento in respuesta.json().get('features', []):
            props = evento.get('properties', {})
            coords = evento.get('geometry', {}).get('coordinates', [])
            if len(coords) < 3 or coords[0] is None or coords[1] is None:
                continue
            fecha = _limpia_fecha_usgs(props.get('time'))
            if fecha is None:
                continue
            filas.append((fecha, round(coords[1], 3), round(coords[0], 3),
                          round(coords[2], 1), round(props.get('mag', 0.0), 3),
                          props.get('magType', 'ND'),
                          props.get('place', ''),
                          props.get('auth', 'NEIC')))
    except Exception as e:
        print("USGS (%s): error en la solicitud: %s"
              % (cuadrante['name'], e))
    return filas


def _gfz_cuadrante(cuadrante, starttime, endtime, minmag):
    filas = []
    parametros = {
        'starttime': starttime[:10], 'endtime': endtime[:10],
        'minmag': minmag,
        'minlatitude': cuadrante['minlat'], 'maxlatitude': cuadrante['maxlat'],
        'minlongitude': cuadrante['minlon'], 'maxlongitude': cuadrante['maxlon'],
        'format': 'text',
    }
    try:
        respuesta = requests.get(BASE_URL_GFZ, params=parametros, timeout=30)
        respuesta.raise_for_status()
        datos = respuesta.text
        if not datos.strip() or all(
                linea.startswith('#') for linea in datos.strip().split('\n')):
            return filas
        df = pd.read_csv(StringIO(datos), sep='|', comment='#')
        if df.empty or df.shape[1] < 14:
            return filas
        for r in df.itertuples(index=False, name=None):
            # Orden de columnas GFZ: EventID, Fecha_Hora, Latitud, Longitud,
            # Prof., Author, Catalog, Contributor, ContributorID, Tipo Mag.,
            # Mag., MagAuthor, Referencia, otro.
            try:
                mag = round(float(r[10]), 1)
            except (TypeError, ValueError):
                mag = r[10]
            filas.append((r[1], r[2], r[3], r[4], mag, r[9], r[12], r[7]))
    except Exception as e:
        print("GFZ (%s): error en la solicitud: %s"
              % (cuadrante['name'], e))
    return filas


def main():
    if len(sys.argv) < 4:
        print("Uso: python3 consultaapi.py <starttime> <endtime> <minmag>")
        sys.exit(1)
    starttime, endtime, minmag = sys.argv[1], sys.argv[2], sys.argv[3]
    print("***** Consultando agencias externas (%s a %s, mag >= %s) *****"
          % (starttime, endtime, minmag))

    tareas = []
    for cuad in CUADRANTES_CHILE:
        tareas.append(("EMSC", cuad['name'], _emsc_cuadrante, cuad))
        tareas.append(("USGS", cuad['name'], _usgs_cuadrante, cuad))
        tareas.append(("GFZ", cuad['name'], _gfz_cuadrante, cuad))

    por_agencia = {"EMSC": [], "USGS": [], "GFZ": []}
    total = len(tareas)
    hechos = 0
    with ThreadPoolExecutor(max_workers=total) as ejecutor:
        futuros = {
            ejecutor.submit(func, cuad, starttime, endtime, minmag):
                (ag, cuad['name'])
            for ag, nombre, func, cuad in tareas
        }
        for fut in as_completed(futuros):
            ag, nombre = futuros[fut]
            try:
                por_agencia[ag].extend(fut.result())
            except Exception as e:
                print("[%s] error en %s: %s" % (ag, nombre, e))
            finally:
                hechos += 1
                prog.avance(hechos / total)
            print("[%s] %s listo." % (ag, nombre))

    _guardar(por_agencia["EMSC"], "EMSC", "consultaapi_EMSC.csv")
    _guardar(por_agencia["USGS"], "USGS", "consultaapi_NEIC.csv")
    _guardar(por_agencia["GFZ"], "GFZ", "consultaapi_GFZ.csv")


if __name__ == "__main__":
    main()
