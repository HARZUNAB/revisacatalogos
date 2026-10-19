# -*- coding: utf-8 -*-
"""
Prueba de punta a punta del botón Estaciones, con CSV de prueba.

Arma una exportación sintética (eventos, fases y no picadas), abre el panel,
elige un evento, pulsa Estaciones y mira que las dos solapas tengan lo que
corresponde. También verifica el caso de una exportación vieja, sin el archivo
de no picadas.
"""
import csv
import os
import shutil
import sys
import tempfile
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import revisa_seiscomp as rs
import exporta_ventana_seiscomp as ex

fallos = []


def check(nombre, condicion, detalle=""):
    if condicion:
        print("  OK    %s" % nombre)
    else:
        print("  FALLA %s  -> %s" % (nombre, detalle))
        fallos.append(nombre)


RAIZ = tempfile.mkdtemp(prefix="seiscomp_est_")
DATOS = os.path.join(RAIZ, "datos")
os.makedirs(DATOS)
BASE = os.path.join(DATOS, "seiscomp_20260101000000_20260131235959.csv")

eventos = [
    {"id_evento": "ev1", "id_origen": "or1", "ot_utc": "2026-01-10 05:00:00",
     "magnitud": "4.5",
     "tipo_magnitud": "Mlv", "fases": "12", "rms": "0.8", "azgap": "45",
     "latitud": "-33.100", "longitud": "-70.800", "profundidad_km": "80.0",
     "agencia": "SNC", "operador": "test", "region": "Valparaiso",
     "estatus": "confirmed", "base_datos": "seiscomp"},
    {"id_evento": "ev2", "id_origen": "or2", "ot_utc": "2026-01-11 08:30:00",
     "magnitud": "3.1",
     "tipo_magnitud": "Md", "fases": "5", "rms": "1.0", "azgap": "90",
     "latitud": "-33.500", "longitud": "-71.200", "profundidad_km": "40.0",
     "agencia": "SNC", "operador": "test", "region": "Valparaiso",
     "estatus": "confirmed", "base_datos": "seiscomp"},
]

fases = []
for i, (est, red, cha) in enumerate([("SCL", "CL", "HHZ"), ("LGO", "CL", "HHZ"),
                                     ("PEL", "CL", "HHZ")]):
    # SCL manual y usada, LGO automática y usada, PEL automática y sin usar.
    manual = i == 0
    fases.append({"id_evento": "ev1", "id_origen": "or1", "id_pick": "pk%d" % i,
                  "red": red, "estacion": est, "loc": "", "cha": cha,
                  "fase": "P", "llegada_utc": "2026-01-10 05:00:%02d" % (10 + i),
                  "llegada_us": "0", "correccion_s": "1.2", "residual_s": "0.4",
                  "azimut": str(30 * i + 10), "distancia": "0.3",
                  "usada": "true" if i < 2 else "false", "peso": "1.0",
                  "polaridad": "positive", "snr": "12.5",
                  "modo_pick": "manual" if manual else "automatic",
                  "pick_autor": "mary" if manual else "scautopic@host",
                  "pick_agencia": "CSN",
                  "pick_metodo": "" if manual else "AIC",
                  "mag_estacion": "3.4", "tipo_mag_estacion": "Mlv",
                  "tiene_magnitud": "Si", "mag_est_residuo": "0.1",
                  "qc_estacion": "aprobado", "est_lat": "-33.4",
                  "est_lon": "-70.7", "est_elev": "600", "est_lugar": "Santiago",
                  "est_pais": "Chile", "base_datos": "seiscomp"})
fases.append({"id_evento": "ev2", "id_origen": "or2", "id_pick": "pk9",
              "red": "CL", "estacion": "SCL", "loc": "", "cha": "HHZ",
              "fase": "P", "llegada_utc": "2026-01-11 08:30:10",
              "llegada_us": "0", "correccion_s": "0.8", "residual_s": "0.2",
              "azimut": "5", "distancia": "0.2", "usada": "true", "peso": "1.0",
              "polaridad": "positive", "snr": "8.0",
              "modo_pick": "manual", "pick_autor": "mary", "pick_agencia": "CSN",
              "pick_metodo": "",
              "mag_estacion": "",
              "tipo_mag_estacion": "", "tiene_magnitud": "No",
              "mag_est_residuo": "", "qc_estacion": "sin_evaluar",
              "est_lat": "-33.4", "est_lon": "-70.7", "est_elev": "600",
              "est_lugar": "Santiago", "est_pais": "Chile",
              "base_datos": "seiscomp"})

no_picadas = [
    # ev1: SCL y LGO ya picaron, así que no aparecen. Estas dos sí.
    {"id_evento": "ev1", "id_origen": "or1", "red": "CL", "estacion": "COCA",
     "loc_ref": "", "cha_ref": "BHZ", "streams_vigentes": "1",
     "distancia_km": "21.4",
     "est_lat": "-33.30", "est_lon": "-70.72", "est_elev": "1120",
     "est_lugar": "Cochrane", "est_pais": "Chile", "radio_km": "300.0",
     "actividad_ventana": "3", "waveform_status": "NO_CONSULTADO",
     "availability_source": "", "cobertura_desde": "", "cobertura_hasta": ""},
    {"id_evento": "ev1", "id_origen": "or1", "red": "CL", "estacion": "RANC",
     "loc_ref": "", "cha_ref": "BHZ", "streams_vigentes": "1",
     "distancia_km": "64.8",
     "est_lat": "-33.05", "est_lon": "-71.30", "est_elev": "430",
     "est_lugar": "Rancagua", "est_pais": "Chile", "radio_km": "300.0",
     "actividad_ventana": "0", "waveform_status": "SIN_DATOS",
     "availability_source": "", "cobertura_desde": "", "cobertura_hasta": ""},
    {"id_evento": "ev1", "id_origen": "or1", "red": "CL", "estacion": "LEMA",
     "loc_ref": "10", "cha_ref": "BHN", "streams_vigentes": "2",
     "distancia_km": "18.0",
     "est_lat": "-33.26", "est_lon": "-70.90", "est_elev": "880",
     "est_lugar": "Lema", "est_pais": "Chile", "radio_km": "300.0",
     "actividad_ventana": "1", "waveform_status": "NO_CONSULTADO",
     "availability_source": "", "cobertura_desde": "", "cobertura_hasta": ""},
    # ev2 solo tiene a SCL picada.
    {"id_evento": "ev2", "id_origen": "or2", "red": "CL", "estacion": "COCA",
     "loc_ref": "", "cha_ref": "BHZ", "streams_vigentes": "1",
     "distancia_km": "95.0",
     "est_lat": "-33.30", "est_lon": "-70.72", "est_elev": "1120",
     "est_lugar": "Cochrane", "est_pais": "Chile", "radio_km": "300.0",
     "actividad_ventana": "0", "waveform_status": "NO_CONSULTADO",
     "availability_source": "", "cobertura_desde": "", "cobertura_hasta": ""},
]


def escribir(ruta, filas, cabecera):
    with open(ruta, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cabecera)
        w.writeheader()
        for fila in filas:
            w.writerow({c: fila.get(c, "") for c in cabecera})


escribir(BASE, eventos, ex.CABECERA)
escribir(BASE[:-4] + "_fases.csv", fases, ex.CABECERA_FASES)
escribir(BASE[:-4] + "_no_picadas.csv", no_picadas, ex.CABECERA_NO_PICADAS)

print("== funciones puras de la interfaz ==")
filas_np = rs._leer_fases_de_evento(BASE[:-4] + "_no_picadas.csv",
                                   *rs._indexar_fases(
                                       BASE[:-4] + "_no_picadas.csv")[:2],
                                   "ev1")
check("el índice por bytes trae solo las de ev1", len(filas_np) == 3,
      [f["estacion"] for f in filas_np])
check("el id es la primera columna y se puede leer",
      all(f["id_evento"] == "ev1" for f in filas_np))
check("las no picadas de ev1 son las tres esperadas",
      [f["estacion"] for f in filas_np] == ["COCA", "RANC", "LEMA"],
      [f["estacion"] for f in filas_np])

valores = rs._valores_no_picada(filas_np[0])
check("las columnas coinciden con las declaradas",
      len(valores) == len(rs.COLUMNAS_NO_PICADA), valores)
check("la distancia sale con un decimal", valores[0] == "21.4", valores[0])
check("la red y la estación se leen", valores[1:3] == ["CL", "COCA"], valores)
check("el loc_ref y el canal_ref se leen",
      valores[3:5] == ["—", "BHZ"], valores)
check("los streams vigentes se muestran enteros", valores[5] == "1", valores[5])
check("la evidencia distingue el indicio de la certeza",
      valores[6] == "Indicio (actividad)", valores[6])
check("las formas de onda sin consultar quedan vacías",
      valores[7] == "—", valores[7])
check("la actividad inferida se muestra entera", valores[8] == "3", valores[8])

check("actividad y cerca va como indicio",
      rs._etiqueta_no_picada({"distancia_km": "18.0",
                              "actividad_ventana": "1"}) == "indicio")
check("actividad y lejos va como indicio lejano",
      rs._etiqueta_no_picada({"distancia_km": "64.8",
                              "actividad_ventana": "2"}) == "indicio_lejos")
check("cerca, sin consultar y sin actividad no se destaca",
      rs._etiqueta_no_picada({"distancia_km": "20.0",
                              "actividad_ventana": "0"}) == "normal")
check("cerca, sin ondas y sin actividad va como sin evidencia",
      rs._etiqueta_no_picada({"distancia_km": "20.0",
                              "actividad_ventana": "0",
                              "waveform_status": "SIN_DATOS"}) ==
      "sin_evidencia")
check("lejos e inactiva va como normal",
      rs._etiqueta_no_picada({"distancia_km": "250.0",
                              "actividad_ventana": "0"}) == "normal")
check("sin dato de actividad no revienta",
      rs._etiqueta_no_picada({"distancia_km": "10.0"}) == "normal")
check("sin dato de distancia no revienta",
      rs._etiqueta_no_picada({"actividad_ventana": "0"}) == "normal")
# El umbral de "cerca" es configurable: la misma fila cambia de categoría.
check("un umbral de cerca mayor reclasifica una lejana",
      rs._etiqueta_no_picada({"distancia_km": "64.8", "actividad_ventana": "2"},
                             umbral_cercano=70.0) == "indicio")
check("un umbral de cerca menor saca de cerca a una intermedia",
      rs._etiqueta_no_picada({"distancia_km": "64.8", "actividad_ventana": "2"},
                             umbral_cercano=30.0) == "indicio_lejos")
check("el umbral también mueve el caso activo",
      rs._etiqueta_no_picada({"distancia_km": "18.0", "actividad_ventana": "2"},
                             umbral_cercano=10.0) == "indicio_lejos")

# Análisis rápido: resumen de sin arribos cercanas por evento.
analisis50 = rs.analizar_sin_arribos(BASE[:-4] + "_no_picadas.csv", eventos,
                                     50.0)
check("el análisis a 50 km deja solo ev1 (ev2 no tiene cercanas)",
      [r["evento"]["id_evento"] for r in analisis50] == ["ev1"],
      [r["evento"]["id_evento"] for r in analisis50])
check("ev1 a 50 km: 2 indicios (COCA y LEMA) y 0 sin evidencia",
      analisis50[0]["verificadas"] == 0
      and analisis50[0]["indicios"] == 2
      and analisis50[0]["sin_evidencia"] == 0,
      analisis50[0])
check("la distancia mínima es 18.0 km (LEMA)",
      abs(analisis50[0]["dist_min"] - 18.0) < 0.01, analisis50[0]["dist_min"])
check("el total de sin arribos del evento se conserva",
      analisis50[0]["total"] == 3, analisis50[0]["total"])
analisis100 = rs.analizar_sin_arribos(BASE[:-4] + "_no_picadas.csv", eventos,
                                      100.0)
check("con umbral 100 entran ev1 y ev2",
      {r["evento"]["id_evento"] for r in analisis100} == {"ev1", "ev2"},
      [r["evento"]["id_evento"] for r in analisis100])
check("ev1 con umbral 100 suma RANC como sin evidencia",
      analisis100[0]["evento"]["id_evento"] == "ev1"
      and analisis100[0]["sin_evidencia"] == 1, analisis100[0])
valores_analisis = rs._valores_analisis(analisis50[0])
check("la fila del análisis trae el operador", valores_analisis[7] == "test",
      valores_analisis)
largas = rs.filas_analisis_largo(analisis100)
check("la descarga larga trae una fila por evento+estación",
      len(largas) == 4, len(largas))
clasificaciones = {f["clasificacion"] for f in largas}
check("la descarga larga marca la clasificación",
      clasificaciones <= {"verificado", "indicio", "sin evidencia",
                          "sin consultar"}
      and "indicio" in clasificaciones,
      clasificaciones)

# Orden del análisis por columna.
def _ids(resumenes):
    return [r["evento"]["id_evento"] for r in resumenes]

check("_ordenar_analisis por distancia ascendente",
      _ids(rs._ordenar_analisis(analisis100, "dist_min", False))
      == ["ev1", "ev2"])
check("_ordenar_analisis por distancia descendente",
      _ids(rs._ordenar_analisis(analisis100, "dist_min", True))
      == ["ev2", "ev1"])
check("_ordenar_analisis por fases ascendente",
      _ids(rs._ordenar_analisis(analisis100, "fases", False))
      == ["ev2", "ev1"])
check("_ordenar_analisis sin columna vuelve a la severidad",
      _ids(rs._ordenar_analisis(analisis100, None)) == _ids(analisis100))
sinteticos = [
    {"evento": {"id_evento": "a", "magnitud": "3.0", "fases": "2"},
     "destacadas": 0, "cercanas": 1, "dist_min": 5.0, "estaciones": []},
    {"evento": {"id_evento": "b"}, "destacadas": 0, "cercanas": 1,
     "dist_min": 9.0, "estaciones": []},
]
check("lo que no tiene dato va al final (ascendente)",
      _ids(rs._ordenar_analisis(sinteticos, "magnitud", False)) == ["a", "b"])
check("lo que no tiene dato va al final (descendente)",
      _ids(rs._ordenar_analisis(sinteticos, "magnitud", True)) == ["a", "b"])

# Modo del pick (manual/automática).
check("_texto_modo traduce manual", rs._texto_modo("manual") == "manual")
check("_texto_modo traduce automatic", rs._texto_modo("automatic") == "automática")
check("_texto_modo vacío da guion", rs._texto_modo("") == rs.VACIO)
check("_desglose_uso sin modo cae al texto clásico",
      rs._desglose_uso({"con_modo": 0, "usadas": 2, "no_usadas": 1})
      == "2 usadas, 1 sin usar")
res_ev1 = rs._resumen_fases([f for f in fases if f["id_evento"] == "ev1"])
check("_resumen_fases cuenta usadas manuales",
      res_ev1["usadas_manual"] == 1, res_ev1)
check("_resumen_fases cuenta usadas automáticas",
      res_ev1["usadas_auto"] == 1, res_ev1)
check("_resumen_fases cuenta sin usar automáticas",
      res_ev1["sin_usar_auto"] == 1, res_ev1)
desglose = rs._desglose_uso(res_ev1)
check("_desglose_uso desglosa por modo",
      "1 manual" in desglose and "1 automática" in desglose, desglose)
valores_fase = rs._valores_fase(fases[0])
check("_valores_fase trae modo, autor, método y agencia",
      valores_fase[8] == "manual" and valores_fase[9] == "mary"
      and valores_fase[10] == rs.VACIO and valores_fase[11] == "CSN",
      valores_fase)
# Exportación vieja: sin la columna modo, no debe inventar un desglose.
viejo_est = rs._encabezado_estacion("CL X", [{"usada": "true"},
                                              {"usada": "false"}])
check("encabezado de estación viejo usa el texto clásico",
      "sin usar" in viejo_est and "manual" not in viejo_est, viejo_est)

check("_ruta_no_picadas deriva bien",
      rs._ruta_no_picadas("/x/seiscomp_a.csv") == "/x/seiscomp_a_no_picadas.csv")

# Línea de parámetros del evento para el encabezado de Estaciones.
param_linea = rs._parametros_evento_en_linea(eventos[0])
check("la línea de parámetros trae mag, región y agencia",
      "M4.5 Mlv" in param_linea and "Valparaiso" in param_linea
      and "Agencia SNC" in param_linea, param_linea)
check("el analista sale del operador",
      rs._analista_del_evento(eventos[0]) == "test",
      rs._analista_del_evento(eventos[0]))
check("la línea tolera campos faltantes",
      rs._parametros_evento_en_linea({}) == "",
      rs._parametros_evento_en_linea({}))

# Comparación: el publicado guarda lat/lon a 2 decimales, se tolera 0.005°.
import comparacion as comp
check("coordenadas iguales dentro de la media centésima",
      comp.mismo_coordenada("-34.580", "-34.575") is True)
check("coordenadas distintas más allá de la media centésima",
      comp.mismo_coordenada("-34.580", "-34.574") is False)
check("profundidad sigue exacta a 1 decimal",
      comp.misma_profundidad("25.9", "26.0") is False)
check("magnitud sigue exacta a 1 decimal",
      comp.mismo_magnitud("2.8", "2.9") is False)
check("distancia_km calcula el caso del ejemplo",
      abs(comp.distancia_km("-34.575", "-72.292", "-34.58", "-72.29")
          - 0.585) < 0.05)

# No actualizados: tolerancia de coordenadas + columna dist_km.
base_noact = tempfile.mkdtemp(prefix="noact_")
os.makedirs(os.path.join(base_noact, "datos"))
with open(os.path.join(base_noact, "datos", "atribucion_seiscomp.csv"), "w",
          newline="") as f:
    f.write("fecha_eventquery,lat_eventquery,lon_eventquery,prof_eventquery,"
            "mag_eventquery,fecha_local,lat_local,lon_local,prof_local,"
            "mag_local,analista,dt_seg,dlat,dlon\n")
    # Solo el redondeo del publicado (2 dec): NO debe marcarse.
    f.write("e1,-34.58,-72.29,25.9,2.8,l1,-34.575,-72.292,25.9,2.8,jaba,"
            "0.0,0.005,0.002\n")
    # Diferencia real de magnitud: SÍ debe marcarse.
    f.write("e2,-30.55,-71.25,47.0,4.4,l2,-30.550,-71.250,47.0,4.6,mdur,"
            "0.0,0.0,0.0\n")
filas_noact = rs._no_actualizados("seiscomp", cwd=base_noact)
check("solo queda el que difiere de verdad (mag)",
      len(filas_noact) == 1 and filas_noact[0]["mag_local"] == "4.6",
      filas_noact)
check("el no actualizado trae dist_km calculado (fallback)",
      abs(float(filas_noact[0]["dist_km"])) < 1.0,
      filas_noact[0].get("dist_km"))
check("la tabla de No actualizados trae la columna Dist (km)",
      any(c == "dist_km" for c, _, _ in rs.COLUMNAS_NO_ACTUALIZADO))
shutil.rmtree(base_noact, ignore_errors=True)

# Ploteo de un evento suelto y comparación local vs publicado.
import plotear as pl
import asigna_perfiles as ap
import sismicidad as sismo
_llamados = []
_orig = (pl.plotear_perfil, pl.plotear_planta, ap.asignar_perfil_evento,
         sismo.es_sospechoso)
pl.plotear_perfil = lambda evs, perf, *a, **k: _llamados.append(
    ("perfil", perf["id"], len(evs), k.get("titulo"), k.get("subtitulo")))
pl.plotear_planta = lambda evs, *a, **k: _llamados.append(("planta", len(evs)))
sismo.es_sospechoso = lambda ev, *a, **k: False
perfil_falso = {"id": "P001", "lat_media": -33.0, "slab": {"p": [], "depth": []},
                "topo_p": [], "topo_alt": []}
try:
    pl.abrir_evento({"fecha hora": "", "latitud": -33.3, "longitud": -70.6,
                     "prof": 90.0, "perfil": "P001", "along_km": 100.0,
                     "magnitud": "2.6", "tipo": "ML", "analista": "x"},
                    "seisan", perfiles=[perfil_falso])
    check("abrir_evento con perfil llama a plotear_perfil",
          _llamados[-1][:3] == ("perfil", "P001", 1)
          and _llamados[-1][3] is None, _llamados)
    # Comparación de la solución contra lo publicado: mismo perfil (el de la
    # solución) y título.
    _llamados.clear()
    pl.abrir_eventos([
        {"rol": "local", "fecha hora": "2026-01-01 00:00:00", "latitud": -33.3,
         "longitud": -70.6, "prof": 90.0, "perfil": "P001", "along_km": 100.0},
        {"rol": "publicado", "fecha hora": "2026-01-01 00:00:00",
         "latitud": -33.35, "longitud": -70.65, "prof": 88.0}], "seisan",
        perfiles=[perfil_falso])
    check("abrir_eventos con local+publicado llama a plotear_perfil",
          _llamados and _llamados[-1][0] == "perfil" and _llamados[-1][2] == 2,
          _llamados)
    check("la comparación titula con la fuente de la solución",
          _llamados[-1][3] == "Comparación Seisan vs publicado"
          and _llamados[-1][4] and "Seisan" in _llamados[-1][4], _llamados)
    ap.asignar_perfil_evento = lambda *a, **k: {
        "perfil": None, "along_km": None, "perp_km": None, "residuo_km": None,
        "dist_asoc": None, "motivo": "fuera_cobertura"}
    _llamados.clear()
    pl.abrir_evento({"fecha hora": "", "latitud": 0.0, "longitud": 0.0,
                     "prof": 10.0, "magnitud": "", "tipo": "", "analista": ""},
                    "seisan", perfiles=[perfil_falso])
    check("abrir_evento fuera de cobertura llama a plotear_planta",
          _llamados[-1][0] == "planta", _llamados)
finally:
    (pl.plotear_perfil, pl.plotear_planta, ap.asignar_perfil_evento,
     sismo.es_sospechoso) = _orig

print("== búsqueda de pares ==")
raiz_pares = tempfile.mkdtemp(prefix="seiscomp_pares_")
os.makedirs(os.path.join(raiz_pares, "datos"))
for nombre in ("seiscomp_20260101000000_20260131235959.csv",
               "seiscomp_20260101000000_20260131235959_fases.csv",
               "seiscomp_20260101000000_20260131235959_no_picadas.csv"):
    open(os.path.join(raiz_pares, "datos", nombre), "w").close()
pares = rs._pares_disponibles(raiz_pares)
check("los derivados no aparecen como pares sueltos", len(pares) == 1,
      [os.path.basename(p["eventos"]) for p in pares])
check("el par trae la ruta de no picadas",
      pares[0]["no_picadas"].endswith("_no_picadas.csv"), pares[0])
# Una ventana vieja, sin el archivo de no picadas.
for nombre in ("seiscomp_20260201000000_20260228235959.csv",
               "seiscomp_20260201000000_20260228235959_fases.csv"):
    open(os.path.join(raiz_pares, "datos", nombre), "w").close()
pares = rs._pares_disponibles(raiz_pares)
viejo = [p for p in pares if "20260201" in p["eventos"]][0]
check("una ventana vieja trae no_picadas en None", viejo["no_picadas"] is None,
      viejo)

print("== ventana de estaciones con ttkbootstrap ==")
try:
    import ttkbootstrap as tb
    raiz = tb.Window(themename="flatly")
except Exception as e:
    print("  (salteado: no hay pantalla, %s)" % e)
    raiz = None

if raiz is not None:
    # La app oculta la tira de pestañas del cuaderno PRINCIPAL con un estilo
    # propio ("Principal.TNotebook") para no afectar a otros cuadernos. Si se
    # anulara "TNotebook.Tab", la ventana de Estaciones se quedaría sin
    # pestañas. Se simula aquí y se comprueba que "TNotebook.Tab" sobrevive.
    estilo_raiz = tb.Style.get_instance()
    estilo_raiz.layout("Principal.TNotebook.Tab", [])
    check("ocultar pestañas del cuaderno principal no afecta al resto",
          bool(estilo_raiz.layout("TNotebook.Tab")),
          estilo_raiz.layout("TNotebook.Tab"))

    marco = tb.Frame(raiz)
    marco.pack(fill="both", expand=True)
    registros = []
    ok = rs.abrir_panel(marco, BASE, BASE[:-4] + "_fases.csv",
                        BASE[:-4] + "_no_picadas.csv",
                        etiqueta_fuente="seiscomp", log=registros.append,
                        cwd=RAIZ)
    check("el panel abre con los tres archivos", ok is True)

    def _primer_arbol(widget):
        for hijo in widget.winfo_children():
            if isinstance(hijo, tb.Treeview):
                return hijo
            encontrado = _primer_arbol(hijo)
            if encontrado is not None:
                return encontrado
        return None

    arbol_ev = _primer_arbol(marco)
    check("la lista de eventos trae los dos",
          arbol_ev is not None and len(arbol_ev.get_children()) == 2,
          arbol_ev.get_children() if arbol_ev is not None else None)

    # El árbol de llegadas NO debe estar embebido en el detalle.
    def _todos(w):
        for hijo in w.winfo_children():
            yield hijo
            for x in _todos(hijo):
                yield x

    def _etiquetas(w):
        for hijo in w.winfo_children():
            if type(hijo).__name__ == "Label":
                yield hijo
            for x in _etiquetas(hijo):
                yield x

    def _arboles(w):
        encontrados = []
        for hijo in w.winfo_children():
            if isinstance(hijo, tb.Treeview):
                encontrados.append(hijo)
            encontrados.extend(_arboles(hijo))
        return encontrados

    def _toplevels(w):
        encontrados = []
        for hijo in w.winfo_children():
            if isinstance(hijo, tb.Toplevel):
                encontrados.append(hijo)
            encontrados.extend(_toplevels(hijo))
        return encontrados

    def _por_titulo(fragmento):
        return [w for w in _toplevels(raiz) if fragmento in w.title()]

    def _esperar(condicion, segundos=5.0):
        """Bombea el loop de Tk hasta que 'condicion()' sea verdadera.

        La consulta a la base ahora corre en un hilo: el resultado vuelve por
        una cola que atiende el loop principal, así que desde un script hay que
        esperar a que ese ciclo lo procese antes de restaurar los parches.
        """
        tope = time.time() + segundos
        while time.time() < tope:
            raiz.update()
            if condicion():
                return True
            time.sleep(0.02)
        return condicion()

    def _botones(w):
        # ttkbootstrap.Button no es una clase: es la función que crea el
        # widget, así que isinstance no sirve. Se pregunta por el nombre.
        for hijo in w.winfo_children():
            if type(hijo).__name__ == "Button":
                yield hijo
            for x in _botones(hijo):
                yield x

    def _progressbars(w):
        for hijo in w.winfo_children():
            if type(hijo).__name__ == "Progressbar":
                yield hijo
            for x in _progressbars(hijo):
                yield x

    def _abrir_detalle(arbol):
        # El detalle ahora abre con doble clic o con Enter sobre la fila. Desde
        # un script no se puede generar un doble clic, así que se usa Enter;
        # para las teclas hace falta que la ventana del árbol tenga el foco real
        # y esté mapeada, por eso se dan unos updates con una pequeña espera.
        toplevel = arbol.winfo_toplevel()
        for _ in range(4):
            toplevel.update()
            time.sleep(0.05)
        toplevel.focus_force()
        arbol.focus_set()
        toplevel.update()
        arbol.event_generate("<Return>", when="now")
        toplevel.update()
        raiz.update()

    check("la lista de eventos es el único árbol del panel",
          len(_arboles(marco)) == 1, len(_arboles(marco)))

    # Un clic simple (<<TreeviewSelect>>) ya NO abre el detalle: abre el doble.
    check("el clic simple no abre el detalle",
          not any("Parámetros del evento" in w.title()
                  for w in _toplevels(raiz)),
          [w.title() for w in _toplevels(raiz)])
    check("el detalle queda atado al doble clic",
          arbol_ev.bind("<Double-1>") != "", arbol_ev.bind("<Double-1>"))
    check("y a la tecla Enter",
          arbol_ev.bind("<Return>") != "", arbol_ev.bind("<Return>"))

    # Elegir el primer evento: el detalle abre en su propia ventana.
    arbol_ev.selection_set(arbol_ev.get_children()[0])
    _abrir_detalle(arbol_ev)
    parametros = _por_titulo("Parámetros del evento")
    check("el clic en la fila abre la ventana de parámetros",
          len(parametros) == 1,
          [w.title() for w in _toplevels(raiz)])
    check("el título de parámetros trae el id del evento",
          parametros and "ev1" in parametros[0].title(),
          parametros and parametros[0].title())
    ventana_param = parametros[0]
    check("la ventana de parámetros no captura la entrada (no modal)",
          ventana_param.grab_current() is None,
          ventana_param.grab_current())
    check("el panel ya no embebe el detalle",
          len(_arboles(marco)) == 1, len(_arboles(marco)))
    textos_param = [str(w.cget("text")) for w in _etiquetas(ventana_param)]
    check("la ventana de parámetros trae los datos del evento",
          any(x == "latitud:" for x in textos_param), textos_param[:14])

    # El botón Estaciones vive dentro de la ventana de parámetros.
    boton = [b for b in _botones(ventana_param)
             if str(b.cget("text")) == "Estaciones"][0]
    boton.invoke()
    raiz.update()

    estaciones = _por_titulo("Estaciones del evento")
    check("el botón Estaciones abre su ventana", len(estaciones) == 1,
          [w.title() for w in _toplevels(raiz)])
    ventana = estaciones[0]
    check("la ventana de estaciones no captura la entrada (no modal)",
          ventana.grab_current() is None, ventana.grab_current())
    check("el título es el de estaciones del evento",
          "Estaciones del evento" in ventana.title(), ventana.title())
    check("el título trae el id del evento", "ev1" in ventana.title(),
          ventana.title())

    cuadernos = [w for w in _todos(ventana)
                 if type(w).__name__ == "Notebook"]
    check("hay un cuaderno con dos solapas",
          len(cuadernos) == 1 and len(cuadernos[0].tabs()) == 2,
          [c.tabs() for c in cuadernos])
    cuaderno = cuadernos[0]
    titulos = [str(cuaderno.tab(t, "text")) for t in cuaderno.tabs()]
    check("las solapas son Con arribos y Sin arribos",
          titulos == ["Con arribos", "Sin arribos"], titulos)

    arboles_ventana = _arboles(ventana)
    check("la ventana tiene dos tablas", len(arboles_ventana) == 2,
          len(arboles_ventana))
    tabla_picadas, tabla_no_picadas = arboles_ventana[0], arboles_ventana[1]
    # La de picadas va agrupada: 3 estaciones para ev1.
    check("la solapa de arribos trae las 3 estaciones de ev1",
          len(tabla_picadas.get_children()) == 3,
          len(tabla_picadas.get_children()))
    check("la solapa de sin arribos trae 3 estaciones planas",
          len(tabla_no_picadas.get_children()) == 3,
          len(tabla_no_picadas.get_children()))
    primero = tabla_no_picadas.item(tabla_no_picadas.get_children()[0], "values")
    check("la tabla de sin arribos está ordenada por distancia",
          primero[0] == "18.0", primero)
    colores = {tabla_no_picadas.item(i, "tags")[0]
               for i in tabla_no_picadas.get_children()}
    check("se usan las etiquetas de color", "indicio" in colores, colores)

    # Las tablas se desplazan con sus barras: antes el árbol, empaquetado con
    # expand=True antes que ellas, las dejaba en 1x1 px (invisibles).
    def _barra_h_de(tabla):
        for h in tabla.master.winfo_children():
            if (type(h).__name__ == "Scrollbar"
                    and str(h.cget("orient")) == "horizontal"):
                return h
        return None

    raiz.update()
    barra_h_picadas = _barra_h_de(tabla_picadas)
    check("la tabla de arribos tiene barra horizontal visible",
          barra_h_picadas is not None and barra_h_picadas.winfo_height() > 1,
          barra_h_picadas and (barra_h_picadas.winfo_width(),
                               barra_h_picadas.winfo_height()))
    cuaderno.select(cuaderno.tabs()[1])
    raiz.update()
    barra_h_np = _barra_h_de(tabla_no_picadas)
    check("la tabla de sin arribos tiene barra horizontal visible",
          barra_h_np is not None and barra_h_np.winfo_height() > 1,
          barra_h_np and (barra_h_np.winfo_width(), barra_h_np.winfo_height()))
    check("la ventana no supera el ancho de referencia (1920)",
          0 < ventana.winfo_width() <= rs.ajuste.TOPE_MAXIMO[0],
          ventana.winfo_width())

    # --- Análisis rápido: botón sobre la lista, ventana con dos pestañas ---
    botones_panel = list(_botones(marco))
    analisis_boton = [b for b in botones_panel
                      if str(b.cget("text")) == "Análisis rápido"]
    check("el botón Análisis rápido está en el panel", len(analisis_boton) == 1,
          [str(b.cget("text")) for b in botones_panel])
    analisis_boton[0].invoke()
    raiz.update()
    ventanas_an = _por_titulo("Análisis rápido")
    check("Análisis rápido abre su ventana", len(ventanas_an) == 1,
          [w.title() for w in _toplevels(raiz)])
    ventana_an = ventanas_an[0]
    cuadernos_an = [w for w in _todos(ventana_an)
                    if type(w).__name__ == "Notebook"]
    check("la ventana de análisis tiene un cuaderno con dos pestañas",
          len(cuadernos_an) == 1 and len(cuadernos_an[0].tabs()) == 2,
          [c.tabs() for c in cuadernos_an])
    titulos_an = [str(cuadernos_an[0].tab(t, "text"))
                  for t in cuadernos_an[0].tabs()]
    check("las pestañas son Contexto y Resultados",
          titulos_an == ["Contexto", "Resultados"], titulos_an)
    arbol_an = _arboles(ventana_an)[0]
    check("el análisis a 50 km lista solo ev1",
          len(arbol_an.get_children()) == 1
          and arbol_an.item(arbol_an.get_children()[0], "values")[2] == "ev1",
          [arbol_an.item(i, "values") for i in arbol_an.get_children()])
    check("la lista del análisis trae el operador",
          arbol_an.item(arbol_an.get_children()[0], "values")[7] == "test",
          arbol_an.item(arbol_an.get_children()[0], "values"))
    # El umbral es configurable y recalcula en el acto.
    entradas_an = [w for w in _todos(ventana_an)
                   if type(w).__name__ == "Entry"]
    botones_an = {str(b.cget("text")): b for b in _botones(ventana_an)}
    entradas_an[0].delete(0, "end")
    entradas_an[0].insert(0, "100")
    botones_an["Recalcular"].invoke()
    raiz.update()
    arbol_an = _arboles(ventana_an)[0]
    check("con umbral 100 el análisis lista ev1 y ev2",
          len(arbol_an.get_children()) == 2,
          [arbol_an.item(i, "values") for i in arbol_an.get_children()])

    # Orden por clic: ciclo ascendente → descendente → por defecto (severidad).
    def _click_encabezado(tabla, columna):
        comando = tabla.heading(columna, "command")
        tabla.tk.call(comando, columna)
        raiz.update()

    def _primer_id(tabla):
        return tabla.item(tabla.get_children()[0], "values")[2]

    _click_encabezado(arbol_an, "fases")
    arbol_an = _arboles(ventana_an)[0]
    check("el 1er clic ordena por Fases ascendente",
          _primer_id(arbol_an) == "ev2"
          and "▲" in str(arbol_an.heading("fases", "text")),
          (arbol_an.heading("fases", "text"), _primer_id(arbol_an)))
    _click_encabezado(arbol_an, "fases")
    arbol_an = _arboles(ventana_an)[0]
    check("el 2do clic invierte a descendente",
          _primer_id(arbol_an) == "ev1"
          and "▼" in str(arbol_an.heading("fases", "text")),
          (arbol_an.heading("fases", "text"), _primer_id(arbol_an)))
    _click_encabezado(arbol_an, "fases")
    arbol_an = _arboles(ventana_an)[0]
    check("el 3er clic vuelve al orden por severidad (sin flecha)",
          _primer_id(arbol_an) == "ev1"
          and arbol_an.heading("fases", "text") == "Fases",
          (arbol_an.heading("fases", "text"), _primer_id(arbol_an)))

    # Doble clic (Enter) abre los parámetros del evento.
    arbol_an.selection_set(arbol_an.get_children()[0])
    _abrir_detalle(arbol_an)
    parametros_an = _por_titulo("Parámetros del evento")
    check("el doble clic del análisis abre los parámetros",
          len(parametros_an) == 1 and "ev1" in parametros_an[0].title(),
          [w.title() for w in _toplevels(raiz)])
    # Descarga larga (se evita el diálogo de nombre/formato).
    descarga_original = rs.descargas.preguntar_descarga
    rs.descargas.preguntar_descarga = lambda *a, **k: ("csv", None, False)
    try:
        botones_an["Descargar"].invoke()
        raiz.update()
    finally:
        rs.descargas.preguntar_descarga = descarga_original
    carpeta_desc = os.path.join(RAIZ, "descargas")
    archivos_an = ([n for n in os.listdir(carpeta_desc)
                    if n.startswith("analisis_")]
                   if os.path.isdir(carpeta_desc) else [])
    check("la descarga del análisis escribe el CSV largo", bool(archivos_an),
          archivos_an)

    # La ayuda fija tiene que estar visible, no solo en el tooltip.
    textos_ayuda = [str(w.cget("text")) for w in _etiquetas(ventana)]
    check("está la ayuda de que sin arribos no es no grabó",
          any("demuestra ausencia de formas de onda" in x
              for x in textos_ayuda), textos_ayuda)
    check("la columna se llama Indicio ±2 h",
          any(t == "Indicio ±2 h" for _, t, _ in rs.COLUMNAS_NO_PICADA),
          rs.COLUMNAS_NO_PICADA)
    check("la ayuda menciona el tooltip por estación",
          any("Pase el mouse por una estación" in x for x in textos_ayuda),
          textos_ayuda)
    check("la tabla de sin arribos tiene tooltip por fila",
          bool(tabla_no_picadas.bind("<Motion>")),
          tabla_no_picadas.bind("<Motion>"))
    barras = list(_progressbars(ventana))
    check("la tabla de sin arribos tiene barra de progreso",
          len(barras) >= 1, len(barras))
    check("la barra de progreso está oculta en reposo",
          all(not b.winfo_manager() for b in barras),
          [b.winfo_manager() for b in barras])
    boton_formas = [b for b in _botones(ventana)
                    if "Consultar formas de onda" in str(b.cget("text"))]
    check("el botón de formas de onda está habilitado en reposo",
          bool(boton_formas)
          and str(boton_formas[0].cget("state")) != "disabled",
          [str(b.cget("state")) for b in boton_formas])

    # Modo del pick en la tabla de arribos.
    columnas = tabla_picadas["columns"]
    check("la tabla de arribos trae Modo y Autor pick",
          "modo" in columnas and "pick_autor" in columnas, columnas)
    etiquetas_fases = []
    for nodo in tabla_picadas.get_children():
        for fila in tabla_picadas.get_children(nodo):
            etiquetas_fases.extend(tabla_picadas.item(fila, "tags"))
    check("el pick manual usado se resalta",
          "manual_usada" in etiquetas_fases, set(etiquetas_fases))
    textos_ventana = [str(w.cget("text")) for w in _etiquetas(ventana)]
    check("el encabezado de la ventana desglosa por modo",
          any("1 manual" in x and "1 automática" in x for x in textos_ventana),
          textos_ventana)
    check("el encabezado de Estaciones muestra el analista del evento",
          any(x == "Analista: test" for x in textos_ventana), textos_ventana)
    check("el encabezado de Estaciones muestra los parámetros del evento",
          any("M4.5 Mlv" in x and "Valparaiso" in x for x in textos_ventana),
          textos_ventana)
    encabezados_est = [str(tabla_picadas.item(n, "text"))
                       for n in tabla_picadas.get_children()]
    check("el encabezado de estación desglosa por modo",
          any("usadas 1 (1 manual" in x for x in encabezados_est),
          encabezados_est)

    # Controles de distancia, en el encabezado de la ventana Estaciones.
    marco_np = cuaderno.nametowidget(cuaderno.tabs()[1])
    entradas_win = [w for w in _todos(ventana)
                    if type(w).__name__ == "Entry"]
    botones_win = [str(b.cget("text")) for b in _botones(ventana)]
    etiquetas_win = [str(w.cget("text")) for w in _etiquetas(ventana)]
    checkbuttons_win = [str(w.cget("text")) for w in _todos(ventana)
                        if type(w).__name__ == "Checkbutton"]
    check("los controles de distancia están en el encabezado",
          len(entradas_win) == 2
          and "Radio a mostrar (km):" in etiquetas_win
          and "Resaltar cerca ≤ (km):" in etiquetas_win
          and "Solo cercanas" in checkbuttons_win
          and "Sin límite" in checkbuttons_win
          and "Aplicar radio" in botones_win
          and "Ampliar (consulta a la base)" not in botones_win
          and "Todo (sin límite)" not in botones_win, botones_win)
    entrada_radio = entradas_win[0]
    entrada_cerca = entradas_win[1]
    boton_aplicar = [b for b in _botones(ventana)
                     if str(b.cget("text")) == "Aplicar radio"][0]
    chk_solo = [w for w in _todos(ventana)
                if type(w).__name__ == "Checkbutton"
                and str(w.cget("text")) == "Solo cercanas"][0]
    chk_limite = [w for w in _todos(ventana)
                  if type(w).__name__ == "Checkbutton"
                  and str(w.cget("text")) == "Sin límite"][0]
    # Aplicar a 20 km deja solo LEMA (18.0): COCA 21.4 y RANC 64.8 quedan fuera.
    entrada_radio.delete(0, "end")
    entrada_radio.insert(0, "20")
    boton_aplicar.invoke()
    raiz.update()
    tabla_np = _arboles(marco_np)[0]
    check("aplicar a 20 km deja 1 sola estación",
          len(tabla_np.get_children()) == 1,
          [tabla_np.item(i, "values") for i in tabla_np.get_children()])
    # El estado aclara cuántas se muestran y cuántas quedan resaltadas.
    textos_estado = [str(w.cget("text")) for w in _etiquetas(ventana)]
    check("el estado informa lo mostrado y lo resaltado",
          any("Mostrando 1 de 3" in x and "resaltadas como cerca" in x
              for x in textos_estado), textos_estado)

    # El umbral «cerca» recolorea sin cambiar la lista.
    def _tag_de(tabla, estacion):
        for i in tabla.get_children():
            if tabla.item(i, "values")[2] == estacion:
                return tabla.item(i, "tags")[0]
        return None

    entrada_radio.delete(0, "end")
    entrada_radio.insert(0, "100")
    entrada_cerca.delete(0, "end")
    entrada_cerca.insert(0, "30")
    boton_aplicar.invoke()
    raiz.update()
    tabla_np = _arboles(marco_np)[0]
    check("con cerca=30 km, RANC (64.8) queda normal",
          _tag_de(tabla_np, "RANC") == "normal", _tag_de(tabla_np, "RANC"))
    entrada_cerca.delete(0, "end")
    entrada_cerca.insert(0, "70")
    boton_aplicar.invoke()
    raiz.update()
    tabla_np = _arboles(marco_np)[0]
    check("subir cerca a 70 km reclasifica RANC como sin evidencia",
          _tag_de(tabla_np, "RANC") == "sin_evidencia",
          _tag_de(tabla_np, "RANC"))
    check("la lista no cambió al recolorear",
          len(tabla_np.get_children()) == 3,
          len(tabla_np.get_children()))
    # El retinte en vivo repinta sin reconstruir (no cambia la cantidad).
    rs._retintar_no_picadas(tabla_np, 10.0)
    raiz.update()
    check("el retinte en vivo repinta sin rehacer la tabla",
          _tag_de(tabla_np, "COCA") == "indicio_lejos"
          and len(tabla_np.get_children()) == 3,
          (_tag_de(tabla_np, "COCA"), len(tabla_np.get_children())))
    # «Solo cercanas» recorta la lista al umbral cerca.
    entrada_cerca.delete(0, "end")
    entrada_cerca.insert(0, "50")
    chk_solo.invoke()
    raiz.update()
    tabla_np = _arboles(marco_np)[0]
    check("«Solo cercanas» deja solo las de ≤ 50 km (COCA y LEMA)",
          sorted(tabla_np.item(i, "values")[2]
                 for i in tabla_np.get_children()) == ["COCA", "LEMA"],
          [tabla_np.item(i, "values")[2] for i in tabla_np.get_children()])
    chk_solo.invoke()
    raiz.update()
    tabla_np = _arboles(marco_np)[0]
    check("al desmarcar «Solo cercanas» vuelven las 3",
          len(tabla_np.get_children()) == 3,
          len(tabla_np.get_children()))

    # «Sin límite» deshabilita la casilla de radio; Enter aplica igual.
    chk_limite.invoke()
    raiz.update()
    check("«Sin límite» deshabilita la casilla de radio",
          str(entrada_radio.cget("state")) == "disabled",
          entrada_radio.cget("state"))
    chk_limite.invoke()
    raiz.update()
    check("al desmarcar «Sin límite» vuelve la casilla de radio",
          str(entrada_radio.cget("state")) == "normal",
          entrada_radio.cget("state"))
    entrada_radio.delete(0, "end")
    entrada_radio.insert(0, "20")
    entrada_radio.focus_set()
    entrada_radio.event_generate("<Return>")
    raiz.update()
    tabla_np = _arboles(marco_np)[0]
    check("Enter en la casilla de radio aplica igual que el botón",
          len(tabla_np.get_children()) == 1,
          [tabla_np.item(i, "values") for i in tabla_np.get_children()])

    # Ampliar: se reemplaza la consulta a la base por una lista fija.
    ampliadas = [{"id_evento": "ev1", "id_origen": "or1", "red": "CL",
                  "estacion": "FAR", "loc_ref": "", "cha_ref": "BHZ",
                  "streams_vigentes": "1", "distancia_km": "620.0",
                  "est_lat": "-30.0", "est_lon": "-70.0", "est_elev": "100",
                  "est_lugar": "Lejos", "est_pais": "Chile", "radio_km": "1000.0",
                  "actividad_ventana": "0", "waveform_status": "NO_CONSULTADO",
                  "availability_source": "", "cobertura_desde": "",
                  "cobertura_hasta": ""}]
    original_ampliar = ex.no_picadas_de_evento_desde_base

    def _lento(*a, **k):
        time.sleep(0.4)
        return (ampliadas, 0)

    ex.no_picadas_de_evento_desde_base = _lento
    try:
        entrada_radio.delete(0, "end")
        entrada_radio.insert(0, "1000")
        boton_aplicar.invoke()
        raiz.update()
        # La consulta corre en un hilo: mientras tanto el botón está
        # deshabilitado y la ventana sigue viva (la interfaz no se congela).
        check("durante la consulta el botón está deshabilitado",
              str(boton_aplicar.cget("state")) == "disabled",
              boton_aplicar.cget("state"))
        check("y la ventana sigue viva y respondiendo",
              ventana.winfo_exists() and ventana.winfo_viewable(),
              (ventana.winfo_exists(), ventana.winfo_viewable()))
        # El resultado vuelve por una cola que atiende el loop principal: hay
        # que esperarla antes de restaurar el parche (si no, el hilo podría
        # llamar a la función real).
        _esperar(lambda: len(_por_titulo("Sin arribos ampliado")) == 1
                 or any("Consulta a la base" in str(w.cget("text"))
                        for w in _etiquetas(ventana)))
    finally:
        ex.no_picadas_de_evento_desde_base = original_ampliar
    ampliadas_win = _por_titulo("Sin arribos ampliado")
    check("Aplicar radio con radio mayor al exportado abre la ventana aparte",
          len(ampliadas_win) == 1,
          [w.title() for w in _toplevels(raiz)])
    if ampliadas_win:
        ventana_amp = ampliadas_win[0]
        check("la ventana ampliada no captura la entrada",
              ventana_amp.grab_current() is None, ventana_amp.grab_current())
        tabla_amp = _arboles(ventana_amp)[0]
        check("la ventana ampliada trae la estación consultada",
              len(tabla_amp.get_children()) == 1
              and tabla_amp.item(tabla_amp.get_children()[0], "values")[2] == "FAR",
              [tabla_amp.item(i, "values")
               for i in tabla_amp.get_children()])
        check("la ventana ampliada tiene su descarga",
              any(str(b.cget("text")) == "Descargar sin arribos"
                  for b in _botones(ventana_amp)),
              [str(b.cget("text")) for b in _botones(ventana_amp)])
    textos_estado_win = [str(w.cget("text")) for w in _etiquetas(ventana)]
    check("el estado dice que se consultó la base a 1000 km",
          any("Consulta a la base (≤ 1000 km)" in x for x in textos_estado_win),
          textos_estado_win)

    # La tabla aclara la ventana de la columna de actividad (±2 h).
    textos_np = [str(w.cget("text")) for w in _etiquetas(ventana)]
    check("la tabla aclara que la actividad es ±2 h (2 antes y 2 después)",
          any("2 h antes y 2 h después" in x for x in textos_np), textos_np)
    check("la columna se llama Indicio ±2 h",
          any(t == "Indicio ±2 h" for _, t, _ in rs.COLUMNAS_NO_PICADA),
          rs.COLUMNAS_NO_PICADA)
    # Leyenda de colores de 2 líneas.
    check("la leyenda de colores está presente",
          any(x.startswith("Colores (Cerca = ≤") for x in textos_np), textos_np)
    check("la leyenda describe el caso verificado con ondas",
          any("Verificado con ondas" in x for x in textos_np), textos_np)
    check("la leyenda describe el caso de indicio por actividad",
          any("Indicio por actividad" in x for x in textos_np), textos_np)
    check("la leyenda describe el caso sin evidencia",
          any("Sin evidencia" in x for x in textos_np), textos_np)
    check("la leyenda aclara los casos lejanos",
          any("Más lejos: verde = verificado" in x for x in textos_np),
          textos_np)
    check("la leyenda usa el umbral configurado (50 km)",
          any("≤ 50 km" in x for x in textos_np), textos_np)

    # «Sin límite»: consulta la base con radio None y el encabezado lo dice.
    ex.no_picadas_de_evento_desde_base = lambda *a, **k: (ampliadas, 0)
    try:
        chk_limite.invoke()
        raiz.update()
        boton_aplicar.invoke()
        _esperar(lambda: any("sin límite" in str(w.cget("text"))
                            for w in _etiquetas(ventana)))
    finally:
        ex.no_picadas_de_evento_desde_base = original_ampliar
    if ampliadas_win:
        textos_amp = [str(w.cget("text")) for w in _etiquetas(ventana_amp)]
        check("«Sin límite» consulta sin tope y lo dice",
              any("sin límite" in x for x in textos_amp), textos_amp)

    # Aviso de cordura: con muchas filas pide confirmación antes de mostrar.
    import ttkbootstrap.dialogs as _dlg
    muchas = [dict(ampliadas[0]) for _ in range(rs.UMBRAL_AVISO_AMPLIADO + 1)]
    llamado = {"n": 0}

    def _cancelar(*a, **k):
        llamado["n"] += 1
        return "Cancelar"

    ex.no_picadas_de_evento_desde_base = lambda *a, **k: (muchas, 0)
    original_q = _dlg.Messagebox.show_question
    _dlg.Messagebox.show_question = _cancelar
    try:
        boton_aplicar.invoke()
        # El aviso lo muestra el hilo principal cuando el hilo de consulta
        # termina: esperar a que se abra antes de restaurar los parches.
        _esperar(lambda: llamado["n"] == 1)
    finally:
        _dlg.Messagebox.show_question = original_q
        ex.no_picadas_de_evento_desde_base = original_ampliar
    check("con muchas filas pide confirmación", llamado["n"] == 1, llamado)
    textos_win = [str(w.cget("text")) for w in _etiquetas(ventana)]
    check("al cancelar, el estado lo indica",
          any("cancelada" in x for x in textos_win), textos_win)

    # Elegir el segundo evento reusa la ventana de parámetros.
    arbol_ev.selection_set(arbol_ev.get_children()[1])
    _abrir_detalle(arbol_ev)
    parametros = _por_titulo("Parámetros del evento")
    check("la ventana de parámetros se reusa, no se abre otra",
          len(parametros) == 1 and parametros[0] is ventana_param,
          [w.title() for w in _toplevels(raiz)])
    check("y ahora muestra el segundo evento", "ev2" in ventana_param.title(),
          ventana_param.title())
    # El detalle se rearma, así que el botón anterior ya no existe: hay que
    # buscar el nuevo.
    boton = [b for b in _botones(ventana_param)
             if str(b.cget("text")) == "Estaciones"][0]
    boton.invoke()
    raiz.update()
    estaciones = _por_titulo("Estaciones del evento")
    check("la ventana de estaciones también se reusa",
          len(estaciones) == 1 and estaciones[0] is ventana,
          [w.title() for w in _toplevels(raiz)])
    tabla_no_picadas = _arboles(ventana)[1]
    check("el segundo evento trae 1 sola estación sin arribos",
          len(tabla_no_picadas.get_children()) == 1,
          [tabla_no_picadas.item(i, "values")
           for i in tabla_no_picadas.get_children()])

    # Un diálogo normal (confirmación) sí debe seguir capturando la entrada.
    dialogo = tb.Toplevel(raiz)
    rs.descargas.encima_de(raiz, dialogo)
    raiz.update()
    check("un diálogo normal sigue siendo modal",
          dialogo.grab_current() is not None, dialogo.grab_current())
    dialogo.destroy()

    raiz.destroy()

    # --- No actualizados: botón «Ver planta y perfil» ---
    base_gui = tempfile.mkdtemp(prefix="noact_gui_")
    os.makedirs(os.path.join(base_gui, "datos"))
    with open(os.path.join(base_gui, "datos", "atribucion_seiscomp.csv"),
              "w", newline="") as f:
        f.write("fecha_eventquery,lat_eventquery,lon_eventquery,"
                "prof_eventquery,mag_eventquery,fecha_local,lat_local,"
                "lon_local,prof_local,mag_local,analista,dt_seg,dlat,dlon\n")
        f.write("e1,-33.451,-70.610,88.0,2.4,l1,-33.420,-70.592,92.0,2.2,"
                "tark,2.1,0.031,0.018\n")
    raiz = tb.Window(themename="flatly")
    marco = tb.Frame(raiz)
    marco.pack(fill="both", expand=True)
    rs.abrir_no_actualizados(marco, "seiscomp", cwd=base_gui)
    raiz.update()
    botones_noact = [str(b.cget("text")) for b in _botones(marco)]
    check("el listado de No actualizados ya no trae el botón de ploteo",
          "Ver planta y perfil" not in botones_noact, botones_noact)
    textos_noact = [str(w.cget("text")) for w in _etiquetas(marco)]
    check("el listado avisa que el doble clic plotea",
          any("Doble clic plotea" in x for x in textos_noact), textos_noact)
    arbol_noact = _arboles(marco)[0]
    arbol_noact.selection_set(arbol_noact.get_children()[0])
    registrado = []
    orig_abrir = pl.abrir_eventos
    pl.abrir_eventos = lambda evs, fuente, **k: registrado.append((evs, fuente))
    try:
        # Doble clic / Enter sobre la fila (se usa Enter: mismo binding).
        toplevel = arbol_noact.winfo_toplevel()
        toplevel.focus_force()
        arbol_noact.focus_set()
        toplevel.update()
        arbol_noact.event_generate("<Return>", when="now")
        raiz.update()
    finally:
        pl.abrir_eventos = orig_abrir
    check("el doble clic/Enter plotea la solución local y la publicada",
          registrado and registrado[0][1] == "seiscomp"
          and len(registrado[0][0]) == 2
          and registrado[0][0][0]["rol"] == "local"
          and abs(registrado[0][0][0]["latitud"] + 33.420) < 1e-6
          and registrado[0][0][1]["rol"] == "publicado"
          and abs(registrado[0][0][1]["latitud"] + 33.451) < 1e-6, registrado)
    check("los eventos que se plotean no traen id (no se etiquetan)",
          registrado and all("id" not in e for e in registrado[0][0]),
          registrado)
    raiz.destroy()
    shutil.rmtree(base_gui, ignore_errors=True)

    print("== exportación vieja, sin archivo de no picadas ==")
    raiz = tb.Window(themename="flatly")
    marco = tb.Frame(raiz)
    marco.pack(fill="both", expand=True)
    # Ruta que no existe: es lo que pasa con una ventana exportada antes de que
    # el archivo existiera.
    ok = rs.abrir_panel(marco, BASE, BASE[:-4] + "_fases.csv",
                        os.path.join(RAIZ, "no_existe_no_picadas.csv"),
                        etiqueta_fuente="seiscomp", cwd=RAIZ)
    check("el panel abre igual sin el archivo de no picadas", ok is True)

    def _primer_arbol_sin(widget):
        for hijo in widget.winfo_children():
            if isinstance(hijo, tb.Treeview):
                return hijo
            encontrado = _primer_arbol_sin(hijo)
            if encontrado is not None:
                return encontrado
        return None

    arbol_ev = _primer_arbol_sin(marco)
    arbol_ev.selection_set(arbol_ev.get_children()[0])
    _abrir_detalle(arbol_ev)
    parametros = _por_titulo("Parámetros del evento")
    check("sin el archivo igual abre la ventana de parámetros",
          len(parametros) == 1, [w.title() for w in _toplevels(raiz)])
    boton = [b for b in _botones(parametros[0])
             if str(b.cget("text")) == "Estaciones"][0]
    boton.invoke()
    raiz.update()
    ventana = _por_titulo("Estaciones del evento")[0]
    check("sin el archivo no se arma la tabla de no picadas",
          len(_arboles(ventana)) == 1, len(_arboles(ventana)))
    textos = [str(w.cget("text")) for w in _etiquetas(ventana)]
    check("la solapa avisa que hay que reexportar",
          any("no tiene el archivo" in x for x in textos), textos)
    check("la cabecera de la ventana avisa también",
          any("sin arribos: sin archivo" in x for x in textos), textos)
    check("igual muestra las picadas",
          len(_arboles(ventana)[0].get_children()) == 3,
          len(_arboles(ventana)[0].get_children()))
    raiz.destroy()

shutil.rmtree(RAIZ, ignore_errors=True)
shutil.rmtree(raiz_pares, ignore_errors=True)
print()
if fallos:
    print("FALLARON %d: %s" % (len(fallos), fallos))
    sys.exit(1)
print("Todas las pruebas pasaron.")
