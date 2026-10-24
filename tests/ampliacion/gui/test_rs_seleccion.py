#!/usr/bin/env python3
"""
Tests de revisa_seiscomp.py — selección por casillas
=====================================================
Cubre el componente compartido de selección y su integración en abrir_tabla.
Necesita DISPLAY.
"""

import tkinter as tk
from tkinter import ttk

import pytest

import revisa_seiscomp as rs

pytestmark = pytest.mark.gui


def _boton(widget, texto):
    for hijo in widget.winfo_children():
        if isinstance(hijo, ttk.Button) and hijo.cget("text") == texto:
            return hijo
        encontrado = _boton(hijo, texto)
        if encontrado is not None:
            return encontrado
    return None


def _arbol(raiz):
    arbol = ttk.Treeview(raiz, columns=("a",), show="headings")
    arbol.heading("a", text="A")
    arbol.column("a", width=80)
    arbol.pack()
    arbol.insert("", "end", iid="0", values=("uno",))
    arbol.insert("", "end", iid="1", values=("dos",))
    return arbol


def test_seleccion_tabla_marca_y_conserva_al_repintar(raiz_tk):
    filas = [{"valor": "uno"}, {"valor": "dos"}]
    arbol = _arbol(raiz_tk)
    sel = rs.SeleccionTabla(arbol)
    sel.registrar("0", filas[0])
    sel.registrar("1", filas[1])

    assert arbol.item("0", "text") == "☐"
    sel.alternar("0")
    assert arbol.item("0", "text") == "☑"
    assert sel.seleccionadas(filas) == [filas[0]]

    arbol.delete(*arbol.get_children())
    arbol.insert("", "end", iid="0", values=("uno",))
    arbol.insert("", "end", iid="1", values=("dos",))
    sel.reiniciar()
    sel.registrar("0", filas[0])
    sel.registrar("1", filas[1])

    assert arbol.item("0", "text") == "☑"
    assert arbol.item("1", "text") == "☐"
    assert sel.contar() == 1


def test_seleccion_tabla_clic_en_la_casilla(raiz_tk):
    filas = [{"valor": "uno"}, {"valor": "dos"}]
    top = tk.Toplevel(raiz_tk)
    top.deiconify()
    arbol = _arbol(top)
    top.update()
    sel = rs.SeleccionTabla(arbol)
    sel.registrar("0", filas[0])
    sel.registrar("1", filas[1])
    top.update()

    caja = arbol.bbox("0", "#0")
    assert caja
    if isinstance(caja, str):
        caja = [int(v) for v in caja.split()]
    x, y, _ancho, _alto = caja
    arbol.event_generate("<Button-1>", x=x + 4, y=y + 4)
    top.update()

    assert sel.contar() == 1
    assert arbol.item("0", "text") == "☑"
    top.destroy()


def test_seleccion_tabla_encabezado_marca_y_desmarca_visibles(raiz_tk):
    filas = [{"valor": "uno"}, {"valor": "dos"}]
    arbol = _arbol(raiz_tk)
    sel = rs.SeleccionTabla(arbol)
    sel.registrar("0", filas[0])
    sel.registrar("1", filas[1])

    sel.alternar_visibles()
    assert all(arbol.item(iid, "text") == "☑"
               for iid in arbol.get_children())
    assert sel.contar() == 2

    sel.alternar_visibles()
    assert all(arbol.item(iid, "text") == "☐"
               for iid in arbol.get_children())
    assert sel.contar() == 0


def test_mostrar_todo_limpia_los_filtros(raiz_tk):
    filas = [
        {"a": "uno", "mag": "5.0", "latitud": "-30", "longitud": "-70"},
        {"a": "dos", "mag": "2.0", "latitud": "-40", "longitud": "-75"},
    ]
    columnas = [("a", "A", 80), ("mag", "Mag", 60),
                ("latitud", "Lat", 60), ("longitud", "Lon", 60)]
    valores = lambda fila: [fila["a"], fila["mag"], fila["latitud"],
                            fila["longitud"]]
    marco = ttk.Frame(raiz_tk)
    marco.pack()

    tabla = rs.abrir_tabla(
        marco, filas, columnas, valores,
        filtros=("texto", "mag", "latlon"), iid_por_id=False)
    arbol = tabla["arbol"]
    assert len(arbol.get_children()) == 2

    tabla["entradas"]["texto"].insert(0, "uno")
    tabla["entradas"]["mag"].insert(0, "4")
    tabla["entradas"]["lat"].insert(0, "-30")
    tabla["entradas"]["lon"].insert(0, "-70")
    _boton(marco, "Aplicar").invoke()
    raiz_tk.update()
    assert len(arbol.get_children()) == 1

    mostrar = _boton(marco, "Mostrar todo")
    assert mostrar is not None
    assert mostrar is tabla["boton_mostrar_todo"]
    mostrar.invoke()
    raiz_tk.update()

    assert len(arbol.get_children()) == 2
    assert all(not caja.get() for caja in tabla["entradas"].values())


def test_abrir_tabla_descarga_solo_las_marcadas(raiz_tk, monkeypatch):
    filas = [{"a": "uno", "b": "1"}, {"a": "dos", "b": "2"}]
    columnas = [("a", "A", 80, False), ("b", "B", 80, False)]
    valores = lambda fila: [fila["a"], fila["b"]]
    marco = ttk.Frame(raiz_tk)
    marco.pack()

    exportadas = []

    def exportar(elegidas, _valores, _columnas, _cwd, _etiqueta, **kwargs):
        exportadas.append(list(elegidas))
        return "datos/seleccion.csv"

    monkeypatch.setattr(rs, "_exportar_listado", exportar)
    tabla = rs.abrir_tabla(
        marco, filas, columnas, valores, seleccionable=True,
        descarga_texto="Descargar", descarga_todo=True, etiqueta="prueba")

    arbol = tabla["arbol"]
    primero = arbol.get_children()[0]
    assert list(arbol["columns"]) == ["a", "b"]
    assert arbol.item(primero, "values") == ("uno", "1")
    assert tabla["boton_seleccion"].instate(["disabled"])

    sel = tabla["seleccion"]
    sel.alternar(primero)
    assert not tabla["boton_seleccion"].instate(["disabled"])

    tabla["boton_seleccion"].invoke()

    assert exportadas == [[filas[0]]]
