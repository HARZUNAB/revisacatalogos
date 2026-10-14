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

Cada *caso* es una carpeta ``casos/<caso>/``. Los archivos de primer nivel son
las fixtures que se pasan por argumento (copiadas a ``entrada/``). Si el caso
tiene una subcarpeta ``cwd/``, su contenido se copia a la raíz del temporal:
es para los scripts que leen rutas fijas relativas al cwd y que ``app.py``
invoca **sin argumentos** (p. ej. ``revisaselect.py`` y su ``select.out``). El
script se corre como subproceso (igual que app.py): ``RV_PROG=1``, en un
directorio temporal. Se corre dos veces: en **modo app** (sin
``RV_ENTREGABLES``) y en **modo entregables** (con ``RV_ENTREGABLES=1``).

Uso:
    python3 arnes_refactor.py capturar  <script> <caso> -- <args...>
    python3 arnes_refactor.py verificar <script> <caso> -- <args...>
    python3 arnes_refactor.py capturar  <script> <caso>        # caso con cwd/

Ejemplos:
    python3 tests/ampliacion/scripts/arnes_refactor.py capturar compara.py \\
        compara -- eventquery.csv local.csv
    python3 tests/ampliacion/scripts/arnes_refactor.py capturar revisaselect.py \\
        revisaselect

El golden queda en ``golden/<caso>.txt`` (versionado: es la regresión permanente;
el nombre del caso ya es único por módulo). Es una herramienta local: correr el
script de verdad necesita sus dependencias (p. ej. pandas), que el CI no instala.
"""

import argparse
import datetime
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
_FECHA_RE = re.compile(r"\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}")

# Un timestamp que cae dentro de esta ventana del momento de la corrida es
# "volátil" (una fecha de impresión), no un dato del fixture. Las fechas de los
# casos son históricas y quedan intactas, así el golden sigue detectando
# regresiones en las fechas.
_VENTANA_VOLATIL = datetime.timedelta(days=2)


def _reemplazar_fecha(match):
    """Neutraliza la fecha solo si es un timestamp de impresión (reciente)."""
    texto = match.group(0)
    try:
        fecha = datetime.datetime.strptime(
            " ".join(texto.split()), "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return texto
    if abs(datetime.datetime.now() - fecha) <= _VENTANA_VOLATIL:
        return "<TS>"
    return texto


def _estabilizar(texto):
    """Reemplaza los timestamps volátiles por un marcador estable."""
    texto = _TIEMPO_RE.sub("<TS>", texto)
    return _FECHA_RE.sub(_reemplazar_fecha, texto)


def _normalizar(texto, tmp):
    """Vuelve estable la salida: la ruta del temporal y los timestamps."""
    return _estabilizar(texto.replace(tmp, "$CWD"))


def _hash(ruta):
    """sha256 del contenido; si es texto, con los timestamps normalizados.

    Varios scripts escriben la fecha de impresión en sus salidas (p. ej. la
    cabecera del .dat de proc_query_harz_2), así que hashear el contenido crudo
    daría un golden distinto en cada corrida. Para los binarios o lo que no
    decodifique como UTF-8 se hashea el crudo.
    """
    with open(ruta, "rb") as f:
        datos = f.read()
    try:
        texto = datos.decode("utf-8")
    except UnicodeDecodeError:
        return hashlib.sha256(datos).hexdigest()
    return hashlib.sha256(_estabilizar(texto).encode("utf-8")).hexdigest()


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


def _staging(origen, tmp):
    """Prepara el temporal con las fixtures del caso.

    Los archivos de primer nivel van a ``entrada/`` (se pasan como argumentos,
    el comportamiento de siempre). Si el caso tiene una carpeta ``cwd/``, su
    contenido se copia a la raíz del temporal, para los scripts que leen rutas
    fijas relativas al cwd y que la app invoca sin argumentos.
    """
    shutil.copytree(origen, os.path.join(tmp, "entrada"),
                    ignore=shutil.ignore_patterns("cwd"))
    dir_cwd = os.path.join(origen, "cwd")
    if os.path.isdir(dir_cwd):
        for nombre in os.listdir(dir_cwd):
            src = os.path.join(dir_cwd, nombre)
            dst = os.path.join(tmp, nombre)
            if os.path.isdir(src):
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)


def _snapshot(script, caso, args):
    """Corre el script en los dos modos y devuelve el texto del snapshot."""
    origen = os.path.join(DIR_CASOS, caso)
    if not os.path.isdir(origen):
        raise SystemExit("No existe el caso: %s" % origen)

    secciones = []
    for modo, extra in (("app", {}), ("entregables", {"RV_ENTREGABLES": "1"})):
        tmp = tempfile.mkdtemp(prefix="rcs_regr_")
        try:
            _staging(origen, tmp)
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
    tiene_cwd = os.path.isdir(os.path.join(DIR_CASOS, ns.caso, "cwd"))
    if not args and not tiene_cwd:
        raise SystemExit("Faltan las fixtures de entrada: usá '-- a.csv b.csv' "
                         "o una carpeta cwd/ en el caso.")

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
