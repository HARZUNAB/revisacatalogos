#!/usr/bin/env python3
"""
arnes_refactor.py
=================
Arnés de regresión "antes/después" para el refactor de los scripts del flujo.

La idea: los scripts que hay que refactorizar (agregarles ``main()`` y el
guard ``__main__``) hoy escriben cosas por stdout y generan archivos. Antes de
tocarlos se captura esa salida como *golden*; después del refactor se corre de
nuevo y se verifica que sea **idéntica**. Así el refactor no cambia el
comportamiento que consume ``app.py``.

Cada *caso* es una carpeta ``casos/<caso>/`` con los CSV de entrada. El script
se corre como subproceso (igual que app.py): ``RV_PROG=1``, en un directorio
temporal, con los argumentos apuntando a las fixtures copiadas en ``entrada/``.
Se corre dos veces: en **modo app** (sin ``RV_ENTREGABLES``) y en **modo
entregables** (con ``RV_ENTREGABLES=1``).

Uso:
    python3 arnes_refactor.py capturar  <script> <caso> -- <args...>
    python3 arnes_refactor.py verificar <script> <caso> -- <args...>

Ejemplo:
    python3 tests/ampliacion/scripts/arnes_refactor.py capturar compara.py \\
        compara -- eventquery.csv local.csv

El golden queda en ``golden/<caso>.txt`` (versionado: es la regresión permanente;
el nombre del caso ya es único por módulo). Es una herramienta local: correr el
script de verdad necesita sus dependencias (p. ej. pandas), que el CI no instala.
"""

import argparse
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(AQUI)))
DIR_CASOS = os.path.join(AQUI, "casos")
DIR_GOLDEN = os.path.join(AQUI, "golden")

_TIEMPO_RE = re.compile(r"\d{14}")


def _normalizar(texto, tmp):
    """Vuelve estable la salida: la ruta del temporal y los timestamps."""
    texto = texto.replace(tmp, "$CWD")
    return _TIEMPO_RE.sub("<TS>", texto)


def _hash(ruta):
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(65536), b""):
            h.update(bloque)
    return h.hexdigest()


def _manifiesto(tmp):
    """sha256 y ruta relativa de cada archivo generado, ordenado."""
    lineas = []
    for base, dirs, archivos in os.walk(tmp):
        dirs[:] = [d for d in dirs if d != "entrada"]
        for nombre in archivos:
            ruta = os.path.join(base, nombre)
            rel = os.path.relpath(ruta, tmp).replace(os.sep, "/")
            lineas.append("%s  %s" % (_hash(ruta), rel))
    return "\n".join(sorted(lineas))


def _snapshot(script, caso, args):
    """Corre el script en los dos modos y devuelve el texto del snapshot."""
    origen = os.path.join(DIR_CASOS, caso)
    if not os.path.isdir(origen):
        raise SystemExit("No existe el caso: %s" % origen)

    secciones = []
    for modo, extra in (("app", {}), ("entregables", {"RV_ENTREGABLES": "1"})):
        tmp = tempfile.mkdtemp(prefix="rcs_regr_")
        try:
            shutil.copytree(origen, os.path.join(tmp, "entrada"))
            env = dict(os.environ)
            env["RV_PROG"] = "1"
            env.update(extra)
            cmd = [sys.executable, script] + [
                os.path.join("entrada", a) for a in args]
            proc = subprocess.run(
                cmd, cwd=tmp, env=env, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, universal_newlines=True)
            stdout = _normalizar(proc.stdout, tmp)
            archivos = _manifiesto(tmp)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

        secciones.append(
            "===== modo: %s =====\n"
            "--- exit: %d ---\n"
            "--- stdout ---\n%s\n"
            "--- archivos ---\n%s\n"
            % (modo, proc.returncode, stdout, archivos))
    return "\n".join(secciones)


def _ruta_script(nombre):
    return nombre if os.path.isabs(nombre) else os.path.join(RAIZ, nombre)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("accion", choices=["capturar", "verificar"])
    p.add_argument("script", help="ruta al script (relativa a la raíz)")
    p.add_argument("caso", help="carpeta dentro de casos/")
    p.add_argument("args", nargs=argparse.REMAINDER,
                   help="nombres de las fixtures, tras '--'")
    ns = p.parse_args()

    args = ns.args
    if args and args[0] == "--":
        args = args[1:]
    if not args:
        raise SystemExit("Faltan las fixtures de entrada (usá '-- a.csv b.csv').")

    script = _ruta_script(ns.script)
    if not os.path.isfile(script):
        raise SystemExit("No existe el script: %s" % script)

    golden = os.path.join(DIR_GOLDEN, ns.caso + ".txt")
    actual = _snapshot(script, ns.caso, args)

    if ns.accion == "capturar":
        os.makedirs(DIR_GOLDEN, exist_ok=True)
        with open(golden, "w") as f:
            f.write(actual)
        print("Golden escrito:", os.path.relpath(golden, RAIZ))
        return 0

    if not os.path.isfile(golden):
        raise SystemExit("No hay golden para comparar: %s" % golden)
    with open(golden) as f:
        esperado = f.read()
    if actual == esperado:
        print("OK: la salida es idéntica al golden (%s)." % ns.caso)
        return 0

    import difflib
    diff = difflib.unified_diff(
        esperado.splitlines(), actual.splitlines(),
        fromfile="golden", tofile="actual", lineterm="")
    sys.stdout.write("\n".join(diff) + "\n")
    return 1


if __name__ == "__main__":
    sys.exit(main())
