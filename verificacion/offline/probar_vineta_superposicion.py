# -*- coding: utf-8 -*-
"""
Prueba de la viñeta de soluciones superpuestas: debe mostrar la identificación
del evento (id y fecha/hora de NUESTRA referencia) para no depender de buscar el
id en el catálogo.
"""
import os
import sys

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, RAIZ)
import plotear  # noqa: E402

fallos = []


def check(nombre, ok, detalle=None):
    print("  %-4s %s" % ("OK" if ok else "FALLA", nombre))
    if not ok:
        fallos.append(nombre)
        if detalle is not None:
            print("        -> %r" % (detalle,))


def ev(rol, prof=30, mag=5.0, tipo="ML", ag=None):
    e = {"rol": rol, "prof": prof, "magnitud": mag, "tipo": tipo,
         "latitud": -33.0, "longitud": -71.0, "fecha hora": "2026-10-02 12:47:27"}
    if ag:
        e["agencia"] = ag
    return e


print("\n1. Con referencia (id + fecha/hora)")
ref = ev("referencia")
ref["id"] = 40
ag = ev("agencia", prof=32, mag=5.1, ag="EMSC")
txt = plotear._texto_superposicion([ref, ag], ref)
lineas = txt.split("\n")
check("encabezado de superposición", lineas[0].startswith("Soluciones superpuestas"), lineas[0])
check("2a línea con id y fecha/hora",
      lineas[1] == "id: 40 · 2026-10-02 12:47:27", lineas[1])
check("lista las fuentes", "CSN" in txt and "EMSC" in txt, txt)

print("\n2. Referencia sin id -> solo fecha/hora")
ref2 = ev("referencia")
txt2 = plotear._texto_superposicion([ref2, ag], ref2).split("\n")
check("sin id, la 2a línea es la fecha/hora",
      txt2[1] == "2026-10-02 12:47:27" and not txt2[1].startswith("id:"), txt2[1])

print("\n3. Sin referencia -> no inventa identificación")
txt3 = plotear._texto_superposicion([ag], None).split("\n")
check("sin referencia, la 2a línea ya es una fuente",
      txt3[0].startswith("Soluciones superpuestas")
      and ("EMSC" in txt3[1]) and not txt3[1].startswith("id:"), txt3)

print("\n4. Referencia sin fecha -> solo id")
ref4 = ev("referencia")
ref4["id"] = 7
ref4["fecha hora"] = ""
txt4 = plotear._texto_superposicion([ref4, ag], ref4).split("\n")
check("sin fecha, la 2a línea es solo el id",
      txt4[1] == "id: 7", txt4[1])

print("\n" + "=" * 60)
if fallos:
    print("FALLARON %d pruebas: %s" % (len(fallos), fallos))
    sys.exit(1)
print("Todas las pruebas pasan.")
