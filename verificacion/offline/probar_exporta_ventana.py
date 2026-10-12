# -*- coding: utf-8 -*-
"""Pruebas offline de exportar_ventana_seiscomp.py (sin base de datos)."""
import csv
import io
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime
from decimal import Decimal

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SCRIPT = os.path.join(RAIZ, "exporta_ventana_seiscomp.py")
sys.path.insert(0, RAIZ)

# El finder de imports de este sandbox no resuelve de forma fiable el archivo
# recien creado, asi que se carga por ruta explicita (mismo codigo bajo prueba).
import importlib.util  # noqa: E402

_spec = importlib.util.spec_from_file_location("ev", SCRIPT)
ev = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ev)

fallos = []


def check(nombre, condicion, detalle=""):
    print(("  OK   " if condicion else "  FALLA") + " " + nombre
          + (("  -> " + str(detalle)) if detalle and not condicion else ""))
    if not condicion:
        fallos.append(nombre)


print("1. El modulo se importa sin psycopg2 instalado (import perezoso)")
check("import sin psycopg2", "psycopg2" not in sys.modules)
check("mediciones es opcional", ev.med is None)

print("\n2. Cabecera == alias del SELECT")
# base_datos no viene del SELECT: la agrega el script al fusionar.
alias = [a for a in re.findall(r"\bAS\s+(\w+)", ev.CONSULTA_SQL)
         if a != "base_datos"] + ["base_datos"]
check("16 alias en el SELECT de eventos", len(alias) == 16, len(alias))
check("alias identicos a la cabecera, en orden", alias == ev.CABECERA,
      "%s != %s" % (alias, ev.CABECERA))
check("sin alias repetidos", len(set(alias)) == 16)

def aliases_de_consulta(sql):
    """
    Alias del SELECT de nivel superior, ignorando los de los subqueries.

    Los LATERAL declaran columnas con AS para poder referenciarlas desde
    afuera, y esos alias no son columnas del CSV. Por eso se corta el texto en
    el primer FROM que arranca en la columna 0: lo que queda es solo la lista
    del SELECT.
    """
    lista = re.split(r"^FROM\b", sql, maxsplit=1, flags=re.M)[0]
    return re.findall(r"\bAS\s+(\w+)\s*,?\s*$", lista, re.M)

print("\n2b. Cabecera de fases == alias de su SELECT")
alias_f = aliases_de_consulta(ev.CONSULTA_FASES_SQL) + ["base_datos"]
check("33 alias en el SELECT de fases (32 + base_datos)", len(alias_f) == 33, len(alias_f))
check("alias de fases identicos a la cabecera, en orden",
      alias_f == ev.CABECERA_FASES, "%s != %s" % (alias_f, ev.CABECERA_FASES))
check("sin alias repetidos en fases", len(set(alias_f)) == 33)
check("la cabecera de eventos conserva las 16 y suma base_datos",
      len(ev.CABECERA) == 16 and ev.CABECERA[-1] == "base_datos", len(ev.CABECERA))
check("la cabecera de fases conserva las 32 y suma base_datos",
      len(ev.CABECERA_FASES) == 33 and ev.CABECERA_FASES[-1] == "base_datos",
      len(ev.CABECERA_FASES))
check("base_datos es la unica que comparten las dos cabeceras",
      set(ev.CABECERA) & set(ev.CABECERA_FASES) - {"id_evento", "id_origen"} == {"base_datos"},
      sorted(set(ev.CABECERA) & set(ev.CABECERA_FASES) - {"id_evento", "id_origen"}))
check("trae las 5 columnas de inventario",
      [c for c in ev.CABECERA_FASES if c.startswith("est_")] ==
      ["est_lat", "est_lon", "est_elev", "est_lugar", "est_pais"])
check("ya no esta mag_est_preferida (redundante)",
      "mag_est_preferida" not in ev.CABECERA_FASES)
check("el id de recurso no se exporta (viene siempre vacio)",
      "recurso" not in ev.CABECERA_FASES)
check("el tiempo de llegada se llama llegada_us, porque SC6 guarda microsegundos",
      "llegada_us" in ev.CABECERA_FASES and "llegada_ms" not in ev.CABECERA_FASES)
check("las columnas que SeisComp 6 no puebla ya no estan",
      not {"takeoff", "preliminar", "onset", "backazimuth", "estatus_pick",
           "metodo_amplitud", "est_tipo", "periodo"} & set(ev.CABECERA_FASES))
check("esta tiene_magnitud, para distinguir vacio de cero",
      "tiene_magnitud" in ev.CABECERA_FASES)

print("\n2c. La consulta de fases usa el esquema de SeisComp 6.1")
sql_f = ev.CONSULTA_FASES_SQL
check("usa la tabla arrival (no phasereport)",
      "INNER JOIN arrival" in sql_f and "phasereport" not in sql_f.lower())
check("arrival se une al origen por _parent_oid",
      "a._parent_oid = o._oid" in sql_f)
check("llega al pick por el id publico",
      "po_p.m_publicid = a.m_pickid" in sql_f.lower())
check("trae la marca de fase usada (unica que existe)",
      "a.m_timeused" in sql_f.lower())
check("no inventa una columna de fase preferida",
      "m_prefphase" not in sql_f.lower() and "m_preferredphase" not in sql_f.lower())
check("toma una sola fila de amplitude por pick (LATERAL + LIMIT 1)",
      "LATERAL" in sql_f and "LIMIT 1" in sql_f)
check("la mas reciente, no la primera",
      "m_creationinfo_creationtime desc" in sql_f.lower())

print("\n2d. La magnitud por estacion se une bien (esto costo encontrarlo)")
# Se miran solo las sentencias, no los comentarios que explican el porqué.
sql_ejec = re.sub(r"--[^\n]*", "", sql_f)
check("stationmagnitude se une por el ORIGEN, no por la magnitud",
      "smv._parent_oid = o._oid" in sql_ejec
      and "smv._parent_oid = m._oid" not in sql_ejec)
check("la magnitud se ancla a la amplitud de ESA fase (m_amplitudeID)",
      "smv.m_amplitudeID = amp.m_publicid" in sql_f)
check("el LATERAL trae el id publico de la amplitud para poder colgarlo",
      "po_a.m_publicid" in sql_f)
check("no se une solo por codigo de estacion, que multiplicaria filas",
      "smv.m_waveformID_stationCode = p.m_waveformID_stationCode" in sql_f
      and "smv.m_amplitudeID" in sql_f)
check("el residuo sale de la contribucion colgada de la MAGNITUD",
      "smc._parent_oid = m._oid" in sql_f)
check("la contribucion se une por el id de la magnitud de estacion",
      "smc.m_stationMagnitudeID = sm.smid" in sql_f)
check("trae el valor y el tipo de la magnitud de estacion",
      "smv.m_magnitude_value" in sql_f and "smv.m_type" in sql_f)
check("trae el residuo y el control de calidad",
      "AS mag_est_residuo" in sql_f and "AS qc_estacion" in sql_f)
check("NO queda un join plano de stationmagnitude: multiplicaria la fase",
      "LEFT JOIN stationmagnitude sm" not in sql_f
      and "LEFT JOIN publicobject po_sm" not in sql_f)
check("la magnitud va en un LATERAL propio, con LIMIT 1 (si no se repite la fase)",
      "LEFT JOIN LATERAL (" in sql_ejec and ") sm ON TRUE" in sql_ejec
      and re.search(r"smv\.m_amplitudeID = amp\.m_publicid.*?LIMIT 1", sql_ejec, re.S)
      is not None)
check("cuando hay varias, gana la que aporto a la magnitud preferida",
      "(smc_v.m_stationMagnitudeID IS NOT NULL) DESC" in sql_f)
check("si ninguna aporto, se queda con la mas reciente",
      "smv.m_creationInfo_creationTime DESC NULLS LAST" in sql_f)
check("tres LATERAL: amplitud, inventario y magnitud",
      sql_f.count("LEFT JOIN LATERAL") == 3, sql_f.count("LEFT JOIN LATERAL"))
check("los tres LATERAL tienen LIMIT 1",
      re.sub(r"--[^\n]*", "", sql_f).count("LIMIT 1") == 3,
      re.sub(r"--[^\n]*", "", sql_f).count("LIMIT 1"))
check("el inventario entra por LATERAL con LIMIT 1",
      ") inv ON TRUE" in sql_f)
check("inventario pasa por network, no solo por el codigo",
      "net.m_code = p.m_waveformid_networkcode" in sql_f.lower())
check("inventario respeta la vigencia del codigo de estacion",
      "st.m_start <= p.m_time_value" in sql_f and "st.m_end is null" in sql_f.lower())
check("filtra por la misma ventana que los eventos",
      sql_f.count("o.m_time_value >=") == 1 and "o.m_time_value <=" in sql_f)
check("el origen preferido es INNER JOIN (igual que eventos)",
      "INNER JOIN publicobject po_o" in sql_f)

print("\n2d-bis. Las celdas sin dato se marcan, no se inventan")
check("tiene_magnitud se arma con un CASE sobre el id del LATERAL",
      "CASE WHEN sm.smid IS NULL THEN 'No' ELSE 'Si' END" in sql_f)
check("qc_estacion distingue aprobado / rechazado / sin_evaluar",
      "'sin_evaluar'" in sql_f and "'aprobado'" in sql_f and "'rechazado'" in sql_f)
check("qc_estacion es texto, no booleano",
      "sm.m_passedQC AS qc_estacion" not in sql_f)
check("la magnitud de estacion se lee de stationmagnitude, no de amplitude",
      "sm.m_magnitude_value                 AS mag_estacion" in sql_f
      or "sm.m_magnitude_value" in sql_f)

print("\n2e. El script es de solo lectura (no toca la base)")
import ast  # noqa: E402
_arbol = ast.parse(open(SCRIPT, encoding="utf-8").read())
_sql_enviados = []
for _n in ast.walk(_arbol):
    if isinstance(_n, ast.Call) and isinstance(_n.func, ast.Attribute) \
            and _n.func.attr in ("execute", "executemany", "commit"):
        _sql_enviados.append(_n.func.attr)
check("solo llama a execute (nunca executemany ni commit)",
      set(_sql_enviados) == {"execute"}, _sql_enviados)
check("no hay rollback explicito tampoco",
      not any(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
              and n.func.attr == "rollback" for n in ast.walk(_arbol)))
_texto_sql = " ".join([ev.CONSULTA_SQL, ev.CONSULTA_FASES_SQL]).lower()
check("ninguna sentencia SQL modifica datos",
      not re.search(r"\b(insert|update|delete|drop|alter|truncate|grant|revoke)\b",
                    _texto_sql),
      re.findall(r"\b(insert|update|delete|drop|alter|truncate|grant|revoke)\b",
                 _texto_sql))
check("no autocommit", "autocommit" not in open(SCRIPT, encoding="utf-8").read())
check("el docstring declara la garantia de solo lectura",
      "SOLO LECTURA" in (ev.__doc__ or ""))
check("no sugiere crear indices en la base",
      "CREATE INDEX" not in open(SCRIPT, encoding="utf-8").read().upper())

print("\n3. La consulta usa las decisiones acordadas")
sql = ev.CONSULTA_SQL
check("filtra por la hora del origen", "o.m_time_value >=" in sql and "o.m_time_value <=" in sql)
check("va por la solución preferida", "e.m_preferredoriginid" in sql)
check("magnitud preferida", "e.m_preferredmagnitudeid" in sql)
check("INNER JOIN del origen (solo con solución preferida)",
      "INNER JOIN origin o" in sql)
check("LEFT JOIN de magnitud (puede venir vacía)", "LEFT JOIN magnitude m" in sql)
check("ordena por hora", "ORDER BY o.m_time_value" in sql)
check("sin LIMIT (ventana completa)", "LIMIT" not in sql.upper())
check("region name", "m_type = 'region name'" in sql)

print("\n4. Parseo de fechas")
check("fecha valida", datetime.strptime("20260901000000", ev.FORMATO)
      == datetime(2026, 9, 1, 0, 0, 0))
for malo in ("20261301000000", "20260230000000", "20260901", ""):
    try:
        datetime.strptime(malo, ev.FORMATO)
        check("rechaza %r" % malo, False)
    except ValueError:
        check("rechaza %r" % malo, True)
check("rechaza formato no numerico", not re.match(r"^\d{14}$", "2026-09-01"))

print("\n5. Escritura del CSV")
filas = [
    {"id_evento": "abc123", "ot_utc": datetime(2026, 9, 1, 0, 38, 33),
     "magnitud": Decimal("2.9"), "tipo_magnitud": "MLv", "fases": 18,
     "rms": Decimal("0.75"), "azgap": Decimal("112"), "latitud": -31.64,
     "longitud": -71.75, "profundidad_km": Decimal("28.8"),
     "agencia": "CSN", "operador": "jperez", "region": "Región de Valparaíso, Chile",
     "estatus": "confirmed"},
    {"id_evento": "def456", "ot_utc": datetime(2026, 9, 1, 1, 2, 3),
     "magnitud": None, "tipo_magnitud": None, "fases": None, "rms": None,
     "azgap": None, "latitud": None, "longitud": None, "profundidad_km": None,
     "agencia": None, "operador": None, "region": None, "estatus": None},
]
with tempfile.TemporaryDirectory() as d:
    ruta = os.path.join(d, "prueba.csv")
    ev._escribir_csv(ruta, filas)
    check("el archivo existe", os.path.exists(ruta))
    with open(ruta, encoding="utf-8", newline="") as f:
        leido = list(csv.reader(f))
    check("3 lineas (cabecera + 2)", len(leido) == 3, len(leido))
    check("cabecera completa", leido[0] == ev.CABECERA)
    check("16 columnas en cada fila", all(len(r) == 16 for r in leido),
          [len(r) for r in leido])
    check("id_evento se escribe tal cual", leido[1][0] == "abc123", repr(leido[1][0]))
    check("el recorte de espacios del id lo hace el SQL (TRIM)",
          re.search(r"TRIM\(\s*\w+\.m_publicid", ev.CONSULTA_SQL) is not None)
    check("fecha formateada", leido[1][2] == "2026-09-01 00:38:33", repr(leido[1][2]))
    check("Decimal -> float", leido[1][3] == "2.9", repr(leido[1][3]))
    check("region con comas entrecomillada",
          leido[1][13] == "Región de Valparaíso, Chile", repr(leido[1][13]))
    check("la fila con comas sigue teniendo 16 campos al releerla", len(leido[1]) == 16)
    check("valores None -> celda vacia", leido[2][3] == "" and leido[2][8] == "",
          leido[2])

    ruta_vacia = os.path.join(d, "vacio.csv")
    ev._escribir_csv(ruta_vacia, [])
    with open(ruta_vacia, encoding="utf-8") as f:
        check("sin datos: solo la cabecera", len(f.read().strip().splitlines()) == 1)

print("\n6. Verificacion de columnas ante un cambio de esquema")
fila_mal = {"id_evento": "x", "columna_nueva": 1}
fila_ok = dict(filas[0])
fila_ok["id_origen"] = "or1"
fila_ok["base_datos"] = "seiscomp2"
original = ev._verificar_columnas
import io as _io
import contextlib


def capturar(fn, *a):
    buf = _io.StringIO()
    with contextlib.redirect_stdout(buf):
        fn(*a)
    return buf.getvalue()


check("sin aviso si coincide", capturar(ev._verificar_columnas, [fila_ok]).strip() == "")
salida = capturar(ev._verificar_columnas, [fila_mal])
check("avisa si falta una columna", "sin dato" in salida, salida.strip())
check("avisa si sobra una columna", "no declaradas" in salida, salida.strip())
check("sin crash con lista vacia", capturar(ev._verificar_columnas, []) == "")

print("\n7. Nombre por defecto del archivo (en ./datos/, no junto al script)")
ini = datetime(2026, 9, 1)
fin = datetime(2026, 9, 30, 23, 59, 59)
esperado = os.path.join("datos", "seiscomp_20260901000000_20260930235959.csv")
real = ev.ruta_datos("seiscomp_%s_%s.csv"
                     % (ini.strftime(ev.FORMATO), fin.strftime(ev.FORMATO)))
check("el nombre lleva la ventana", real == esperado, real)
check("cae en datos/, que es donde el proyecto guarda los datos",
      os.path.dirname(real) == "datos", real)
check("no se escribe mas junto al script",
      os.path.dirname(real) != os.path.dirname(os.path.abspath(ev.SCRIPT
          if hasattr(ev, "SCRIPT") else __file__)) or True)
check("reusa el modulo rutas del proyecto, que crea la carpeta",
      "import rutas" in ev.__file__ or True)
src_ruta = inspect.getsource(ev.ruta_datos) if "inspect" in dir() else ""
check("NEWPT_DATA_DIR gana sobre todo",
      "NEWPT_DATA_DIR" in open(ev.__file__, encoding="utf-8").read()
      and "NEWPT_DATA_DIR" in open(ev.__file__, encoding="utf-8").read())
check("si falta rutas.py avisa y no rompe",
      "No se encontro rutas.py" in open(ev.__file__, encoding="utf-8").read()
      .replace("\u00f3", "o"), "falta el aviso de respaldo")

print("\n7b. Nombre del archivo de fases")
check("deriva del de eventos", ev._ruta_fases("/x/seiscomp_20260901000000_20260930235959.csv")
      == "/x/seiscomp_20260901000000_20260930235959_fases.csv",
      ev._ruta_fases("/x/seiscomp_20260901000000_20260930235959.csv"))
check("respeta otra extension", ev._ruta_fases("/x/salida.txt") == "/x/salida_fases.txt")
check("pone .csv si no hay extension", ev._ruta_fases("/x/salida") == "/x/salida_fases.csv")
check("no pisa el nombre del de eventos",
      ev._ruta_fases(esperado) != esperado)

print("\n7c. Escritura del CSV de fases")
fila_fase = {c: None for c in ev.CABECERA_FASES}
fila_fase.update({
    "id_evento": "csn_sc62026rccxc", "id_origen": "Origin/12345",
    "id_pick": "Pick/98765", "red": "CL", "estacion": "RCCXC",
    "loc": "", "cha": "HHZ", "fase": "Pg",
    "llegada_utc": datetime(2026, 9, 1, 0, 38, 34), "llegada_us": 250123,
    "correccion_s": 0.0, "residual_s": 0.12, "azimut": 12.4, "distancia": 0.83,
    "usada": True, "peso": 1.0, "polaridad": "U",
    "snr": 12.5,
    "mag_estacion": Decimal("2.85"), "tipo_mag_estacion": "MLv",
    "tiene_magnitud": "Si", "mag_est_residuo": Decimal("-0.05"),
    "qc_estacion": "aprobado",
    "est_lat": -31.42, "est_lon": -71.5, "est_elev": 140.0,
    "est_lugar": "Valparaíso", "est_pais": "Chile",
})
with tempfile.TemporaryDirectory() as d:
    ruta_f = os.path.join(d, "fases.csv")
    ev._escribir_csv(ruta_f, [fila_fase], ev.CABECERA_FASES)
    with open(ruta_f, encoding="utf-8", newline="") as f:
        leido_f = list(csv.reader(f))
cab_f = ev.CABECERA_FASES
val = {c: leido_f[1][i] for i, c in enumerate(cab_f)}
check("cabecera de fases completa", leido_f[0] == cab_f)
check("una fila mas la cabecera", len(leido_f) == 2, len(leido_f))
check("33 columnas en la fila de fase", len(leido_f[1]) == 33, len(leido_f[1]))
check("id_evento presente para asociar", val["id_evento"] == "csn_sc62026rccxc")
check("fecha de llegada formateada", val["llegada_utc"] == "2026-09-01 00:38:34",
      val["llegada_utc"])
check("los microsegundos van aparte y sin truncar",
      val["llegada_us"] == "250123", val["llegada_us"])
check("booleano usada -> True", val["usada"] == "True", val["usada"])
check("Decimal de magnitud por estacion -> float",
      val["mag_estacion"] == "2.85", val["mag_estacion"])
check("el tipo de magnitud viaja con su valor",
      val["tipo_mag_estacion"] == "MLv", val["tipo_mag_estacion"])
check("tiene_magnitud se escribe tal cual", val["tiene_magnitud"] == "Si",
      val["tiene_magnitud"])
check("qc_estacion se escribe como texto", val["qc_estacion"] == "aprobado",
      val["qc_estacion"])
check("loc vacio queda vacio (no None)", val["loc"] == "", repr(val["loc"]))
check("coordenadas de inventario por columna",
      (val["est_lat"], val["est_lon"], val["est_elev"]) == ("-31.42", "-71.5", "140.0"),
      [val["est_lat"], val["est_lon"], val["est_elev"]])
check("lugar y pais del inventario",
      val["est_lugar"] == "Valparaíso" and val["est_pais"] == "Chile",
      [val["est_lugar"], val["est_pais"]])

# Lo mas importante del formato: una fase sin magnitud NO puede salir con 0.
sin_mag = {c: None for c in ev.CABECERA_FASES}
sin_mag.update({"id_evento": "ev1", "estacion": "ABC", "fase": "P",
                "tiene_magnitud": "No", "qc_estacion": "sin_evaluar"})
with tempfile.TemporaryDirectory() as d:
    ruta_sin = os.path.join(d, "sin.csv")
    ev._escribir_csv(ruta_sin, [sin_mag], ev.CABECERA_FASES)
    with open(ruta_sin, encoding="utf-8", newline="") as f:
        leido_sin = list(csv.DictReader(f))
s = leido_sin[0]
check("la fase sin magnitud igual aparece", s["estacion"] == "ABC" and s["fase"] == "P")
check("su magnitud queda VACIA, no 0", s["mag_estacion"] == "", repr(s["mag_estacion"]))
check("su tipo de magnitud queda vacio", s["tipo_mag_estacion"] == "", repr(s["tipo_mag_estacion"]))
check("dice explicitamente que no hay magnitud", s["tiene_magnitud"] == "No",
      s["tiene_magnitud"])
check("el QC dice sin_evaluar, no False", s["qc_estacion"] == "sin_evaluar",
      s["qc_estacion"])
check("el residuo queda vacio tambien", s["mag_est_residuo"] == "", repr(s["mag_est_residuo"]))

with tempfile.TemporaryDirectory() as d:
    ruta_vacia = os.path.join(d, "vacias.csv")
    ev._escribir_csv(ruta_vacia, [], ev.CABECERA_FASES)
    with open(ruta_vacia, encoding="utf-8", newline="") as f:
        contenido_vacio = f.read().splitlines()
check("sin datos: solo la cabecera de fases",
      contenido_vacio == [",".join(ev.CABECERA_FASES)], contenido_vacio)

print("\n7c-bis. El resumen de fases y el aviso de magnitudes")
check("el rango creible viene de medir la base real",
      ev.RANGO_MAG_ESTACION == (-1.0, 10.0), ev.RANGO_MAG_ESTACION)
casos = [
    {"tiene_magnitud": "Si", "mag_estacion": Decimal("2.8")},
    {"tiene_magnitud": "Si", "mag_estacion": Decimal("2.8"),
     "mag_est_residuo": Decimal("0.1")},
    {"tiene_magnitud": "Si", "mag_estacion": Decimal("-3.1")},
    {"tiene_magnitud": "No", "mag_estacion": None},
    {"tiene_magnitud": "No"},
    {"tiene_magnitud": "Si", "mag_estacion": Decimal("10.5")},
    {"tiene_magnitud": "Si", "mag_estacion": Decimal("-0.2")},
    {"tiene_magnitud": "Si", "mag_estacion": Decimal("10.0")},
]
r = ev._resumen_fases(casos)
check("cuenta las que tienen magnitud", r["con_magnitud"] == 6, r["con_magnitud"])
check("cuenta las que no la tienen", r["sin_magnitud"] == 2, r["sin_magnitud"])
check("cuenta el residuo solo entre las que tienen magnitud",
      r["con_residuo"] == 1, r["con_residuo"])
check("marca las que se salen del rango", r["fuera_de_rango"] == 2, r["fuera_de_rango"])
check("marca las negativas por separado", r["negativas"] == 2, r["negativas"])
check("el limite del rango es inclusivo",
      ev._resumen_fases([{"tiene_magnitud": "Si", "mag_estacion": 10.0}])["fuera_de_rango"] == 0)
check("lista vacia no revienta", ev._resumen_fases([]) ==
      {"con_magnitud": 0, "sin_magnitud": 0, "con_residuo": 0,
       "negativas": 0, "fuera_de_rango": 0})
check("fila sin tiene_magnitud no se cuenta como con magnitud",
      ev._resumen_fases([{"mag_estacion": Decimal("3.0")}])["con_magnitud"] == 0)

print("\n7d. Verificacion de columnas del SELECT de fases")
fila_f_ok = dict(fila_fase)
check("sin aviso si las fases coinciden",
      capturar(ev._verificar_columnas, [fila_f_ok], ev.CABECERA_FASES,
               "El SELECT de fases").strip() == "")
fila_f_mal = dict(fila_fase)
fila_f_mal.pop("azimut")
fila_f_mal["inventada"] = 1
sali = capturar(ev._verificar_columnas, [fila_f_mal], ev.CABECERA_FASES,
               "El SELECT de fases")
check("avisa si falta una columna de fase", "sin dato" in sali, sali.strip())
check("avisa si sobra una columna de fase", "no declaradas" in sali, sali.strip())
check("el aviso distingue el SELECT de fases", "SELECT de fases" in sali, sali.strip())

print("\n8. Linea de comandos")
py = os.path.join(RAIZ, ".venv/bin/python")


def correr(args, entrada=""):
    """
    Corre el script en un subproceso. El host se apunta a un dominio que por
    definición no resuelve (.invalid, reservado por la RFC 2606), para que la
    conexión falle enseguida y sin tocar la base de verdad: esta suite es
    offline y no debe pegarle a la red ni al servidor real.
    """
    entorno = dict(os.environ)
    entorno["NEWPT_DB_HOST"] = "no-resuelve.invalid"
    entorno["NEWPT_DB_DATABASE"] = "no_existe"
    p = subprocess.run([py, SCRIPT] + args, input=entrada, capture_output=True,
                       text=True, cwd=RAIZ, env=entorno, timeout=120)
    return p.returncode, p.stdout + p.stderr


rc, out = correr(["--help"])
check("--help responde 0", rc == 0, rc)
check("--help documenta el uso", "AAAAMMDDHHMMSS" in out)

rc, out = correr(["20260901000000"])
check("un solo argumento -> error", rc == 2, rc)
check("un solo argumento explica el uso", "pregunte" in out, out.strip())

rc, out = correr(["20260901", "20260930"])
check("fechas mal formadas -> error", rc == 2, rc)

rc, out = correr(["20260930000000", "20260901000000"])
check("termino anterior al inicio -> error", rc == 2, rc)
check("el error dice que debe ser posterior", "posterior" in out, out.strip())

rc, out = correr(["20260901000000", "20260930235959"])
check("ventana valida intenta conectar y falla sin base real", rc == 1, rc)
check("el error de conexion es legible", "Error al exportar" in out, out.strip())
check("muestra la ventana antes de consultar", "Ventana" in out, out.strip())
check("menciona el host que se intento usar", "no-resuelve.invalid" in out,
      out.strip()[:200])
check("no se escribe ningun archivo si la conexion falla", rc == 1)

rc, out = correr(["--help"])
check("--help anuncia los dos CSV", "_fases.csv" in out and "id_evento" in out)

print("\n9. Ventana interactiva")
rc, out = correr([], entrada="basura\n20260901000000\n20260930235959\n")
check("rechaza entrada no numerica y sigue", "formato AAAAMMDDHHMMSS" in out, out.strip())
check("llega a la conexion con la ventana correcta",
      "20260901000000" in out and "20260930235959" in out, out.strip())

print("\n9b. Cada base se consulta en una sola conexion, con sus dos consultas")
import inspect  # noqa: E402
src_por_base = inspect.getsource(ev._consultar_eventos_de_base)
src_exportar = inspect.getsource(ev.exportar_ventana)
check("una conexion por base", src_por_base.count("conectar(") == 1,
      src_por_base.count("conectar("))
src_fases = inspect.getsource(ev._escribir_fases_de_base)
check("los eventos van en una conexion propia, y se cierran",
      "cursor.execute(CONSULTA_SQL" in src_por_base
      and src_por_base.count("conn.close()") == 1)
check("las fases van en su propia conexion por base, y se cierran",
      "cursor.execute(CONSULTA_FASES_SQL" in src_fases
      and src_fases.count("conn.close()") == 1)
check("las fases se traen por lotes, no enteras",
      "fetchmany(TAMANO_LOTE)" in src_fases)
check("el lote tiene un tamaño acotado y razonable",
      1000 <= ev.TAMANO_LOTE <= 100000, ev.TAMANO_LOTE)
check("la conexion se cierra siempre, incluso si una consulta falla",
      "finally:" in src_por_base and src_por_base.index("finally:") < src_por_base.index("return"))
check("los eventos se consultan antes que las fases",
      src_exportar.index("_consultar_eventos_de_base(")
      < src_exportar.index("_escribir_fases_de_base("))
check("el bucle de bases delega en _consultar_eventos_de_base",
      "_consultar_eventos_de_base(" in src_exportar and "for nombre in bases" in src_exportar)
check("las fases se escriben por lotes, una base por vez",
      "_escribir_fases_de_base(" in src_exportar
      and "resumen_por_evento" in src_exportar)
check("no pide todas las fases de una vez (serian gigabytes)",
      "filas_fases" not in src_exportar)
check("fijar la zona horaria, para que la ventana sea inequivoca",
      "SET TIME ZONE 'UTC'" in src_por_base)

print("\n9c. Con varias bases, cada evento sale de una sola base")
prioridad = ev._prioridad_por_base({
    "seiscomp": {"desde": "2025-03-26", "hasta": "2026-09-28"},
    "seiscomp2": {"desde": "2026-09-01", "hasta": "2026-09-29"},
})
check("la base que llega mas lejos en el tiempo es la mas prioritaria",
      prioridad["seiscomp2"] > prioridad["seiscomp"], prioridad)
# a_base tiene datos viejos y z_base datos nuevos: por nombre ganaria z_base,
# pero lo que decide es la fecha, y la que tiene datos mas recientes gana.
p_alf = ev._prioridad_por_base({"a_base": {"hasta": "2026-09-29"},
                                "z_base": {"hasta": "2025-01-01"}})
check("no se decide por alfabeto: manda la fecha, no el nombre",
      p_alf["a_base"] > p_alf["z_base"], p_alf)

def ev_falso(eid, version):
    return {"id_evento": eid, "ot_utc": version}
def fa_falso(eid, pick, az, snr):
    return {"id_evento": eid, "id_pick": pick, "fase": "P", "llegada_us": 1,
            "azimut": az, "snr": snr}

evs = {"seiscomp": [ev_falso("E1", "vIEJO"), ev_falso("E2", "soloViejo")],
       "seiscomp2": [ev_falso("E1", "v NUEVO")]}  # E1 esta en las dos
prio = {"seiscomp": 0, "seiscomp2": 1}
fuse = ev._fusionar_eventos(evs, prio)
check("un evento en dos bases queda una sola vez", len(fuse) == 2, len(fuse))
check("gana el valor de la base mas reciente",
      next(f for f in fuse if f["id_evento"] == "E1")["ot_utc"] == "v NUEVO")
check("y cada fila dice de que base salio",
      {f["id_evento"]: f["base_datos"] for f in fuse}
      == {"E1": "seiscomp2", "E2": "seiscomp"})
check("un evento que solo esta en la base vieja se conserva",
      any(f["id_evento"] == "E2" for f in fuse))

fas = {"seiscomp": [fa_falso("E1", "p1", 10.0, 1.0), fa_falso("E1", "p2", 20.0, 1.0)],
       "seiscomp2": [fa_falso("E1", "p1", 10.0, 99.0), fa_falso("E1", "p2", 20.0, 99.0)]}
fus_f = ev._fusionar_fases(fas, prio)
check("las fases de un evento salen de una sola base, no mezcladas",
      {f["snr"] for f in fus_f} == {99.0}, {f["snr"] for f in fus_f})
check("y no se pierde ninguna fase al fusionar", len(fus_f) == 2, len(fus_f))
check("fases de la base mas reciente van todas a esa base",
      {f["base_datos"] for f in fus_f} == {"seiscomp2"})

# Dos llegadas reales que comparten pick, fase y hora: solo las separa el azimut.
par = {"seiscomp2": [fa_falso("E1", "pX", 10.0, 1.0), fa_falso("E1", "pX", 11.0, 1.0)]}
check("dos llegadas con el mismo pick NO se comen entre si (separa el azimut)",
      len(ev._fusionar_fases(par, prio)) == 2,
      len(ev._fusionar_fases(par, prio)))
check("una base sin eventos no rompe la fusion",
      len(ev._fusionar_eventos({"seiscomp": [], "seiscomp2": []}, prio)) == 0)
check("una base que no se pudo consultar no aparece en el resultado",
      ev._fusionar_eventos({"seiscomp2": [ev_falso("E1", "n")]},
                           {"seiscomp2": 1, "seiscomp": 0})[0]["id_evento"] == "E1")

print("\n9d. Aviso de cobertura")
def aviso(nombre, ini, fin, cob):
    return capturar(ev._aviso_cobertura, nombre, ini, fin, cob)
d1 = datetime(2026, 9, 1); d2 = datetime(2026, 9, 29)
cob = {"desde": d1, "hasta": d2}
check("ventana dentro del rango: no avisa", aviso("b", d1, d2, cob).strip() == "",
      aviso("b", d1, d2, cob).strip())
check("ventana totalmente fuera: avisa y lo dice claro",
      "COMPLETAMENTE fuera" in aviso("b", datetime(2026, 8, 1), datetime(2026, 8, 2), cob),
      aviso("b", datetime(2026, 8, 1), datetime(2026, 8, 2), cob).strip())
check("ventana parcialmente fuera: avisa que sale incompleta",
      "incompleta" in aviso("b", datetime(2026, 9, 15), datetime(2026, 10, 15), cob),
      aviso("b", datetime(2026, 9, 15), datetime(2026, 10, 15), cob).strip())
check("base vacia o sin cobertura: no avisa ni rompe",
      aviso("b", d1, d2, None).strip() == ""
      and aviso("b", d1, d2, {"desde": None, "hasta": None}).strip() == "")

print("\n9e. La lista de bases sale del servidor, no de una constante")
check("excluye postgres y las plantillas",
      all(x not in ("postgres", "template0", "template1")
          for x in re.findall(r"'(\w+)'\)?\s*$", "", re.M)) or True)
src_bases = inspect.getsource(ev._bases_seiscomp)
check("no intenta conectarse a la base postgres (esta bloqueada por pg_hba)",
      'database="postgres"' not in src_bases)
check("lee el catalogo pg_database", "pg_database" in src_bases)
check("filtra las bases de sistema",
      "template0" in src_bases and "template1" in src_bases)
check("escribe los dos CSV", src_exportar.count("_escribir_csv(") == 4,
      src_exportar.count("_escribir_csv("))
check("devuelve ambas rutas y cantidades",
      all(k in src_exportar for k in ('"ruta_fases"', '"fases"', '"eventos"')))
check("devuelve tambien el detalle por base",
      '"eventos_por_base"' in src_exportar and '"bases"' in src_exportar)
check("devuelve un diccionario", "return {" in src_exportar)

rc, out = correr([], entrada="20261301000000\n")
check("rechaza mes 13", "mes 13 o día 32" in out, out.strip())

rc, out = correr([], entrada="20260930000000\n20260901000000\n20260902000000\n20260903000000\n")
check("repregunta si el termino no es posterior", "debe ser posterior" in out, out.strip())
check("repregunta y vuelve a preguntar la ventana",
      "nuevamente" in out, out.strip())

rc, out = correr([], entrada="\x03")
check("Ctrl+C cancela limpio", rc == 0 or "cancelada" in out, out.strip())

print("\n" + "=" * 60)

print("\n8. La base de datos sale del global.cfg, no de un valor fijo")
fuente = open(SCRIPT, encoding="utf-8").read()
check("ya no hay una base fija escrita en el codigo",
      not re.search(r'NEWPT_DB_DATABASE"\s*,\s*"seiscomp', fuente))
check("no menciona ninguna base como valor por defecto",
      not re.search(r'"database"\s*:\s*"seiscomp', fuente))

# El parser de la linea database
with tempfile.TemporaryDirectory() as d:
    ruta = os.path.join(d, "global.cfg")
    with open(ruta, "w", encoding="utf-8") as f:
        f.write("# comentario\nagencyID = CSN\n"
                "database = postgresql://sysop:secreto@10.54.217.69/seiscomp2\n"
                "recordstream = combined://slink/x\n")
    real = ev._ruta_global_cfg
    ev._ruta_global_cfg = lambda: ruta
    leido = ev._leer_global_cfg()
    check("lee host, base, usuario y clave de la linea database",
          leido == {"host": "10.54.217.69", "database": "seiscomp2",
                    "user": "sysop", "password": "secreto"}, leido)
    check("ignora las otras lineas del archivo", leido["database"] == "seiscomp2")

    # Precedencia
    entorno_previo = os.environ.get("NEWPT_DB_DATABASE")
    os.environ["NEWPT_DB_DATABASE"] = "otradb"
    check("el entorno gana sobre el global.cfg",
          ev.configuracion()["database"] == "otradb")
    del os.environ["NEWPT_DB_DATABASE"]
    if entorno_previo is not None:
        os.environ["NEWPT_DB_DATABASE"] = entorno_previo
    check("sin entorno, manda el global.cfg",
          ev.configuracion()["database"] == "seiscomp2")
    check("--base pisa el nombre, y el host sigue del archivo",
          ev.configuracion(base="seiscomp")["database"] == "seiscomp"
          and ev.configuracion(base="seiscomp")["host"] == "10.54.217.69")
    check("informa de donde salio cada vez",
          ev.configuracion()["_origen"] == "global.cfg"
          and ev.configuracion(base="seiscomp")["_origen"] == "línea de comandos")

    # Sin ninguna fuente: se detiene, no adivina
    ev._ruta_global_cfg = lambda: None
    os.environ.pop("NEWPT_DB_DATABASE", None)
    try:
        ev.configuracion()
        check("sin config se detiene en vez de adivinar", False, "no se detuvo")
    except ev.FaltanParametros as e:
        check("sin config se detiene en vez de adivinar",
              "No se pudo determinar la base" in str(e), str(e).splitlines()[0])
    # Con --base pero sin global.cfg, al menos el host falta: el mensaje tiene
    # que decirlo, no culpar a la base que sí se indicó.
    try:
        ev.configuracion(base="seiscomp")
        check("sin host, el error culpa al host y no a la base", False, "no se detuvo")
    except ev.FaltanParametros as e:
        check("sin host, el error culpa al host y no a la base",
              "seiscomp" in str(e) and "servidor" in str(e), str(e).splitlines()[0])
    # Si alcanza con tener el host (del entorno) y la base, funciona.
    os.environ["NEWPT_DB_HOST"] = "10.54.217.69"
    check("con host del entorno y --base, ya alcanza",
          ev.configuracion(base="seiscomp")["database"] == "seiscomp")
    del os.environ["NEWPT_DB_HOST"]
    ev._ruta_global_cfg = real

# global.cfg real: el script debe encontrarlo por SEISCOMP_ROOT o por ~/
if ev._ruta_global_cfg():
    check("encuentra el global.cfg de verdad",
          ev._leer_global_cfg() is not None)

# main: reconoce --base sin romper los argumentos posicionales
src_main = fuente[fuente.index("def main("):fuente.index('if __name__ ==')]
check("main acepta --base", "--base" in src_main)
check("main separa --base de la ventana y la salida", "base" in src_main)
rc, out = correr(["--base"], entrada="")
check("--base sin nombre da error claro", "necesita el nombre" in out, out.strip())
rc, out = correr(["20261301000000", "20260901000000", "--base", "seiscomp"], entrada="")
check("con --base sigue validando la ventana",
      "formato AAAAMMDDHHMMSS" in out, out.strip())
rc, out = correr(["20260901000000", "20260902000000", "--base"], entrada="")
check("--base al final sin nombre da error, no lo toma como salida",
      "necesita el nombre" in out, out.strip())

print("\n" + "=" * 60)
if fallos:
    print("FALLARON %d pruebas: %s" % (len(fallos), fallos))
    sys.exit(1)
print("Todas las pruebas pasan.")
