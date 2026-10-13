# -*- coding: utf-8 -*-
"""Prueba de integracion: simula la base y comprueba que se escriben los 2 CSV."""
import csv
import importlib.util
import os
import tempfile
from datetime import datetime

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SCRIPT = os.path.join(RAIZ, "exporta_ventana_seiscomp.py")
spec = importlib.util.spec_from_file_location("ev", SCRIPT)
ev = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ev)

fallos = []


def check(nombre, ok, detalle=None):
    print("  %-4s %s" % ("OK" if ok else "FALLA", nombre))
    if not ok:
        fallos.append(nombre)
        if detalle is not None:
            print("        -> %r" % (detalle,))


EVENTO = {
    "id_evento": "csn_sc62026rccxc", "ot_utc": datetime(2026, 9, 1, 0, 38, 33),
    "magnitud": 2.9, "tipo_magnitud": "MLv", "fases": 14, "rms": 0.22,
    "azgap": 244.0, "latitud": -31.64, "longitud": -71.75,
    "profundidad_km": 28.8, "agencia": "CSN", "operador": "mary",
    "region": "Near Coast of Central Chile", "estatus": "confirmed",
}


def fase(n):
    base = {c: None for c in ev.CABECERA_FASES}
    base.update({
        "id_evento": "csn_sc62026rccxc", "id_origen": "Origin/1",
        "id_pick": "Pick/%d" % n, "red": "CL", "estacion": "RCCX%02d" % n,
        "cha": "HHZ", "fase": "Pg" if n % 2 else "Sg",
        "llegada_utc": datetime(2026, 9, 1, 0, 38, 30 + n),
        "llegada_us": 100 * n, "correccion_s": 0.0,
        "residual_s": 0.1 * n, "azimut": 10.0 * n,
        "distancia": 0.5 * n, "usada": n <= 14,
        "peso": 1.0, "polaridad": "U", "snr": 12.0,
        # La mitad de las fases NO tiene magnitud de estacion. Es el caso que
        # importa: la fila tiene que seguir saliendo igual.
        "est_lat": -31.4, "est_lon": -71.5, "est_elev": 140.0,
        "est_lugar": "Valparaiso", "est_pais": "Chile",
    })
    if n % 2:                      # con magnitud
        base.update({
            "mag_estacion": 2.85, "tipo_mag_estacion": "MLv",
            "tiene_magnitud": "Si", "mag_est_residuo": -0.05,
            "qc_estacion": "aprobado",
        })
    else:                          # sin magnitud: celdas vacias, jamas 0
        base.update({
            "tiene_magnitud": "No", "qc_estacion": "sin_evaluar",
        })
    return base


FASES = [fase(n) for n in range(1, 21)]


class CursorFalso:
    """Cursor que responde segun la base a la que se conecta."""

    def __init__(self, base):
        self.base = base
        self.consultas = []
        self._pendientes = []
        self.itersize = None
        self._servido = False

    def execute(self, sql, params=None):
        self.consultas.append((sql, params))

    def fetchall(self):
        if not self.consultas:
            return []
        sql = self.consultas[-1][0]
        if "SET TIME ZONE" in sql:
            return []
        if "min(o.m_time_value)" in sql:          # consulta de cobertura
            return [{"desde": datetime(2025, 3, 26), "hasta": datetime(2026, 9, 28)}
                    if self.base == "seiscomp" else
                    {"desde": datetime(2026, 9, 1), "hasta": datetime(2026, 9, 29)}]
        if "arrival" in sql:                       # consulta de fases
            return [dict(f) for f in FASES]
        return [dict(EVENTO)]                      # consulta de eventos

    def fetchone(self):
        filas = self.fetchall()
        return filas[0] if filas else None

    def fetchmany(self, n):
        # El cursor de servidor pide de a tantos y al final devuelve vacío. Aca
        # se finge que todo cabe en un lote: la primera llamada trae las filas
        # y las siguientes nada, para que el bucle del exportador termine.
        if self._servido:
            return []
        self._servido = True
        return self.fetchall()[:n]

    def close(self):
        pass


TODAS = []   # una por base y rol: eventos y fases


class ConexionFalsa:
    def __init__(self, base):
        self.base = base
        self.cerrada = False
        self._cursores = {}

    def cursor(self, name=None, cursor_factory=None, withhold=False):
        # Se memoiza para poder inspeccionar despues las consultas que se
        # hicieron, igual que haria un cursor real. Acepta el 'name' que usa el
        # cursor de servidor del exportador.
        clave = name or "normal"
        if clave not in self._cursores:
            self._cursores[clave] = CursorFalso(self.base)
        return self._cursores[clave]

    def close(self):
        self.cerrada = True
        TODAS.append(self)


ABIERTAS = []


def conectar_falso(config):
    c = ConexionFalsa(config["database"])
    ABIERTAS.append(config["database"])
    return c


ev.conectar = conectar_falso
ev.configuracion = lambda base=None: {
    "host": "10.54.217.69", "database": base or "seiscomp2",
    "user": "sysop", "password": "sysop", "connect_timeout": 10,
    "_origen": "global.cfg",
}
ev._bases_seiscomp = lambda: ["seiscomp", "seiscomp2"]
ev.crear_cursor = lambda conn: conn.cursor()

print("Integracion: exportar_ventana con base simulada")
import contextlib
import io as _io
with tempfile.TemporaryDirectory() as d:
    salida = os.path.join(d, "prueba.csv")
    inicio = datetime(2026, 9, 1)
    fin = datetime(2026, 9, 30, 23, 59, 59)
    _buf = _io.StringIO()
    with contextlib.redirect_stdout(_buf):
        r = ev.exportar_ventana(inicio, fin, salida)
    out = _buf.getvalue()

    check("devuelve ruta de eventos", r["ruta"] == os.path.abspath(salida), r["ruta"])
    check("devuelve ruta de fases derivada",
          r["ruta_fases"] == os.path.abspath(os.path.join(d, "prueba_fases.csv")),
          r["ruta_fases"])
    check("cuenta eventos", r["eventos"] == 1, r["eventos"])
    check("cuenta fases", r["fases"] == 20, r["fases"])
    check("informa cuantas bases combino", r["bases"] == ["seiscomp", "seiscomp2"],
          r["bases"])
    check("informa cuantos eventos traia cada una",
          r["eventos_por_base"] == {"seiscomp": 1, "seiscomp2": 1},
          r["eventos_por_base"])
    check("ambos archivos existen",
          os.path.exists(salida) and os.path.exists(os.path.join(d, "prueba_fases.csv")))
    check("se abren cinco conexiones por base (eventos, fases, no picadas,"
          " inventario y bindings)",
          ABIERTAS == ["seiscomp", "seiscomp2"] * 5,
          ABIERTAS)
    check("las diez conexiones quedaron cerradas",
          all(c.cerrada for c in TODAS) and len(TODAS) == 10, len(TODAS))
    # Una conexion por base para los eventos (zona, cobertura, tamano, eventos)
    # y otra para las fases (zona, fases). Las que siguen son las de no picadas
    # (estimacion, inventario y bindings).
    ev_cursores = [c.cursor("normal") for c in TODAS[:2]]
    fa_cursores = [c.cursor("fases") for c in TODAS[2:4]]
    check("la conexion de eventos hace 4 consultas: zona, cobertura, tamano y eventos",
          all(len(c.consultas) == 4 for c in ev_cursores),
          [len(c.consultas) for c in ev_cursores])
    check("la conexion de fases usa un cursor de servidor aparte",
          all(len(c.consultas) == 1 for c in fa_cursores),
          [len(c.consultas) for c in fa_cursores])
    check("y fija la zona horaria en la otra conexion",
          all(len(c.cursor("normal").consultas) == 1 for c in TODAS[2:4]),
          [len(c.cursor("normal").consultas) for c in TODAS[2:4]])
    check("la consulta de eventos lleva la misma ventana",
          all(c.consultas[3][1][:2] == (inicio, fin) for c in ev_cursores))
    check("la consulta de fases lleva la misma ventana",
          all(c.consultas[0][1][:2] == (inicio, fin) for c in fa_cursores))
    check("y el filtro de estado viaja en los parametros",
          all(c.consultas[3][1][2:] == ("confirmed", "confirmed")
              for c in ev_cursores),
          ev_cursores[0].consultas[3][1])
    check("avisa que la ventana sale incompleta en cada base",
          "incompleta" in out)
    check("anuncia que base manda ante un evento en dos",
          "manda: seiscomp2" in out, out)

    with open(salida, encoding="utf-8", newline="") as f:
        ev_csv = list(csv.reader(f))
    with open(os.path.join(d, "prueba_fases.csv"), encoding="utf-8", newline="") as f:
        fa_csv = list(csv.reader(f))

    check("CSV de eventos con las originales + base_datos",
          ev_csv[0] == ev.CABECERA and len(ev_csv[0]) == len(ev.CABECERA),
          ev_csv[0][:3])
    check("un solo evento, no uno por base",
          len(ev_csv) == 2, len(ev_csv) - 1)
    check("el evento dice de que base salio",
          ev_csv[1][ev.CABECERA.index("base_datos")] == "seiscomp2",
          ev_csv[1][ev.CABECERA.index("base_datos")])
    check("CSV de fases con las columnas declaradas",
          fa_csv[0] == ev.CABECERA_FASES)
    check("CSV de fases con 20 filas + cabecera", len(fa_csv) == 21, len(fa_csv))
    check("todas las filas de fase tienen las columnas declaradas",
          all(len(f) == len(ev.CABECERA_FASES) for f in fa_csv[1:]))
    check("las fases no se duplican al fusionar las dos bases",
          len(fa_csv) - 1 == 20, len(fa_csv) - 1)
    check("cada fase dice de que base salio",
          {f[ev.CABECERA_FASES.index("base_datos")] for f in fa_csv[1:]} == {"seiscomp2"},
          {f[ev.CABECERA_FASES.index("base_datos")] for f in fa_csv[1:]})
    check("todas las fases repiten el id del evento",
          len({f[0] for f in fa_csv[1:]}) == 1 and fa_csv[1][0] == "csn_sc62026rccxc")
    col = ev.CABECERA_FASES.index
    check("las 14 usadas quedan True",
          sum(1 for f in fa_csv[1:] if f[col("usada")] == "True") == 14,
          sum(1 for f in fa_csv[1:] if f[col("usada")] == "True"))
    check("estaciones distintas una por fila",
          len({f[col("estacion")] for f in fa_csv[1:]}) == 20)
    i = ev.CABECERA_FASES.index
    check("el inventario viene en cada fila",
          all(f[i("est_lat")] == "-31.4" and f[i("est_pais")] == "Chile"
              for f in fa_csv[1:]),
          fa_csv[1][i("est_lat"):])
    check("las fases con magnitud traen valor y tipo",
          all(f[i("mag_estacion")] == "2.85"
              and f[i("tipo_mag_estacion")] == "MLv"
              for f in fa_csv[1:] if f[i("tiene_magnitud")] == "Si"),
          [fa_csv[1][i("mag_estacion")], fa_csv[1][i("tipo_mag_estacion")]])
    check("las que no tienen magnitud dicen No",
          sum(1 for f in fa_csv[1:] if f[i("tiene_magnitud")] == "No") == 10)
    check("y su celda de magnitud queda VACIA, no 0",
          all(f[i("mag_estacion")] == "" and f[i("tipo_mag_estacion")] == ""
              and f[i("mag_est_residuo")] == ""
              for f in fa_csv[1:] if f[i("tiene_magnitud")] == "No"),
          [f[i(c)] for f in fa_csv[1:] if f[i("tiene_magnitud")] == "No"
           for c in ("mag_estacion", "mag_est_residuo")])
    check("pero la fila de la estacion NO se pierde: siguen las 20",
          len(fa_csv) - 1 == 20, len(fa_csv) - 1)
    check("el QC de las que no hay magnitud dice sin_evaluar, no False",
          all(f[i("qc_estacion")] == "sin_evaluar"
              for f in fa_csv[1:] if f[i("tiene_magnitud")] == "No"))
    check("los microsegundos se escriben enteros y sin truncar",
          fa_csv[1][i("llegada_us")] == "100", fa_csv[1][i("llegada_us")])
    check("no queda ninguna columna de las que SC6 no puebla",
          not {"recurso", "takeoff", "preliminar", "onset", "backazimuth",
               "estatus_pick", "metodo_amplitud", "est_tipo",
               "periodo"} & set(ev.CABECERA_FASES))

print()
if fallos:
    print("FALLARON %d: %s" % (len(fallos), fallos))
    raise SystemExit(1)
print("Integracion OK")
