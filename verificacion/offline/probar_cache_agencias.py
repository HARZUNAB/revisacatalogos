# -*- coding: utf-8 -*-
"""
Prueba de la reutilización de la comparación de agencias (sin base ni red).

Cubre el caso que se repetía siempre: arrancar en modo catálogo explícito
(sin estado.json), donde `self.periodo` queda vacío. La caché debe inferir el
período con `_periodo()` (del nombre de los archivos) y, si los insumos no
cambiaron, considerar la comparación «al día».
"""
import os
import sys
import json
import shutil
import tempfile
import datetime

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


INI = "20260101000000"
FIN = "20260131235959"
AGS = ["EMSC", "USGS", "GFZ"]


def _escribir(ruta, contenido, mtime=None):
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(contenido)
    if mtime is not None:
        os.utime(ruta, (mtime, mtime))


def _armar_escenario(base):
    """Deja el CWD con los archivos como tras una comparación exitosa."""
    # El nombre de un archivo determinan el período inferido (select_*.out).
    _escribir(os.path.join(base, "select_%s_%s.out" % (INI, FIN)), "")
    ahora = datetime.datetime.utcnow().timestamp()
    datos = os.path.join(base, "datos")
    _escribir(os.path.join(datos, "eventos_eventquery.json"), "[]",
              mtime=ahora - 300)
    for ag in AGS:
        _escribir(os.path.join(datos, "eventos_agencia_%s.json" % ag), "[]",
                  mtime=ahora - 200)
    for ag in AGS:
        _escribir(os.path.join(datos, "agencias",
                               "consultaapi_%s.csv" % app.AGENCIAS_EXTERNAS[ag]),
                  "", mtime=ahora - 250)
    _escribir(os.path.join(datos, "comparacion_agencias.json"), "[]",
              mtime=ahora - 100)
    estado = {
        "consulta": {
            "modo": "ventana",
            "periodo": [INI, FIN],
            "minmag": 2.5,
            "agencias": AGS,
            "referencia": "eventquery",
            "timestamp": datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        },
        "comparacion": {"minmag": 2.5, "agencias": AGS,
                        "referencia": "eventquery"},
    }
    _escribir(os.path.join(datos, "agencias", "estado.json"),
              json.dumps(estado))


cwd_previo = os.getcwd()
base = tempfile.mkdtemp(prefix="rv_cache_agencias_")
try:
    _armar_escenario(base)
    os.chdir(base)

    # App sin __init__: los métodos de la caché solo usan el CWD y self.periodo.
    o = app.App.__new__(app.App)
    o.periodo = (None, None)  # como al arrancar con catálogo explícito

    print("\n1. Inferencia del período sin estado.json")
    check("_periodo() infiere del nombre del archivo",
          o._periodo() == (INI, FIN), o._periodo())

    print("\n2. La comparación se reutiliza cuando nada cambió")
    check("_comparacion_al_dia() es True con período inferido",
          o._comparacion_al_dia(2.5, AGS, "ventana", "eventquery") is True)
    check("_consulta_agencias_al_dia() es True (mismos CSV)",
          o._consulta_agencias_al_dia(2.5, AGS, "ventana", [INI, FIN]) is True)

    print("\n3. Cambió un insumo -> deja de estar al día")
    ahora = datetime.datetime.utcnow().timestamp()
    os.utime(os.path.join("datos", "eventos_eventquery.json"),
             (ahora + 50, ahora + 50))
    check("_comparacion_al_dia() es False si el eventquery es más nuevo",
          o._comparacion_al_dia(2.5, AGS, "ventana", "eventquery") is False)

    print("\n4. Cambió un parámetro -> deja de estar al día")
    # Se restaura el insumo y se prueba con otra magnitud mínima.
    os.utime(os.path.join("datos", "eventos_eventquery.json"),
             (ahora - 300, ahora - 300))
    check("_comparacion_al_dia() es False con otra magnitud",
          o._comparacion_al_dia(3.0, AGS, "ventana", "eventquery") is False)
    check("_comparacion_al_dia() es False con otro modo",
          o._comparacion_al_dia(2.5, AGS, "ahora", "eventquery") is False)

    print("\n5. Falta el CSV de una agencia -> hay que reconsultar")
    os.remove(os.path.join("datos", "agencias", "consultaapi_EMSC.csv"))
    check("_consulta_agencias_al_dia() es False si falta un CSV",
          o._consulta_agencias_al_dia(2.5, AGS, "ventana", [INI, FIN]) is False)

    print("\n6. «Hasta ahora» con inicio elegido")
    desde = "20261001000000"
    estado_ahora = {
        "consulta": {
            "modo": "ahora", "periodo": [desde, "20261013220000"],
            "desde": desde, "minmag": 2.5, "agencias": AGS,
            "referencia": "eventquery",
            "timestamp": datetime.datetime.utcnow().strftime(
                "%Y-%m-%d %H:%M:%S")},
        "comparacion": {"minmag": 2.5, "agencias": AGS,
                        "referencia": "eventquery"},
    }
    with open(os.path.join("datos", "agencias", "estado.json"), "w",
              encoding="utf-8") as f:
        json.dump(estado_ahora, f)
    check("reutiliza si el inicio elegido coincide",
          o._comparacion_al_dia(2.5, AGS, "ahora", "eventquery", desde) is True)
    check("rehace si cambia el inicio elegido",
          o._comparacion_al_dia(2.5, AGS, "ahora", "eventquery",
                                "20261005000000") is False)

finally:
    os.chdir(cwd_previo)
    shutil.rmtree(base, ignore_errors=True)

print("\n" + "=" * 60)
if fallos:
    print("FALLARON %d pruebas: %s" % (len(fallos), fallos))
    sys.exit(1)
print("Todas las pruebas pasan.")
