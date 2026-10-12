# -*- coding: utf-8 -*-
"""
Exportación completa con la base simulada: se comprueba que salen los tres CSV,
que la marca los cuenta, que --reusar exige el de no picadas, que se valida la
cadena de épocas (red/estación/sensorlocation/stream) y que id_origen y los
campos de disponibilidad quedan en el archivo.
"""
import csv
import io
import os
import re
import shutil
import sys
import tempfile
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
import exporta_ventana_seiscomp as ex

fallos = []


def check(nombre, condicion, detalle=""):
    if condicion:
        print("  OK    %s" % nombre)
    else:
        print("  FALLA %s  -> %s" % (nombre, detalle))
        fallos.append(nombre)


RAIZ = tempfile.mkdtemp(prefix="seiscomp_export_")

INVENTARIO = [
    {"red": "CL", "estacion": "SCL", "loc": "", "cha": "BHZ",
     "epoca_inicio": datetime(2000, 1, 1), "epoca_fin": None,
     "latitud": -33.45, "longitud": -70.67, "elevacion": 600,
     "lugar": "Santiago", "pais": "Chile"},
    {"red": "CL", "estacion": "COCA", "loc": "", "cha": "BHZ",
     "epoca_inicio": datetime(2000, 1, 1), "epoca_fin": None,
     "latitud": -33.30, "longitud": -70.72, "elevacion": 1120,
     "lugar": "Cochrane", "pais": "Chile"},
    {"red": "CL", "estacion": "LEMA", "loc": "", "cha": "BHZ",
     "epoca_inicio": datetime(2000, 1, 1), "epoca_fin": None,
     "latitud": -33.26, "longitud": -70.90, "elevacion": 880,
     "lugar": "Lema", "pais": "Chile"},
    {"red": "AR", "estacion": "LPA", "loc": "", "cha": "BHZ",
     "epoca_inicio": datetime(2000, 1, 1), "epoca_fin": None,
     "latitud": -26.5, "longitud": -54.6, "elevacion": 200,
     "lugar": "Paso de los Libres", "pais": "Argentina"},
]

EVENTOS = [
    {"id_evento": "ev1", "id_origen": "or1", "ot_utc": datetime(2026, 1, 10, 5, 0),
     "magnitud": 4.5, "tipo_magnitud": "Mlv", "fases": 2, "rms": 0.8,
     "azgap": 45, "latitud": -33.10, "longitud": -70.80,
     "profundidad_km": 80.0, "agencia": "SNC", "operador": "test",
     "region": "Valparaiso", "estatus": "confirmed"},
    {"id_evento": "ev2", "id_origen": "or2", "ot_utc": datetime(2026, 1, 11, 8, 30),
     "magnitud": 3.1, "tipo_magnitud": "Md", "fases": 1, "rms": 1.0,
     "azgap": 90, "latitud": -33.50, "longitud": -71.20,
     "profundidad_km": 40.0, "agencia": "SNC", "operador": "test",
     "region": "Valparaiso", "estatus": "confirmed"},
]

FASES = [
    {"id_evento": "ev1", "id_origen": "or1", "id_pick": "pk1", "red": "CL",
     "estacion": "SCL", "loc": "", "cha": "HHZ", "fase": "P",
     "llegada_utc": datetime(2026, 1, 10, 5, 0, 10), "llegada_us": 0,
     "correccion_s": 1.2, "residual_s": 0.4, "azimut": 10.0,
     "distancia": 0.3, "usada": True, "peso": 1.0, "polaridad": "positive",
     "modo_pick": "manual", "pick_autor": "mary", "pick_agencia": "CSN",
     "pick_metodo": "",
     "snr": 12.5, "mag_estacion": 3.4, "tipo_mag_estacion": "Mlv",
     "tiene_magnitud": "Si", "mag_est_residuo": 0.1,
     "qc_estacion": "aprobado", "est_lat": -33.45, "est_lon": -70.67,
     "est_elev": 600, "est_lugar": "Santiago", "est_pais": "Chile"},
    {"id_evento": "ev1", "id_origen": "or1", "id_pick": "pk2", "red": "CL",
     "estacion": "LEMA", "loc": "", "cha": "HHZ", "fase": "P",
     "llegada_utc": datetime(2026, 1, 10, 5, 0, 12), "llegada_us": 0,
     "correccion_s": 1.4, "residual_s": 0.6, "azimut": 25.0,
     "distancia": 0.4, "usada": False, "peso": 1.0, "polaridad": "positive",
     "modo_pick": "automatic", "pick_autor": "scautopic@host",
     "pick_agencia": "CSN", "pick_metodo": "AIC",
     "snr": 8.0, "mag_estacion": None, "tipo_mag_estacion": None,
     "tiene_magnitud": "No", "mag_est_residuo": None,
     "qc_estacion": "sin_evaluar", "est_lat": -33.26, "est_lon": -70.90,
     "est_elev": 880, "est_lugar": "Lema", "est_pais": "Chile"},
    {"id_evento": "ev2", "id_origen": "or2", "id_pick": "pk3", "red": "CL",
     "estacion": "SCL", "loc": "", "cha": "HHZ", "fase": "P",
     "llegada_utc": datetime(2026, 1, 11, 8, 30, 10), "llegada_us": 0,
     "correccion_s": 0.8, "residual_s": 0.2, "azimut": 5.0,
     "distancia": 0.2, "usada": True, "peso": 1.0, "polaridad": "positive",
     "modo_pick": "manual", "pick_autor": "mary", "pick_agencia": "CSN",
     "pick_metodo": "",
     "snr": 8.0, "mag_estacion": None, "tipo_mag_estacion": None,
     "tiene_magnitud": "No", "mag_est_residuo": None,
     "qc_estacion": "sin_evaluar", "est_lat": -33.45, "est_lon": -70.67,
     "est_elev": 600, "est_lugar": "Santiago", "est_pais": "Chile"},
]


class _Cursor(object):
    def __init__(self, filas):
        self.filas = filas
        self._i = 0

    def execute(self, sql, params=None):
        s = " ".join(sql.split())
        # El orden importa: el SQL de fases también menciona "network net" y
        # "FROM event e" en sus subconsultas de inventario.
        if "AS muestra" in s:
            # Estimación de no picadas: 5 pares sobre 2 eventos de la muestra.
            self.filas = [{"muestra": 2, "pares": 5}]
        elif "count(*) AS total" in s:
            self.filas = [{"total": 2}]
        elif "m_pickID" in s and "m_phase_code" in s:
            self.filas = list(FASES)
        elif "FROM network net" in s and "m_pickID" not in s:
            self.filas = list(INVENTARIO)
        elif "FROM event e" in s:
            self.filas = list(EVENTOS)
        elif "min(o.m_time_value)" in s:
            self.filas = [{"desde": datetime(2020, 1, 1),
                           "hasta": datetime(2027, 1, 1)}]
        elif "count(*)" in s:
            self.filas = [{"llegadas": len(FASES), "origenes": 2}]
        else:
            self.filas = []

    def fetchall(self):
        return self.filas

    def fetchone(self):
        return self.filas[0] if self.filas else None

    def fetchmany(self, n):
        lote, self.filas = self.filas[:n], self.filas[n:]
        return lote

    def close(self):
        pass


class _Conn(object):
    def cursor(self, *a, **k):
        return _Cursor([])

    def close(self):
        pass


ex.conectar = lambda config=None: _Conn()
ex.configuracion = lambda base=None: {"user": "u", "host": "h", "database": "d",
                                      "password": "p", "_origen": "prueba"}
ex._bases_a_consultar = lambda base: ["seiscomp"]
ex._bases_seiscomp = lambda: ["seiscomp"]

salida = os.path.join(RAIZ, "seiscomp_20260101000000_20260131235959.csv")
inicio, fin = datetime(2026, 1, 1), datetime(2026, 1, 31, 23, 59, 59)

print("== exportar_ventana completa ==")
r = ex.exportar_ventana(inicio, fin, salida, "todas", True, False)
for clave in ("ruta", "ruta_fases", "ruta_no_picadas", "eventos", "fases",
              "no_picadas", "descartadas_sin_stream", "radio_km"):
    check("el resultado trae %s" % clave, clave in r, r.keys())
check("los tres archivos existen",
      all(os.path.isfile(r[k]) for k in ("ruta", "ruta_fases",
                                         "ruta_no_picadas")))
check("2 eventos exportados", r["eventos"] == 2, r["eventos"])
check("3 fases exportadas", r["fases"] == 3, r["fases"])
check("radio_km por defecto 400", r["radio_km"] == 400.0, r["radio_km"])
check("sin descartes con inventario completo", r["descartadas_sin_stream"] == 0,
      r["descartadas_sin_stream"])
check("el nombre del archivo es el derivado",
      r["ruta_no_picadas"].endswith("_no_picadas.csv"), r["ruta_no_picadas"])

# El CSV de eventos ahora lleva id_origen.
with io.open(r["ruta"], encoding="utf-8", newline="") as f:
    eventos = list(csv.DictReader(f))
check("la cabecera de eventos trae id_origen",
      list(eventos[0].keys()) == ex.CABECERA, list(eventos[0].keys()))
check("el id_origen del evento está cargado",
      {e["id_evento"]: e["id_origen"] for e in eventos}
      == {"ev1": "or1", "ev2": "or2"},
      [(e["id_evento"], e["id_origen"]) for e in eventos])

# El CSV de fases lleva la procedencia del pick.
with io.open(r["ruta_fases"], encoding="utf-8", newline="") as f:
    fases_csv = list(csv.DictReader(f))
check("la cabecera de fases trae el modo y la procedencia",
      list(fases_csv[0].keys()) == ex.CABECERA_FASES,
      list(fases_csv[0].keys()))
pk1 = [f for f in fases_csv if f["id_pick"] == "pk1"][0]
check("el pick manual queda con autor y sin método",
      pk1["modo_pick"] == "manual" and pk1["pick_autor"] == "mary"
      and pk1["pick_metodo"] == "" and pk1["pick_agencia"] == "CSN", pk1)
pk2 = [f for f in fases_csv if f["id_pick"] == "pk2"][0]
check("el pick automático queda con método AIC",
      pk2["modo_pick"] == "automatic" and pk2["pick_metodo"] == "AIC", pk2)

with io.open(r["ruta_no_picadas"], encoding="utf-8", newline="") as f:
    filas = list(csv.DictReader(f))
print("  (%d filas sin arribos)" % len(filas))
check("la cabecera es la declarada",
      list(filas[0].keys()) == ex.CABECERA_NO_PICADAS if filas else False,
      list(filas[0].keys()) if filas else "sin filas")
por_evento = {}
for fila in filas:
    por_evento.setdefault(fila["id_evento"], []).append(fila)
ev1 = por_evento.get("ev1", [])
ev2 = por_evento.get("ev2", [])
nombres1 = [f["estacion"] for f in ev1]
# SCL y LEMA picaron ev1, así que solo entra COCA (LPA está a 1300 km).
check("ev1 solo trae COCA (SCL y LEMA picaron, LPA está lejos)",
      nombres1 == ["COCA"], nombres1)
coca_ev1 = ev1[0]
check("la distancia de COCA es un decimal",
      re.match(r"^\d+\.\d$", coca_ev1["distancia_km"] or ""),
      coca_ev1["distancia_km"])
check("trae los datos de inventario",
      coca_ev1["est_lugar"] == "Cochrane" and coca_ev1["est_pais"] == "Chile",
      coca_ev1)
check("trae el radio con el que se generó", coca_ev1["radio_km"] == "400.0",
      coca_ev1["radio_km"])
check("trae el id_origen del evento", coca_ev1["id_origen"] == "or1",
      coca_ev1["id_origen"])
check("trae loc_ref y cha_ref", coca_ev1["loc_ref"] == ""
      and coca_ev1["cha_ref"] == "BHZ", coca_ev1)
check("streams_vigentes cuenta 1", coca_ev1["streams_vigentes"] == "1",
      coca_ev1["streams_vigentes"])
check("waveform_status es NO_CONSULTADO",
      coca_ev1["waveform_status"] == "NO_CONSULTADO", coca_ev1)
check("los campos de disponibilidad van vacíos",
      coca_ev1["availability_source"] == ""
      and coca_ev1["cobertura_desde"] == ""
      and coca_ev1["cobertura_hasta"] == "", coca_ev1)
# ev2: solo picó SCL, así que entran COCA y LEMA (LPA cae fuera).
nombres2 = [f["estacion"] for f in ev2]
check("ev2 trae COCA y LEMA", sorted(nombres2) == ["COCA", "LEMA"], nombres2)
check("ev2 viene ordenado por distancia",
      [f["distancia_km"] for f in ev2] == sorted(f["distancia_km"] for f in ev2),
      [(f["estacion"], f["distancia_km"]) for f in ev2])
lema_ev2 = [f for f in ev2 if f["estacion"] == "LEMA"][0]
check("con 24 h de tolerancia LEMA no cuenta ev1 como cercano",
      lema_ev2["actividad_ventana"] == "0", lema_ev2["actividad_ventana"])
coca_ev2 = [f for f in ev2 if f["estacion"] == "COCA"][0]
check("COCA tampoco cuenta un evento cerca en ev2",
      coca_ev2["actividad_ventana"] == "0", coca_ev2["actividad_ventana"])

print("== tolerancia de actividad mas amplia ==")
salida2 = os.path.join(RAIZ, "seiscomp_tol.csv")
r2 = ex.exportar_ventana(inicio, fin, salida2, "todas", True, False,
                         radio_km=300.0, actividad_horas=48.0)
with io.open(r2["ruta_no_picadas"], encoding="utf-8", newline="") as f:
    filas2 = list(csv.DictReader(f))
lema = [f for f in filas2 if f["id_evento"] == "ev2"
        and f["estacion"] == "LEMA"][0]
check("con 48 h de tolerancia LEMA cuenta ev1",
      lema["actividad_ventana"] == "1", lema["actividad_ventana"])

print("== radio mas chico ==")
salida3 = os.path.join(RAIZ, "seiscomp_chico.csv")
r3 = ex.exportar_ventana(inicio, fin, salida3, "todas", True, False,
                         radio_km=10.0)
with io.open(r3["ruta_no_picadas"], encoding="utf-8", newline="") as f:
    filas3 = list(csv.DictReader(f))
check("con radio de 10 km no entra ninguna estación",
      len(filas3) == 0, len(filas3))
check("pero el archivo existe igual, con su encabezado",
      os.path.isfile(r3["ruta_no_picadas"]))

print("== la marca ==")
with io.open(ex._ruta_completo(salida), encoding="utf-8") as f:
    marca = f.read()
check("la marca cuenta las no picadas", "no_picadas 3" in marca, marca.strip())
check("la marca anota el radio", "radio 400 km" in marca, marca.strip())
check("la marca anota las descartadas", "descartadas_sin_stream 0" in marca,
      marca.strip())
check("la marca sigue teniendo eventos y fases",
      "eventos 2" in marca and "fases 3" in marca, marca.strip())

print("== --reusar ==")
rr = ex.exportar_ventana(inicio, fin, salida, "todas", True, True)
check("con los tres archivos reusa", rr["reusado"] is True, rr)
check("devuelve la ruta de no picadas también",
      rr["ruta_no_picadas"].endswith("_no_picadas.csv"))
# Si se borra el de no picadas, ya no puede reusar.
os.remove(r["ruta_no_picadas"])
rr2 = ex.exportar_ventana(inicio, fin, salida, "todas", True, True)
check("sin el archivo de no picadas no reusa", rr2["reusado"] is False,
      rr2["reusado"])
check("y lo vuelve a exportar", os.path.isfile(rr2["ruta_no_picadas"]))

print("== el reuso compara el radio ==")
salida_radio = os.path.join(RAIZ, "seiscomp_radio.csv")
r_300 = ex.exportar_ventana(inicio, fin, salida_radio, "todas", True, False,
                            radio_km=300.0)
check("la marca guarda el radio", ex._radio_de_la_marca(
    ex._ruta_completo(salida_radio)) == 300.0)
r_igual = ex.exportar_ventana(inicio, fin, salida_radio, "todas", True, True,
                              radio_km=300.0)
check("con el mismo radio reusa", r_igual["reusado"] is True,
      r_igual["reusado"])
r_distinto = ex.exportar_ventana(inicio, fin, salida_radio, "todas", True, True,
                                 radio_km=200.0)
check("con otro radio NO reusa", r_distinto["reusado"] is False,
      r_distinto["reusado"])
check("y re-exporta con el radio nuevo", ex._radio_de_la_marca(
    ex._ruta_completo(salida_radio)) == 200.0)

print("== filtro por bindings en la exportación ==")
_original_bindings = ex._consultar_bindings_de_base
ex._consultar_bindings_de_base = lambda base: {("CL", "COCA")}
salida_bind = os.path.join(RAIZ, "seiscomp_bindings.csv")
r_bind = ex.exportar_ventana(inicio, fin, salida_bind, "todas", True, False)
ex._consultar_bindings_de_base = _original_bindings
with io.open(r_bind["ruta_no_picadas"], encoding="utf-8", newline="") as f:
    filas_bind = list(csv.DictReader(f))
check("con bindings solo queda COCA",
      {f["estacion"] for f in filas_bind} == {"COCA"},
      [f["estacion"] for f in filas_bind])
# La ampliación por evento también respeta los bindings.
_original_bindings = ex._consultar_bindings_de_base
_original_actividad = ex._consultar_actividad_de_base
ex._consultar_bindings_de_base = lambda base: {("CL", "COCA")}
ex._consultar_actividad_de_base = lambda base, instante, horas, \
    solo_confirmados=True: {}
filas_amp_bind, _ = ex.no_picadas_de_evento_desde_base(
    "seiscomp", datetime(2026, 1, 10, 5, 0), "ev1", "or1",
    -33.10, -70.80, {("CL", "SCL")}, radio_km=1000.0)
ex._consultar_bindings_de_base = _original_bindings
ex._consultar_actividad_de_base = _original_actividad
check("la ampliación también filtra por bindings",
      {f["estacion"] for f in filas_amp_bind} == {"COCA"},
      [f["estacion"] for f in filas_amp_bind])

print("== validación de la cadena de streams en la exportación ==")
_original_inventario = ex._consultar_inventario_de_base


def _inventario_streams(base, ini, finn):
    return [
        {"red": "CL", "estacion": "SCL", "loc": "", "cha": "BHZ",
         "epoca_inicio": datetime(2000, 1, 1), "epoca_fin": None,
         "latitud": -33.45, "longitud": -70.67, "elevacion": 600,
         "lugar": "Santiago", "pais": "Chile"},
        {"red": "CL", "estacion": "COCA", "loc": "", "cha": "BHZ",
         "epoca_inicio": datetime(2000, 1, 1), "epoca_fin": None,
         "latitud": -33.30, "longitud": -70.72, "elevacion": 1120,
         "lugar": "Cochrane", "pais": "Chile"},
        # Dos streams vigentes: BHZ y BHN.
        {"red": "CL", "estacion": "MULTI", "loc": "10", "cha": "BHZ",
         "epoca_inicio": datetime(2000, 1, 1), "epoca_fin": None,
         "latitud": -33.10, "longitud": -70.75, "elevacion": 500,
         "lugar": "Multi", "pais": "Chile"},
        {"red": "CL", "estacion": "MULTI", "loc": "10", "cha": "BHN",
         "epoca_inicio": datetime(2000, 1, 1), "epoca_fin": None,
         "latitud": -33.10, "longitud": -70.75, "elevacion": 500,
         "lugar": "Multi", "pais": "Chile"},
        # Stream vencido: la cadena no cubre 2026 y la estación se descarta.
        {"red": "CL", "estacion": "VENC", "loc": "", "cha": "BHZ",
         "epoca_inicio": datetime(2000, 1, 1), "epoca_fin": None,
         "latitud": -33.20, "longitud": -70.80, "elevacion": 400,
         "lugar": "Vencida", "pais": "Chile",
         "cha_inicio": datetime(2000, 1, 1), "cha_fin": datetime(2005, 1, 1)},
    ]


ex._consultar_inventario_de_base = _inventario_streams
salida5 = os.path.join(RAIZ, "seiscomp_streams.csv")
r5 = ex.exportar_ventana(inicio, fin, salida5, "todas", True, False)
ex._consultar_inventario_de_base = _original_inventario
check("cuenta las descartadas por stream vencido",
      r5["descartadas_sin_stream"] == 2, r5["descartadas_sin_stream"])
with io.open(r5["ruta_no_picadas"], encoding="utf-8", newline="") as f:
    filas5 = list(csv.DictReader(f))
check("la estación con stream vencido no aparece",
      not any(f["estacion"] == "VENC" for f in filas5),
      [f["estacion"] for f in filas5])
multi = [f for f in filas5 if f["estacion"] == "MULTI"]
check("la estación multi-stream aparece en los dos eventos", len(multi) == 2,
      len(multi))
check("streams_vigentes cuenta los dos streams",
      all(f["streams_vigentes"] == "2" for f in multi),
      [f["streams_vigentes"] for f in multi])
check("loc_ref sale del stream vigente",
      all(f["loc_ref"] == "10" for f in multi),
      [f["loc_ref"] for f in multi])
check("todas las filas traen id_origen",
      all(f["id_origen"] in ("or1", "or2") for f in filas5),
      [(f["estacion"], f["id_origen"]) for f in filas5])

print("== ampliación por evento contra la base ==")
_original_actividad = ex._consultar_actividad_de_base


def _actividad_falsa(base, instante, horas, solo_confirmados=True):
    return {("CL", "COCA"): [instante]}


ex._consultar_inventario_de_base = _inventario_streams
ex._consultar_actividad_de_base = _actividad_falsa
filas_amp, desc_amp = ex.no_picadas_de_evento_desde_base(
    "seiscomp", datetime(2026, 1, 10, 5, 0), "ev1", "or1",
    -33.10, -70.80, {("CL", "SCL")}, radio_km=1000.0, actividad_horas=24.0)
ex._consultar_actividad_de_base = _original_actividad
ex._consultar_inventario_de_base = _original_inventario
nombres_amp = sorted(f["estacion"] for f in filas_amp)
check("la ampliación trae las estaciones vigentes",
      nombres_amp == ["COCA", "MULTI"], nombres_amp)
check("cuenta la descartada por stream vencido", desc_amp == 1, desc_amp)
coca_amp = [f for f in filas_amp if f["estacion"] == "COCA"][0]
check("la ampliación calcula la actividad",
      coca_amp["actividad_ventana"] == 1, coca_amp["actividad_ventana"])
check("la ampliación trae el radio pedido", coca_amp["radio_km"] == 1000.0,
      coca_amp["radio_km"])

# Sin límite: mismas filas válidas, con radio_km=None y sin cortar por distancia.
ex._consultar_inventario_de_base = _inventario_streams
ex._consultar_actividad_de_base = _actividad_falsa
filas_lim, _ = ex.no_picadas_de_evento_desde_base(
    "seiscomp", datetime(2026, 1, 10, 5, 0), "ev1", "or1",
    -33.10, -70.80, {("CL", "SCL")}, radio_km=None, actividad_horas=24.0)
ex._consultar_actividad_de_base = _original_actividad
ex._consultar_inventario_de_base = _original_inventario
check("la ampliación sin límite trae las vigentes",
      sorted(f["estacion"] for f in filas_lim) == ["COCA", "MULTI"],
      [f["estacion"] for f in filas_lim])
check("la ampliación sin límite deja radio_km en None",
      all(f["radio_km"] is None for f in filas_lim))

print("== estimación previa del tamaño ==")
filas_est, mb_est = ex.estimar_no_picadas(["seiscomp"], inicio, fin, 500.0)
# El mock: 5 pares sobre 2 eventos de la muestra, con 2 eventos totales -> 5.
check("la estimación escala la muestra al total", filas_est == 5, filas_est)
check("la estimación traduce filas a MB",
      abs(mb_est - 5 * ex.NO_PICADAS_BYTES_FILA / 1e6) < 1e-6, mb_est)
check("radio inválido no estima nada",
      ex.estimar_no_picadas(["seiscomp"], inicio, fin, 0) == (0, 0.0))
check("el umbral de aviso es positivo", ex.AVISO_NO_PICADAS_MB > 0,
      ex.AVISO_NO_PICADAS_MB)

print("== el inventario puede fallar sin tirar la exportación ==")


def _inventario_roto(base, ini, finn):
    raise RuntimeError("se cayó la base")


ex._consultar_inventario_de_base = _inventario_roto
salida4 = os.path.join(RAIZ, "seiscomp_sin_inv.csv")
r4 = ex.exportar_ventana(inicio, fin, salida4, "todas", True, False)
check("igual exporta los eventos", r4["eventos"] == 2, r4["eventos"])
check("y escribe el archivo de no picadas vacío",
      os.path.isfile(r4["ruta_no_picadas"]) and r4["no_picadas"] == 0, r4)

shutil.rmtree(RAIZ, ignore_errors=True)
print()
if fallos:
    print("FALLARON %d: %s" % (len(fallos), fallos))
    sys.exit(1)
print("Todas las pruebas pasaron.")
