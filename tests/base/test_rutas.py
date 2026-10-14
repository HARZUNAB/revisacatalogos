#!/usr/bin/env python3
"""
Tests de rutas.py
=================
Cubre la creación de carpetas de salida, las rutas ``p_*`` y el mecanismo de
entregables (escritura real vs. descarte), que es lo que decide si el análisis
deja o no archivos que nadie pidió.
"""

import os

import rutas


# --------------------------------------------------------------------------
# Carpetas y rutas p_*
# --------------------------------------------------------------------------
def test_asegurar_dirs_crea_todas_las_carpetas(cwd_tmp):
    rutas.asegurar_dirs()
    for d in rutas.DIRS:
        assert os.path.isdir(os.path.join(str(cwd_tmp), d))


def test_p_datos_crea_y_devuelve_ruta(cwd_tmp):
    ruta = rutas.p_datos("salida.csv")
    assert ruta == os.path.join("datos", "salida.csv")
    assert os.path.isdir("datos")


def test_todas_las_p_crean_su_carpeta(cwd_tmp):
    casos = [
        (rutas.p_datos, "datos"),
        (rutas.p_informes, "informes"),
        (rutas.p_ploteo, "ploteo"),
        (rutas.p_trabajo, "trabajo"),
        (rutas.p_descargas, "descargas"),
    ]
    for funcion, carpeta in casos:
        ruta = funcion("x.txt")
        assert ruta == os.path.join(carpeta, "x.txt")
        assert os.path.isdir(carpeta)


# --------------------------------------------------------------------------
# con_entregables
# --------------------------------------------------------------------------
def test_con_entregables_activado(con_entregables):
    assert rutas.con_entregables() is True


def test_con_entregables_desactivado(sin_entregables):
    assert rutas.con_entregables() is False


# --------------------------------------------------------------------------
# entregable: real vs. descarte
# --------------------------------------------------------------------------
def test_entregable_desactivado_devuelve_descarte(cwd_tmp, sin_entregables):
    destino = rutas.entregable("no_debe_crearse.txt")
    assert isinstance(destino, rutas.TextoDescartado)
    with destino as f:
        f.write("algo")
    assert not os.path.exists("descargas/no_debe_crearse.txt")


def test_entregable_activado_escribe_el_archivo(cwd_tmp, con_entregables):
    with rutas.entregable("si.txt") as f:
        f.write("hola")
    ruta = os.path.join("descargas", "si.txt")
    assert os.path.isfile(ruta)
    with open(ruta) as f:
        assert f.read() == "hola"


def test_texto_descartado_acepta_la_interfaz_de_archivo():
    descarte = rutas.TextoDescartado()
    assert descarte.name == "(entregables desactivados)"
    assert descarte.write("abcd") == 4
    assert descarte.write("") == 0
    # No levanta al usarlo como context manager.
    with descarte:
        descarte.write("x")
    assert descarte.flush() is None
    assert descarte.close() is None
