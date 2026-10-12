# -*- coding: utf-8 -*-
"""Pruebas del verificador de entorno (nivel proyecto, sin tocar la base real)."""
import importlib.util
import os
import sys
import tempfile

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, RAIZ)
_spec = importlib.util.spec_from_file_location(
    "ve_", os.path.join(RAIZ, "verifica_entorno.py"))
ve = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ve)

fallos = []


def check(nombre, ok, detalle=None):
    print("  %-4s %s" % ("OK" if ok else "FALLA", nombre))
    if not ok:
        fallos.append(nombre)
        if detalle is not None:
            print("        -> %r" % (detalle,))


print("\n1. El entorno virtual")
r = ve.verificar_venv()
check("detecta que estamos en un venv", r["ok"] is True, r["detalle"])
check("dice cuál es el venv", ".venv" in r["detalle"], r["detalle"])
check("no avisa nada cuando todo está bien", r["aviso"] == "", r["aviso"])

print("\n2. Los paquetes de requirements.txt")
r = ve.verificar_requirements()
check("el manifiesto se puede leer", r["detalle"] != "" and "no se pudo leer"
      not in r["detalle"], r["detalle"])
check("están todos en la versión pedida", r["ok"] is True, r.get("distintas"))
check("faltantes vacío", r["faltantes"] == [], r["faltantes"])

with tempfile.TemporaryDirectory() as d:
    ruta = os.path.join(d, "req.txt")
    with open(ruta, "w", encoding="utf-8") as f:
        f.write("# comentario\npandas==%s\nnumpy==0.0.1\nno_existe==1.0\n"
                % ve._version_instalada("pandas"))
    r = ve.verificar_requirements(ruta)
    check("detecta un paquete ausente", r["faltantes"] == ["no_existe"], r["faltantes"])
    check("detecta una versión que no coincide",
          any("numpy" in d for d in r["distintas"]), r["distintas"])
    check("no se queja del que está bien",
          not any("pandas" in d for d in r["distintas"]), r["distintas"])
    check("el resultado no es ok si hay algo mal", r["ok"] is False)

    # Un requisito sin pin solo se comprueba que esté instalado
    ruta2 = os.path.join(d, "req2.txt")
    with open(ruta2, "w", encoding="utf-8") as f:
        f.write("pandas\n")
    r = ve.verificar_requirements(ruta2)
    check("un requisito sin pin solo checa que esté", r["ok"] is True, r)

print("\n3. tkinter (lo que no se arregla con pip)")
r = ve.verificar_tkinter()
check("tkinter está disponible en este entorno", r["ok"] is True, r["detalle"])
check("informa la versión de Tcl/Tk", "Tcl/Tk" in r["detalle"], r["detalle"])
check("menciona el paquete del sistema cuando falta",
      "python3-tk" in ve.PAQUETES_TKINTER.values()
      or "python3-tkinter" in ve.PAQUETES_TKINTER.values(),
      ve.PAQUETES_TKINTER)

print("\n4. La base de datos (sin escribir nada)")
# Host que por definición no resuelve (RFC 2606), así no se toca la red real
r = ve.verificar_base({"host": "no-resuelve.invalid", "database": "x",
                       "user": "u", "password": "p"})
check("un host irresoluble se reporta como problema", r["ok"] is False)
check("el aviso es accionable", "resolver" in r["aviso"] or "red" in r["aviso"],
      r["aviso"][:60])
# Si la configuración no se puede leer, degrada sin reventar
r = ve.verificar_base({"host": "no-resuelve.invalid", "database": "x",
                       "user": "u", "password": "p", "_origen": "prueba"})
check("no crashea con una config mínima", isinstance(r, dict) and "ok" in r, r)

print("\n5. El informe agrupa y decide")
inf = ve.informe()
check("devuelve revisiones y faltan", "revisiones" in inf and "faltan" in inf)
nombres = [n for n, _ in inf["revisiones"]]
check("son las cuatro del entorno",
      nombres == ["venv", "requisitos", "tkinter", "base"], nombres)
check("no incluye la revisión de archivos (no es del entorno)",
      "csv" not in nombres and not hasattr(ve, "verificar_csv"),
      [x for x in dir(ve) if x.startswith("verificar_")])
check("en un entorno sano no falta nada", inf["ok"] is True, inf["faltan"])

print("\n6. Lo único específico de SeisComp que queda es un mensaje")
# verificar_base menciona al admin de SeisComp en el error de permisos, lo cual
# está bien: es un mensaje, no una dependencia. Lo que no debe pasar es que el
# verificador importe la funcionalidad.
fuente = open(os.path.join(RAIZ, "verifica_entorno.py"), encoding="utf-8").read()
check("el verificador no tiene la búsqueda de archivos",
      "verificar_csv" not in fuente and "_fases" not in fuente)
check("pero sí puede pedir la config al exportador (para no duplicarla)",
      "import exporta_ventana_seiscomp" in fuente)

print("\n7. La interfaz de SeisComp no depende del verificador")
fuente_gui = open(os.path.join(RAIZ, "revisa_seiscomp.py"),
                  encoding="utf-8").read()
check("la interfaz no importa el verificador de entorno",
      "verifica_entorno" not in fuente_gui,
      [x for x in dir() if "verifica" in x] if "verifica" in fuente_gui else "")
check("busca sus propios archivos", "_pares_disponibles" in fuente_gui
      and "seiscomp_" in fuente_gui)

print("\n" + "=" * 60)
if fallos:
    print("FALLARON %d pruebas: %s" % (len(fallos), fallos))
    sys.exit(1)
print("Todas las pruebas pasan.")
