# -*- coding: utf-8 -*-
"""
Prueba de la cobertura de agencias (ventana solicitada + real por agencia),
sin base ni red.

Cubre: lectura del período/magnitud guardados, min/max de 'Fecha_Hora' por
agencia (con milisegundos de GFZ), el rezago respecto del fin solicitado y la
degradación cuando falta el CSV de una agencia.
"""
import os
import sys
import json
import shutil
import tempfile

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, RAIZ)
import app  # noqa: E402

fallos = []


def check(nombre, ok, detalle=None):
    print("  %-4s %s" % ("OK" if ok else "FALLA", nombre))
    if not ok:
        fallos.append(nombre)
        if detalle is not None:
            print("        -> %r" % (detalle,))


def _escribir(ruta, contenido):
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(contenido)


ENCAB = ("id,Fecha_Hora,Latitud,Longitud,Prof.,Mag.,Tipo Mag.,Referencia,Agencia\n")


def _fila(i, fecha, ag):
    return "%d,%s,-33.0,-71.0,30,5.0,m,ref,%s\n" % (i, fecha, ag)


base = tempfile.mkdtemp(prefix="rv_cob_")
cwd_previo = os.getcwd()
try:
    datos = os.path.join(base, "datos", "agencias")
    _escribir(os.path.join(datos, "estado.json"), json.dumps({
        "consulta": {"modo": "ventana",
                     "periodo": ["20261001000000", "20261009173500"],
                     "minmag": 2.5, "agencias": ["EMSC", "USGS", "GFZ"],
                     "referencia": "eventquery",
                     "timestamp": "2026-10-13 23:32:18"}}))
    # EMSC: cubre casi toda la ventana.
    _escribir(os.path.join(datos, "consultaapi_EMSC.csv"), ENCAB
              + _fila(1, "2026-10-01 00:08:22", "EMSC")
              + _fila(2, "2026-10-09 17:30:07", "EMSC"))
    # USGS: termina antes (rezago).
    _escribir(os.path.join(datos, "consultaapi_NEIC.csv"), ENCAB
              + _fila(1, "2026-10-02 17:28:18", "USGS")
              + _fila(2, "2026-10-08 05:35:56", "USGS"))
    # GFZ: con milisegundos y más rezago.
    _escribir(os.path.join(datos, "consultaapi_GFZ.csv"), ENCAB
              + _fila(1, "2026-10-02 17:28:17.780", "GFZ")
              + _fila(2, "2026-10-07 15:46:15.123", "GFZ"))
    os.chdir(base)
    o = app.App.__new__(app.App)
    cob = o._cobertura_agencias(["EMSC", "USGS", "GFZ"])

    print("\n1. Ventana solicitada")
    sol = cob["solicitada"]
    check("desde solicitado en formato correcto",
          sol["desde"] == "2026-10-01 00:00:00", sol["desde"])
    check("hasta solicitado en formato correcto",
          sol["hasta"] == "2026-10-09 17:35:00", sol["hasta"])
    check("magnitud mínima conservada", sol["minmag"] == 2.5, sol["minmag"])

    print("\n2. Ventana real por agencia")
    por_ag = {f["agencia"]: f for f in cob["agencias"]}
    check("EMSC: primer/último evento",
          por_ag["EMSC"]["desde"] == "2026-10-01 00:08:22"
          and por_ag["EMSC"]["hasta"] == "2026-10-09 17:30:07",
          por_ag["EMSC"])
    check("EMSC: cuenta 2 eventos", por_ag["EMSC"]["eventos"] == 2,
          por_ag["EMSC"]["eventos"])
    check("EMSC: sin rezago (termina cerca del fin)",
          por_ag["EMSC"]["rezago"] == "", por_ag["EMSC"]["rezago"])
    check("USGS: rezago ~1.5 d",
          por_ag["USGS"]["rezago"] == "1.5 d", por_ag["USGS"]["rezago"])
    check("GFZ: recorta milisegundos",
          por_ag["GFZ"]["hasta"] == "2026-10-07 15:46:15", por_ag["GFZ"])
    check("GFZ: rezago ~2.1 d",
          por_ag["GFZ"]["rezago"] == "2.1 d", por_ag["GFZ"]["rezago"])

    print("\n3. Degradación si falta el CSV de una agencia")
    os.remove(os.path.join(datos, "consultaapi_NEIC.csv"))
    cob2 = o._cobertura_agencias(["EMSC", "USGS", "GFZ"])
    por_ag2 = {f["agencia"]: f for f in cob2["agencias"]}
    check("USGS sin datos -> 0 eventos y campos vacíos",
          por_ag2["USGS"]["eventos"] == 0
          and por_ag2["USGS"]["desde"] == ""
          and por_ag2["USGS"]["hasta"] == "", por_ag2["USGS"])

    print("\n4. Parseo de fechas")
    check("_fecha_desde14 válido",
          app.App._fecha_desde14("20261001000000") == "2026-10-01 00:00:00")
    check("_fecha_desde14 inválido -> ''",
          app.App._fecha_desde14("nada") == "")
    check("_fecha_utc acepta milisegundos",
          app.App._fecha_utc("2026-10-07 15:46:15.123") is not None)
finally:
    os.chdir(cwd_previo)
    shutil.rmtree(base, ignore_errors=True)

print("\n" + "=" * 60)
if fallos:
    print("FALLARON %d pruebas: %s" % (len(fallos), fallos))
    sys.exit(1)
print("Todas las pruebas pasan.")
