#!/usr/bin/env python3
"""
Tests de descargas.py — lógica de interfaz (con dobles)
=======================================================
Cubre la parte de interfaz de `descargas.py` sin Tk real: la ventana que se pone
adelante, la etiqueta atenuada, los avisos, abrir la carpeta y las rutas de
descarga (`descargar_tabla`/`descargar_texto`), incluido el caso de contenido
vacío.

El diálogo real de `preguntar_formato` (que necesita pantalla) se testea en
`tests/ampliacion/gui/`. Acá solo se cubre su rama sin padre.
"""

import os
import sys
import types

import pytest

import descargas


class VentanaFalsa:
    """Doble de una ventana Tk que registra lo que le hacen."""

    def __init__(self, viewable=True, error=None):
        self.viewable = viewable
        self.error = error
        self.llamadas = []

    def _registrar(self, nombre):
        if self.error == nombre:
            raise RuntimeError("falla %s" % nombre)
        self.llamadas.append(nombre)

    def lift(self):
        self._registrar("lift")

    def focus_force(self):
        self._registrar("focus_force")

    def update_idletasks(self):
        self._registrar("update_idletasks")

    def winfo_viewable(self):
        return self.viewable

    def grab_set(self):
        self._registrar("grab_set")


class LabelFalso:
    def __init__(self, marco, **kwargs):
        self.marco = marco
        self.kw = kwargs


class TtkBoot:
    """ttkbootstrap: acepta bootstyle."""

    def Label(self, marco, **kwargs):
        return LabelFalso(marco, **kwargs)


class TtkEstandar:
    """ttk de la stdlib: rechaza bootstyle."""

    def Label(self, marco, **kwargs):
        if "bootstyle" in kwargs:
            raise TypeError("bad option 'bootstyle'")
        return LabelFalso(marco, **kwargs)


class MessageboxFalso:
    def __init__(self):
        self.llamadas = []
        self.error = None

    def showerror(self, titulo, mensaje, parent=None):
        if self.error is not None:
            raise self.error
        self.llamadas.append(("showerror", titulo, mensaje, parent))

    def showinfo(self, titulo, mensaje, parent=None):
        if self.error is not None:
            raise self.error
        self.llamadas.append(("showinfo", titulo, mensaje, parent))


@pytest.fixture
def tkinter_falso(monkeypatch):
    mod = types.ModuleType("tkinter")
    mb = MessageboxFalso()
    mod.messagebox = mb
    monkeypatch.setitem(sys.modules, "tkinter", mod)
    return mb


# --------------------------------------------------------------------------
# encima_de
# --------------------------------------------------------------------------
def test_encima_de_sin_ventana_sube_el_padre():
    padre = VentanaFalsa()
    descargas.encima_de(padre)
    assert padre.llamadas == ["lift", "focus_force"]


def test_encima_de_modal_toma_el_grab():
    padre, ventana = VentanaFalsa(), VentanaFalsa(viewable=True)
    descargas.encima_de(padre, ventana)
    assert ventana.llamadas == ["lift", "focus_force", "update_idletasks",
                                "grab_set"]
    assert padre.llamadas == []


def test_encima_de_no_mapeada_no_toma_el_grab():
    ventana = VentanaFalsa(viewable=False)
    descargas.encima_de(VentanaFalsa(), ventana)
    assert ventana.llamadas == ["lift", "focus_force", "update_idletasks"]


def test_encima_de_no_modal_no_roba_el_foco():
    ventana = VentanaFalsa()
    descargas.encima_de(VentanaFalsa(), ventana, modal=False)
    assert ventana.llamadas == ["lift"]


def test_encima_de_traga_errores():
    ventana = VentanaFalsa(error="lift")
    descargas.encima_de(VentanaFalsa(), ventana)  # no debe propagar
    assert ventana.llamadas == []


def test_encima_de_sin_objetivo_no_hace_nada():
    descargas.encima_de(None)  # no debe romper


# --------------------------------------------------------------------------
# _etiqueta_secundaria
# --------------------------------------------------------------------------
def test_etiqueta_secundaria_con_bootstyle():
    label = descargas._etiqueta_secundaria(TtkBoot(), "marco", "hola")
    assert label.kw["bootstyle"] == "secondary"
    assert label.kw["text"] == "hola"


def test_etiqueta_secundaria_fallback_ttk_estandar():
    label = descargas._etiqueta_secundaria(TtkEstandar(), "marco", "hola")
    assert label.kw["foreground"] == "#777777"
    assert "bootstyle" not in label.kw


# --------------------------------------------------------------------------
# _avisar_error / _avisar_exito
# --------------------------------------------------------------------------
def test_avisar_error(tkinter_falso):
    padre = VentanaFalsa()
    descargas._avisar_error(padre, "no se pudo")
    tipo, titulo, mensaje, parent = tkinter_falso.llamadas[0]
    assert tipo == "showerror" and mensaje == "no se pudo" and parent is padre
    assert padre.llamadas == ["lift", "focus_force"]


def test_avisar_exito(tkinter_falso, tmp_path):
    ruta = str(tmp_path / "descargas" / "x.csv")
    descargas._avisar_exito(VentanaFalsa(), ruta)
    tipo, titulo, mensaje, _ = tkinter_falso.llamadas[0]
    assert tipo == "showinfo" and "x.csv" in mensaje


def test_avisar_error_fallback_consola(tkinter_falso, capsys):
    tkinter_falso.error = RuntimeError("sin display")
    descargas._avisar_error(VentanaFalsa(), "no se pudo")
    assert "[descargas] no se pudo" in capsys.readouterr().out


def test_avisar_exito_fallback_consola(tkinter_falso, capsys, tmp_path):
    tkinter_falso.error = RuntimeError("sin display")
    descargas._avisar_exito(VentanaFalsa(), str(tmp_path / "x.csv"))
    assert "[descargas]" in capsys.readouterr().out


# --------------------------------------------------------------------------
# abrir_carpeta
# --------------------------------------------------------------------------
def test_abrir_carpeta_inexistente(tmp_path):
    assert descargas.abrir_carpeta(str(tmp_path / "no_existe")) is False


def test_abrir_carpeta_linux(monkeypatch, tmp_path):
    llamadas = []
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(descargas.subprocess, "Popen",
                        lambda args: llamadas.append(args))
    assert descargas.abrir_carpeta(str(tmp_path)) is True
    assert llamadas == [["xdg-open", str(tmp_path)]]


def test_abrir_carpeta_mac(monkeypatch, tmp_path):
    llamadas = []
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(descargas.subprocess, "Popen",
                        lambda args: llamadas.append(args))
    assert descargas.abrir_carpeta(str(tmp_path)) is True
    assert llamadas == [["open", str(tmp_path)]]


def test_abrir_carpeta_falla(monkeypatch, tmp_path, capsys):
    def revienta(args):
        raise OSError("no hay explorador")

    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(descargas.subprocess, "Popen", revienta)
    assert descargas.abrir_carpeta(str(tmp_path)) is False
    assert "no se pudo abrir" in capsys.readouterr().out


# --------------------------------------------------------------------------
# descargar_tabla
# --------------------------------------------------------------------------
def test_descargar_tabla_sin_filas_no_pregunta(monkeypatch, cwd_tmp):
    def no_debe_llamarse(padre):
        raise AssertionError("no debería preguntar el formato")

    monkeypatch.setattr(descargas, "preguntar_formato", no_debe_llamarse)
    assert descargas.descargar_tabla(VentanaFalsa(), ["a"], [], "x") is None


def test_descargar_tabla_cancelada(monkeypatch, cwd_tmp):
    monkeypatch.setattr(descargas, "preguntar_formato", lambda padre: None)
    assert descargas.descargar_tabla(VentanaFalsa(), ["a"], [[1]], "x") is None


def test_descargar_tabla_ok(monkeypatch, cwd_tmp):
    avisos = []
    monkeypatch.setattr(descargas, "preguntar_formato", lambda padre: "csv")
    monkeypatch.setattr(descargas, "_avisar_exito",
                        lambda padre, ruta: avisos.append(ruta))
    ruta = descargas.descargar_tabla(VentanaFalsa(), ["a", "b"], [[1, 2]], "etiq")
    assert os.path.isfile(ruta)
    assert avisos == [ruta]


def test_descargar_tabla_error_de_escritura(monkeypatch, cwd_tmp):
    errores = []
    monkeypatch.setattr(descargas, "preguntar_formato", lambda padre: "csv")

    def falla(*a, **k):
        raise OSError("disco lleno")

    monkeypatch.setattr(descargas, "exportar_tabla", falla)
    monkeypatch.setattr(descargas, "_avisar_error",
                        lambda padre, mensaje: errores.append(mensaje))
    assert descargas.descargar_tabla(VentanaFalsa(), ["a"], [[1]], "x") is None
    assert errores and "disco lleno" in errores[0]


def test_descargar_tabla_sin_aviso(monkeypatch, cwd_tmp):
    avisos = []
    monkeypatch.setattr(descargas, "preguntar_formato", lambda padre: "csv")
    monkeypatch.setattr(descargas, "_avisar_exito",
                        lambda padre, ruta: avisos.append(ruta))
    descargas.descargar_tabla(VentanaFalsa(), ["a"], [[1]], "x", aviso=False)
    assert avisos == []


# --------------------------------------------------------------------------
# descargar_texto
# --------------------------------------------------------------------------
def test_descargar_texto_sin_lineas(cwd_tmp):
    assert descargas.descargar_texto(VentanaFalsa(), [], "x") is None


def test_descargar_texto_ok(monkeypatch, cwd_tmp):
    avisos = []
    monkeypatch.setattr(descargas, "_avisar_exito",
                        lambda padre, ruta: avisos.append(ruta))
    ruta = descargas.descargar_texto(VentanaFalsa(), ["uno", "dos"], "informe")
    assert ruta.endswith(".txt") and os.path.isfile(ruta)
    assert avisos == [ruta]


def test_descargar_texto_error_de_escritura(monkeypatch, cwd_tmp):
    errores = []
    monkeypatch.setattr(descargas, "exportar_lineas",
                        lambda *a, **k: (_ for _ in ()).throw(OSError("x")))
    monkeypatch.setattr(descargas, "_avisar_error",
                        lambda padre, mensaje: errores.append(mensaje))
    assert descargas.descargar_texto(VentanaFalsa(), ["uno"], "x") is None
    assert errores


# --------------------------------------------------------------------------
# preguntar_formato: rama sin display
# --------------------------------------------------------------------------
def test_preguntar_formato_sin_padre():
    assert descargas.preguntar_formato(None) is None
