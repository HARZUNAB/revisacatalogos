#!/usr/bin/env python3
"""
Tests de compara.py — funciones puras
=====================================
Cubre los ayudantes puros de `compara.py` (`_parsear_fecha_hora`, `_magnitud`,
`_borrar`) que quedan accesibles una vez que el script deja de ejecutarse al
importarse. La lógica completa de `comparar` se valida con el golden del arnés
(`arnes_refactor.py`).
"""

import datetime

import pytest


# --------------------------------------------------------------------------
# _parsear_fecha_hora
# --------------------------------------------------------------------------
def test_fecha_un_espacio(compara):
    assert compara._parsear_fecha_hora("2020-01-01 00:00:00") == \
        datetime.datetime(2020, 1, 1, 0, 0, 0)


def test_fecha_dos_espacios(compara):
    assert compara._parsear_fecha_hora("2020-01-01  12:34:56") == \
        datetime.datetime(2020, 1, 1, 12, 34, 56)


def test_normaliza_el_segundo_60(compara):
    # eventquery llega con segundos inválidos; 60 se lleva a 59.
    assert compara._parsear_fecha_hora("2020-01-01 00:00:60") == \
        datetime.datetime(2020, 1, 1, 0, 0, 59)


def test_fecha_invalida_revienta(compara):
    with pytest.raises(ValueError):
        compara._parsear_fecha_hora("no es una fecha")


# --------------------------------------------------------------------------
# _magnitud
# --------------------------------------------------------------------------
def test_magnitud_numerica(compara):
    assert compara._magnitud("4.5") == 4.5
    assert compara._magnitud(" 3.0 ") == 3.0


@pytest.mark.parametrize("valor", ["", "   ", None, "abc", "M4.5"])
def test_magnitud_sin_dato_o_invalida(compara, valor):
    assert compara._magnitud(valor) is None


# --------------------------------------------------------------------------
# _borrar
# --------------------------------------------------------------------------
def test_borrar_archivo_existente(compara, tmp_path):
    f = tmp_path / "x.csv"
    f.write_text("hola")
    compara._borrar(str(f))
    assert not f.exists()


def test_borrar_inexistente_no_revienta(compara, tmp_path):
    compara._borrar(str(tmp_path / "no_existe.csv"))  # no debe levantar


# --------------------------------------------------------------------------
# catálogo publicado vacío
# --------------------------------------------------------------------------
def test_sin_catalogo_publicado_no_genera_no_publicados(compara, cwd_tmp,
                                                        capsys):
    import csv
    import os

    os.makedirs("datos", exist_ok=True)
    os.makedirs("informes", exist_ok=True)
    publicado = "datos/publico.csv"
    local = "datos/local.csv"
    with open(publicado, "w", newline="") as f:
        csv.writer(f).writerow(
            ["n", "fecha", "lat", "lon", "prof", "mag", "tipo", "ref", "perc"])
    with open(local, "w", newline="") as f:
        escritor = csv.writer(f)
        escritor.writerow(["", "Fecha_Hora", "Latitud", "Longitud", "Prof.",
                           "Mag.", "Tipo_mag.", "Analista"])
        escritor.writerow([0, "2026-01-01  00:00:00", "-33.0", "-71.0",
                           "10.0", "3.0", "ML", "ana"])
    # Derivados viejos que deben desaparecer.
    with open("datos/no_pub_desde_2_5_estricto.csv", "w") as f:
        f.write("viejo\n")
    with open("datos/atribucion_seisan.csv", "w") as f:
        f.write("viejo\n")

    compara.main(["compara.py", publicado, local])

    assert not os.path.exists("datos/no_pub_desde_2_5_estricto.csv")
    assert not os.path.exists("datos/atribucion_seisan.csv")
    assert os.path.exists("informes/no_act_estricto.txt")
    assert os.path.exists("informes/no_act_amplio.txt")
    assert "no se generan no publicados" in capsys.readouterr().out
