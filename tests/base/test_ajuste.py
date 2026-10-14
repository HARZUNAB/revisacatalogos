#!/usr/bin/env python3
"""
Tests de ajuste.py
==================
El módulo decide cuánto puede crecer una ventana. Se prueba con una ventana
falsa (sin Tk real) que permite fijar lo que "pide" el contenido, el tope del
gestor de ventanas y la posición en pantalla.
"""

import ajuste


class VentanaFalsa:
    """Doble de prueba de una ventana Tk."""

    def __init__(self, req=(0, 0), maxsize=(1920, 1080), x=0, y=0,
                 screen=(1920, 1080), maxsize_error=False):
        self._req = req
        self._maxsize = maxsize
        self._x, self._y = x, y
        self._screen = screen
        self._maxsize_error = maxsize_error
        self.geometrias = []
        self.update_idletasks_llamado = False

    def update_idletasks(self):
        self.update_idletasks_llamado = True

    def winfo_reqwidth(self):
        return self._req[0]

    def winfo_reqheight(self):
        return self._req[1]

    def wm_maxsize(self):
        if self._maxsize_error:
            raise RuntimeError("sin gestor de ventanas")
        return self._maxsize

    def winfo_x(self):
        return self._x

    def winfo_y(self):
        return self._y

    def winfo_screenwidth(self):
        return self._screen[0]

    def winfo_screenheight(self):
        return self._screen[1]

    def geometry(self, texto=None):
        self.geometrias.append(texto)


# --------------------------------------------------------------------------
# techo
# --------------------------------------------------------------------------
def test_techo_usa_el_menor():
    # El gestor admite menos que el tope de referencia.
    assert ajuste.techo(VentanaFalsa(maxsize=(1000, 800))) == (1000, 800)


def test_techo_usa_el_tope_de_referencia():
    # El gestor admite más que el tope Full HD.
    assert ajuste.techo(VentanaFalsa(maxsize=(3000, 2000))) == (1920, 1080)


def test_techo_sin_gestor_de_ventanas():
    v = VentanaFalsa(maxsize_error=True)
    assert ajuste.techo(v) == ajuste.TOPE_MAXIMO


# --------------------------------------------------------------------------
# acotar
# --------------------------------------------------------------------------
def test_acotar_baja_al_techo():
    v = VentanaFalsa(maxsize=(1000, 800))
    assert ajuste.acotar(v, 1500, 900) == (1000, 800)


def test_acotar_no_subi_lo_que_ya_entra():
    v = VentanaFalsa(maxsize=(1920, 1080))
    assert ajuste.acotar(v, 500, 400) == (500, 400)


def test_acotar_no_baja_de_uno():
    v = VentanaFalsa(maxsize=(1920, 1080))
    assert ajuste.acotar(v, 0, 0) == (1, 1)


# --------------------------------------------------------------------------
# medir
# --------------------------------------------------------------------------
def test_medir_usa_lo_que_pide_el_contenido():
    v = VentanaFalsa(req=(500, 400))
    assert ajuste.medir(v) == (500, 400)
    assert v.update_idletasks_llamado


def test_medir_suma_holgura():
    v = VentanaFalsa(req=(500, 400))
    assert ajuste.medir(v, holgura=10) == (510, 410)


def test_medir_respeta_el_minimo():
    v = VentanaFalsa(req=(500, 400))
    assert ajuste.medir(v, minimo=(700, 600)) == (700, 600)


def test_medir_acota_al_techo():
    v = VentanaFalsa(req=(3000, 2000), maxsize=(1920, 1080))
    assert ajuste.medir(v) == (1920, 1080)


# --------------------------------------------------------------------------
# aplicar
# --------------------------------------------------------------------------
def test_aplicar_fija_el_tamano():
    v = VentanaFalsa()
    assert ajuste.aplicar(v, 800, 600) == (800, 600)
    assert v.geometrias[0] == "800x600"


def test_aplicar_no_permite_tamano_cero():
    v = VentanaFalsa()
    assert ajuste.aplicar(v, 0, 0) == (1, 1)


def test_aplicar_mueve_la_ventana_si_se_sale_de_pantalla():
    # Ventana en (1900, 1000) que al crecer se sale: debe reubicarse.
    v = VentanaFalsa(x=1900, y=1000, screen=(1920, 1080))
    ajuste.aplicar(v, 800, 600)
    posiciones = [g for g in v.geometrias if g.startswith("+")]
    assert posiciones, "debería haber reubicado la ventana"
    x, y = posiciones[-1][1:].split("+")
    assert int(x) <= 1920 - 800 - ajuste.MARGEN
    assert int(y) <= 1080 - 600 - ajuste.MARGEN


def test_ajustar_mide_y_aplica():
    v = VentanaFalsa(req=(500, 400))
    assert ajuste.ajustar(v) == (500, 400)
    assert "500x400" in v.geometrias
