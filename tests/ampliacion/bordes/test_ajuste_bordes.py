#!/usr/bin/env python3
"""
Tests de bordes de ajuste.py
============================
Casos borde de tamaño/posición que el test base no cubre: negativos, holgura y
mínimo negativos, un tope de gestor en (0,0) y una ventana en posición negativa.

El módulo no se modifica en esta tanda: el caso de posición negativa (que no se
reubica) queda anotado para revisarlo aparte.
"""

import ajuste


class VentanaFalsa:
    """Doble de prueba de una ventana Tk (mismo molde que el test base)."""

    def __init__(self, req=(0, 0), maxsize=(1920, 1080), x=0, y=0,
                 screen=(1920, 1080)):
        self._req = req
        self._maxsize = maxsize
        self._x, self._y = x, y
        self._screen = screen
        self.geometrias = []

    def update_idletasks(self):
        pass

    def winfo_reqwidth(self):
        return self._req[0]

    def winfo_reqheight(self):
        return self._req[1]

    def wm_maxsize(self):
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
# acotar / techo con valores extremos
# --------------------------------------------------------------------------
def test_acotar_negativos_cae_al_piso():
    v = VentanaFalsa(maxsize=(1920, 1080))
    assert ajuste.acotar(v, -5, -5) == (1, 1)


def test_techo_con_gestor_en_cero():
    # El gestor admite (0,0): techo lo devuelve sin clampear.
    assert ajuste.techo(VentanaFalsa(maxsize=(0, 0))) == (0, 0)
    # Y acotar aplica el piso 1.
    assert ajuste.acotar(VentanaFalsa(maxsize=(0, 0)), 500, 400) == (1, 1)


# --------------------------------------------------------------------------
# medir con holgura / mínimo negativos
# --------------------------------------------------------------------------
def test_medir_holgura_negativa_encoge():
    v = VentanaFalsa(req=(500, 400))
    assert ajuste.medir(v, holgura=-10) == (490, 390)


def test_medir_minimo_negativo_no_protege():
    v = VentanaFalsa(req=(0, 0))
    assert ajuste.medir(v, minimo=(-100, -100)) == (1, 1)


# --------------------------------------------------------------------------
# aplicar con negativos / posición negativa
# --------------------------------------------------------------------------
def test_aplicar_tamano_negativo_cae_a_uno():
    v = VentanaFalsa()
    assert ajuste.aplicar(v, -5, -5) == (1, 1)
    assert v.geometrias[0] == "1x1"


def test_aplicar_posicion_negativa_no_reubica():
    # La corrección solo mira x > max_x / y > max_y: una posición negativa
    # (arriba/izquierda) no se corrige. Comportamiento actual; revisar aparte.
    v = VentanaFalsa(x=-100, y=-100, screen=(1920, 1080))
    ajuste.aplicar(v, 800, 600)
    posiciones = [g for g in v.geometrias if g.startswith("+")]
    assert posiciones == []
