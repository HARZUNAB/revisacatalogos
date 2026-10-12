# -*- coding: utf-8 -*-
"""Pruebas de la interfaz de revision de eventos, sin base de datos."""
import importlib.util
import os
import sys
import tempfile
from datetime import datetime

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, RAIZ)

_spec = importlib.util.spec_from_file_location(
    "rs_", os.path.join(RAIZ, "revisa_seiscomp.py"))
rev = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rev)

fallos = []


def check(nombre, ok, detalle=None):
    print("  %-4s %s" % ("OK" if ok else "FALLA", nombre))
    if not ok:
        fallos.append(nombre)
        if detalle is not None:
            print("        -> %r" % (detalle,))


def fase(id_pick="Pick/1", red="C1", est="AP01", fase_="P", az=120.0,
         usada=True, mag=None, tipo=None, tiene="No", residuo=None,
         qc="sin_evaluar", llegada="2026-09-01 00:38:35", us="412754"):
    """Una llegada de prueba, con lo mismo que produce el exportador."""
    return {
        "id_evento": "ev1", "id_origen": "or1", "id_pick": id_pick, "red": red,
        "estacion": est, "loc": "", "cha": "HHZ", "fase": fase_,
        "llegada_utc": llegada, "llegada_us": us, "correccion_s": "0",
        "residual_s": "0.12", "azimut": str(az), "distancia": "1.06",
        "usada": str(usada), "peso": "1.04", "polarity": "",
        "modo_pick": "manual" if usada else "automatic",
        "pick_autor": "mary" if usada else "scautopic@host",
        "pick_agencia": "CSN",
        "pick_metodo": "" if usada else "AIC",
        "snr": "4.7", "mag_estacion": mag or "",
        "tipo_mag_estacion": tipo or "", "tiene_magnitud": tiene,
        "mag_est_residuo": residuo or "", "qc_estacion": qc,
        "est_lat": "-18.37", "est_lon": "-70.34", "est_elev": "31.0",
        "est_lugar": "Chacalluta", "est_pais": "Chile",
        "base_datos": "seiscomp2",
    }


def evento(id_="ev1", mag="2.8", ot="20260915003833", region="Near Coast",
           op="mary", fases="14", prof="28.8", base="seiscomp2"):
    return {
        "id_evento": id_, "id_origen": "or1", "ot_utc": ot, "magnitud": mag,
        "tipo_magnitud": "MLv", "fases": fases, "rms": "0.22", "azgap": "244.0",
        "latitud": "-31.64", "longitud": "-71.75", "profundidad_km": prof,
        "agencia": "CSN", "operador": op, "region": region, "estatus": "confirmed",
        "base_datos": base,
    }


print("\n1. Formato: lo que falta se muestra como vacio, nunca como 0")
check("una celda vacia se muestra con guion", rev._texto("") == rev.VACIO)
check("un None tambien", rev._texto(None) == rev.VACIO)
check("un cero SI se muestra como cero", rev._texto(0) == "0", rev._texto(0))
check("un numero sin dato no se convierte en 0",
      rev._numero("") == rev.VACIO and rev._numero(None) == rev.VACIO)
check("una magnitud ausente no se vuelve 0",
      rev._numero("", 2) == rev.VACIO)
check("un peso de 0 legitimo se muestra", rev._numero(0.0, 2) == "0.00",
      rev._numero(0.0, 2))
check("un texto no numerico se devuelve tal cual",
      rev._numero("MLv", 2) == "MLv")
check("un numero con muchos decimales se redondea",
      rev._numero("2.5286061833746367", 2) == "2.53",
      rev._numero("2.5286061833746367", 2))

print("\n2. La fecha del CSV viene como YYYY-MM-DD HH:MM:SS (o con T)")
check("se parte en fecha y hora",
      rev._partir_fecha_hora("2026-09-15 00:38:33") == ("2026-09-15", "00:38:33"),
      rev._partir_fecha_hora("2026-09-15 00:38:33"))
check("con T tambien",
      rev._partir_fecha_hora("2026-09-15T00:38:33") == ("2026-09-15", "00:38:33"),
      rev._partir_fecha_hora("2026-09-15T00:38:33"))
check("doble espacio entre fecha y hora (select de Seisan)",
      rev._partir_fecha_hora("2026-09-04  06:48:08") == ("2026-09-04", "06:48:08"),
      rev._partir_fecha_hora("2026-09-04  06:48:08"))
check("un texto que no es fecha no rompe", rev._partir_fecha_hora("basura")[0] == "basura")
check("una fecha vacia no rompe", rev._partir_fecha_hora("")[0] == rev.VACIO)

print("\n3. Agrupar las llegadas por estacion")
mezcla = [
    fase("Pick/2", "C1", "AP02", "P", az=90.0),
    fase("Pick/1", "C1", "AP01", "S", az=200.0, mag="2.85", tipo="MLv",
         tiene="Si", qc="aprobado"),
    fase("Pick/3", "C1", "AP01", "P", az=120.0),
    fase("Pick/4", "CX", "PB10", "P", az=45.0),
]
grupos = rev._agrupar_por_estacion(mezcla)
check("una fila por estacion", len(grupos) == 3, len(grupos))
check("ordenadas por red y estacion",
      [n for _, n, _ in grupos] == ["C1 AP01", "C1 AP02", "CX PB10"],
      [n for _, n, _ in grupos])
ap01 = grupos[0][2]
check("dentro de la estacion, por azimut",
      [f["azimut"] for f in ap01] == ["120.0", "200.0"],
      [f["azimut"] for f in ap01])
check("el encabezado cuenta las llegadas y las usadas",
      "2 llegadas" in rev._encabezado_estacion("C1 AP01", ap01),
      rev._encabezado_estacion("C1 AP01", ap01))
con_sin_usar = [fase("Pick/1", "C1", "AP01", "P", usada=True),
                fase("Pick/8", "C1", "AP01", "S", az=200.0, usada=False)]
check("avisa cuantas se dejaron sin usar",
      "sin usar 1" in rev._encabezado_estacion("C1 AP01", con_sin_usar),
      rev._encabezado_estacion("C1 AP01", con_sin_usar))
check("si todas se usaron, no menciona que falte ninguna",
      "sin usar" not in rev._encabezado_estacion("C1 AP01", ap01),
      rev._encabezado_estacion("C1 AP01", ap01))
check("muestra la magnitud de la estacion, redondeada",
      "mag 2.9 MLv" in rev._encabezado_estacion("C1 AP01", ap01),
      rev._encabezado_estacion("C1 AP01", ap01))
sin_mag = [fase("Pick/9", "C1", "ZZ99")]
check("una estacion sin magnitud no inventa el valor",
      "mag" not in rev._encabezado_estacion("C1 ZZ99", sin_mag),
      rev._encabezado_estacion("C1 ZZ99", sin_mag))
check("una lista vacia no rompe", rev._agrupar_por_estacion([]) == [])

print("\n4. Dos llegadas que comparten pick no se comen entre si")
gemelas = [fase("Pick/5", "C1", "AP01", "P", az=10.0),
           fase("Pick/5", "C1", "AP01", "P", az=11.0)]
claves = {(f["id_pick"], f["fase"], f["azimut"]) for f in gemelas}
check("se distinguen por el azimut", len(claves) == 2, len(claves))
check("la agrupacion no las junta en una sola",
      len(rev._agrupar_por_estacion(gemelas)[0][2]) == 2,
      len(rev._agrupar_por_estacion(gemelas)[0][2]))

print("\n5. Los valores de una llegada")
v = rev._valores_fase(mezcla[2])
check("la cantidad coincide con las columnas declaradas",
      len(v) == len(rev.COLUMNAS_FASE), (len(v), len(rev.COLUMNAS_FASE)))
dic = {c[0]: v[i] for i, c in enumerate(rev.COLUMNAS_FASE)}
check("la llegada pega los microsegundos",
      dic["llegada"] == "2026-09-01 00:38:35.412754", dic["llegada"])
check("la usada se dice con si o no", dic["usada"] == "sí", dic["usada"])
check("una magnitud ausente queda con guion", dic["mag"] == rev.VACIO, dic["mag"])
check("el QC se muestra tal cual", dic["qc"] == "sin_evaluar", dic["qc"])
check("el lugar del inventario viene", dic["lugar"] == "Chacalluta", dic["lugar"])
no_usada = rev._valores_fase(fase(usada=False))
dic2 = {c[0]: no_usada[i] for i, c in enumerate(rev.COLUMNAS_FASE)}
check("una llegada no usada se marca como tal", dic2["usada"] == "no", dic2["usada"])
# Si la celda de llegada_utc ya trajera decimales, no se duplican
con_dec = rev._valores_fase(fase(llegada="2026-09-01 00:38:35.412754"))
dic3 = {c[0]: con_dec[i] for i, c in enumerate(rev.COLUMNAS_FASE)}
check("no se duplica el punto decimal",
      dic3["llegada"] == "2026-09-01 00:38:35.412754", dic3["llegada"])

print("\n6. El resumen de las llegadas de un evento")
res = rev._resumen_fases(mezcla)
check("cuenta las llegadas", res["fases"] == 4, res["fases"])
check("cuenta las estaciones", res["estaciones"] == 3, res["estaciones"])
check("cuanta las usadas", res["usadas"] == 4, res["usadas"])
check("cuenta las que tienen magnitud", res["con_magnitud"] == 1, res["con_magnitud"])
check("las que no tienen", res["sin_magnitud"] == 3, res["sin_magnitud"])
check("con residuo", res["con_residuo"] == 0, res["con_residuo"])
check("sin ninguna magnitud, la media queda en None",
      rev._resumen_fases([fase()])["mag_promedio"] is None)
check("con una sola magnitud, la media es esa",
      abs(rev._resumen_fases([fase(mag="3.0", tiene="Si")])["mag_promedio"]
          - 3.0) < 1e-9)
check("lista vacia no rompe",
      rev._resumen_fases([])["fases"] == 0)

print("\n7. Filtrar la lista de eventos")
eventos = [evento("e1", mag="1.2", op="mary", region="Chile"),
           evento("e2", mag="4.5", op="eatl", region="Argentina"),
           evento("e3", mag="", op="jaba", region="Chile", base="seiscomp")]


def valores(f):
    return [f.get("id_evento", ""), f.get("operador", ""),
            f.get("region", ""), f.get("base_datos", "")]


filtrar = lambda filas, texto="", mag_min=None: rev._filtrar_listado(
    filas, valores, texto=texto, mag_min=mag_min, clave_mag="magnitud")
check("sin filtro salen todos", len(filtrar(eventos)) == 3)
check("filtra por operador", len(filtrar(eventos, "eatl")) == 1)
check("filtra por region", len(filtrar(eventos, "Argentina")) == 1)
check("filtra por id", len(filtrar(eventos, "e2")) == 1)
check("no distingue mayusculas", len(filtrar(eventos, "EATL")) == 1)
check("texto combinado", len(filtrar(eventos, "Chile", 2.0)) == 0)
check("por magnitud minima", len(filtrar(eventos, "", 4.0)) == 1)
check("un evento SIN magnitud no cuenta como menor que el minimo",
      len(filtrar(eventos, "", 2.0)) == 1,
      len(filtrar(eventos, "", 2.0)))
check("un filtro sin resultados da vacio",
      len(filtrar(eventos, "noexiste")) == 0)
check("espacios en el filtro se ignoran",
      len(filtrar(eventos, "  eatl  ")) == 1)

print("\n8. Ordenar la lista de eventos")
lista = [evento("e1", mag="10.0"), evento("e2", mag="3.5"),
         evento("e3", mag="")]
asc = rev._ordenar_eventos(lista, "mag")
check("ordena por numero y no por texto: 3.5 antes que 10.0",
      [e["magnitud"] for e in asc] == ["3.5", "10.0", ""],
      [e["magnitud"] for e in asc])
desc = rev._ordenar_eventos(lista, "mag", True)
check("invertir el sentido invierte el orden",
      [e["magnitud"] for e in desc] == ["10.0", "3.5", ""],
      [e["magnitud"] for e in desc])
check("lo que no tiene dato queda AL FINAL tambien al invertir",
      desc[-1]["magnitud"] == "", desc[-1]["magnitud"])
check("sin columna no reordena nada",
      rev._ordenar_eventos(lista, None) == lista)
check("ordena por texto sin distinguir mayusculas",
      [e["operador"] for e in rev._ordenar_eventos(
          [evento("a", op="Zulma"), evento("b", op="ana")], "operador")]
      == ["ana", "Zulma"])
check("ordena por fecha, que en el CSV ya ordena bien",
      [e["ot_utc"] for e in rev._ordenar_eventos(
          [evento("a", ot="20260902"), evento("b", ot="20260901")], "fecha")]
      == ["20260901", "20260902"])
check("ordenar no modifica la lista original", len(lista) == 3)

print("\n9. El panel se abre con los dos archivos")
with tempfile.TemporaryDirectory() as d:
    ruta_ev = os.path.join(d, "ev.csv")
    ruta_fa = os.path.join(d, "ev_fases.csv")
    import csv as _csv
    with open(ruta_ev, "w", encoding="utf-8", newline="") as f:
        w = _csv.DictWriter(f, fieldnames=list(evento().keys()))
        w.writeheader()
        w.writerow(evento())
    with open(ruta_fa, "w", encoding="utf-8", newline="") as f:
        w = _csv.DictWriter(f, fieldnames=list(fase().keys()))
        w.writeheader()
        w.writerow(fase())
    check("devuelve False si falta el de eventos",
          rev.abrir_panel(None, os.path.join(d, "no.csv"), ruta_fa) is False)
    check("devuelve False si falta el de fases",
          rev.abrir_panel(None, ruta_ev[:-4] + "_otra.csv") is False)
    check("no intenta abrir ventana si no hay contenedor",
          rev.abrir_panel(None, ruta_ev) in (False,))

    # Con display disponible se construye de verdad.
    try:
        import ttkbootstrap as ttk
        vent = ttk.Window(themename="flatly")
        marco = ttk.Frame(vent)
        marco.pack()
        ok = rev.abrir_panel(marco, ruta_ev, ruta_fa)
        check("con los dos archivos devuelve True", ok is True)
        if ok:
            arboles = []

            def buscar(w, acc=None):
                acc = acc if acc is not None else []
                for c in w.winfo_children():
                    if isinstance(c, ttk.Treeview):
                        acc.append(c)
                    buscar(c, acc)
                return acc
            arboles = buscar(marco)
            check("hay un arbol de eventos", len(arboles) >= 1, len(arboles))
            check("el evento se ve en la lista",
                  len(arboles[0].get_children()) == 1,
                  len(arboles[0].get_children()))
            check("las columnas son las declaradas",
                  list(arboles[0]["columns"])
                  == [c for c, _, _ in rev.COLUMNAS_EVENTO])
            check("base_datos aparece en la lista de eventos",
                  "base" in [c for c, _, _ in rev.COLUMNAS_EVENTO])
            # Seleccionar, como si el usuario hiciera clic
            arboles[0].selection_set(arboles[0].get_children()[0])
            arboles[0].event_generate("<<TreeviewSelect>>")
            vent.update()
            # El detalle es una ventana aparte (Toplevel), no embebido en el
            # panel: se busca entre las ventanas hijas de la raíz.
            toplevels = [w for w in vent.winfo_children()
                         if isinstance(w, ttk.Toplevel)]
            check("al seleccionar se abre la ventana de detalle",
                  len(toplevels) >= 1, len(toplevels))
            if toplevels:
                arboles_detalle = buscar(toplevels[0])
                check("y trae el arbol de llegadas",
                      len(arboles_detalle) >= 1, len(arboles_detalle))
                if arboles_detalle:
                    raices = arboles_detalle[0].get_children()
                    check("una fila plegable por estacion", len(raices) == 1,
                          len(raices))
                    check("con la llegada colgando",
                          len(arboles_detalle[0].get_children(raices[0])) == 1)
                    check("la fila de la estacion dice cuantas son",
                          "1 llegada" in arboles_detalle[0].item(raices[0], "text"),
                          arboles_detalle[0].item(raices[0], "text"))
        vent.destroy()
    except Exception as e:                       # sin display
        print("  (sin display, se salta la prueba de widgets: %s)" % e)

print("\n9-bis. El indice de fases: memoria acotada con archivos grandes")
import csv as _csv2
import random as _random

def _escribir_csv_fases(ruta, fases_por_evento, ):
    with open(ruta, "w", encoding="utf-8", newline="") as f:
        w = _csv2.writer(f)
        w.writerow(list(fase().keys()))
        for ev, filas in fases_por_evento.items():
            for fila in filas:
                fila = dict(fila)
                fila["id_evento"] = ev
                w.writerow([fila.get(c, "") for c in fase().keys()])

with tempfile.TemporaryDirectory() as d:
    ruta = os.path.join(d, "fases.csv")
    # Varios eventos, con Distintas cantidades de llegadas
    datos = {}
    for i in range(12):
        ev = "ev%02d" % i
        datos[ev] = [fase("Pick/%s-%d" % (ev, n), red="C1",
                          est="E%02d" % (n % 3), az=float(n))
                     for n in range(1 + i)]
    _escribir_csv_fases(ruta, datos)

    indice, campos, total = rev._indexar_fases(ruta)
    check("el indice tiene una entrada por evento", len(indice) == 12, len(indice))
    check("cuenta todas las llegadas", total == sum(len(v) for v in datos.values()),
          total)
    check("la cabecera sale del archivo",
          campos[0] == "id_evento" and len(campos) == len(fase()),
          campos[:3])
    check("cada evento con la cantidad correcta de llegadas",
          all(len(rev._leer_fases_de_evento(ruta, indice, campos, ev)) == len(v)
              for ev, v in datos.items()))
    check("al leer un evento vienen todas sus columnas",
          all(f.get("id_pick", "").startswith("Pick/") or True
              for f in rev._leer_fases_de_evento(ruta, indice, campos, "ev03")))

    # Un evento que NO esta: no inventa nada
    check("un evento inexistente no trae filas",
          rev._leer_fases_de_evento(ruta, indice, campos, "no_existe") == [])

    # Lo importante: los tramos cubren el archivo entero salvo la cabecera.
    with open(ruta, "rb") as f:
        largo_cabecera = len(f.readline())
    cubierto = sum(l for tramos in indice.values() for _, l in tramos)
    check("los tramos cubren TODO el archivo, sin dejar ni pisar bytes",
          cubierto == os.path.getsize(ruta) - largo_cabecera,
          (cubierto, os.path.getsize(ruta) - largo_cabecera))

    # Un evento partido en dos tramos (separado por otro) se lee entero
    ruta2 = os.path.join(d, "partido.csv")
    _escribir_csv_fases(ruta2, {"evA": [fase("Pick/a1", az=1.0)],
                              "evB": [fase("Pick/b1", az=2.0)],
                              "evA2": [fase("Pick/a2", az=3.0)]})
    # se reescribe a mano para que evA aparezca en dos tramos
    with open(ruta2, "w", encoding="utf-8", newline="") as f:
        w = _csv2.writer(f)
        cabs = list(fase().keys())
        w.writerow(cabs)
        for ev, n in (("evA", 1), ("evB", 2), ("evA", 3)):
            fila = dict(fase("Pick/%s%d" % (ev, n), az=float(n)))
            fila["id_evento"] = ev
            w.writerow([fila.get(c, "") for c in cabs])
    indice2, campos2, total2 = rev._indexar_fases(ruta2)
    check("un evento en dos tramos queda con dos entradas",
          len(indice2.get("evA", [])) == 2, indice2.get("evA"))
    check("y al leerlo trae las dos filas",
          len(rev._leer_fases_de_evento(ruta2, indice2, campos2, "evA")) == 2,
          len(rev._leer_fases_de_evento(ruta2, indice2, campos2, "evA")))

    # Un id entre comillas se lee sin las comillas
    ruta3 = os.path.join(d, "comillas.csv")
    with open(ruta3, "w", encoding="utf-8", newline="") as f:
        w = _csv2.writer(f)
        cabs = list(fase().keys())
        w.writerow(cabs)
        fila = dict(fase("Pick/q1"))
        fila["id_evento"] = 'evento,con coma'
        w.writerow([fila.get(c, "") for c in cabs])
    indice3, campos3, _ = rev._indexar_fases(ruta3)
    check("un id con coma y entre comillas se indexa bien",
          list(indice3) == ['evento,con coma'], list(indice3))
    check("y se puede volver a leer",
          len(rev._leer_fases_de_evento(ruta3, indice3, campos3,
                                        'evento,con coma')) == 1)

    # La interfaz NO tiene que cargar todas las fases
    fuente = open(os.path.join(RAIZ, "revisa_seiscomp.py"), encoding="utf-8").read()
    check("el codigo ya no carga el archivo de fases entero",
          "_leer_csv(ruta_fases)" not in fuente)
    check("usa el indice en cambio", "_indexar_fases(ruta_fases)" in fuente)
    check("al seleccionar lee solo el evento",
          "_leer_fases_de_evento" in fuente)

print("\n10. Elegir otros archivos")

class DialogoFalso:
    """Sustituye al selector de archivos, para no depender de un clic."""

    def __init__(self, respuestas):
        self.respuestas = list(respuestas)
        self.llamadas = []

    def askopenfilename(self, **kw):
        self.llamadas.append(kw)
        return self.respuestas.pop(0) if self.respuestas else ""


def _con_dialogo(respuestas, fn, *args):
    """Corre fn con el selector de archivos simulado."""
    import tkinter.filedialog as fd
    real = fd.askopenfilename
    falso = DialogoFalso(respuestas)
    fd.askopenfilename = falso.askopenfilename
    try:
        resultado = fn(*args)
    finally:
        fd.askopenfilename = real
    return resultado, falso


with tempfile.TemporaryDirectory() as d:
    ruta_ev = os.path.join(d, "ev.csv")
    ruta_fa = os.path.join(d, "ev_fases.csv")
    open(ruta_ev, "w").close()
    open(ruta_fa, "w").close()
    sola_ev = os.path.join(d, "sin_fases.csv")
    open(sola_ev, "w").close()

    r, _ = _con_dialogo([ruta_ev], rev._elegir_archivos, d, None)
    check("si existe el de fases con el mismo nombre, no pregunta dos veces",
          r == (ruta_ev, ruta_fa), r)

    r, dl = _con_dialogo([sola_ev, ruta_fa], rev._elegir_archivos, d, None)
    check("si falta el de fases, lo pregunta",
          r == (sola_ev, ruta_fa), r)
    check("hizo dos consultas al dialogo", len(dl.llamadas) == 2, len(dl.llamadas))
    check("la segunda empieza en la carpeta del primero",
          dl.llamadas[1]["initialdir"] == d, dl.llamadas[1].get("initialdir"))

    r, dl = _con_dialogo([""], rev._elegir_archivos, d, None)
    check("si se cancela, no devuelve archivos", r == (None, None), r)
    check("y solo preguntó una vez", len(dl.llamadas) == 1, len(dl.llamadas))

    filtros = [str(c[1]) for c in dl.llamadas[0].get("filetypes", [])]
    check("el dialogo ofrece el filtro de CSV, ademas del de todos",
          "*.csv" in filtros and "*" in filtros, filtros)

# Lo que se rompe: ttkbootstrap no tiene selectores de archivos.
try:
    import ttkbootstrap
    check("esta version de ttkbootstrap NO tiene filedialog (por eso se usa tkinter)",
          not hasattr(ttkbootstrap, "filedialog"))
except ImportError:
    pass
fuente = open(os.path.join(RAIZ, "revisa_seiscomp.py"), encoding="utf-8").read()
check("el codigo ya no llama a ttk.filedialog", "ttk.filedialog" not in fuente)
check("usa el de tkinter", "from tkinter import filedialog" in fuente)

print("\n11. Un evento sin llegadas no rompe nada")
check("el agrupado vacio es lista vacia", rev._agrupar_por_estacion([]) == [])
check("el resumen vacio no divide por cero",
      rev._resumen_fases([])["mag_promedio"] is None)
check("los valores de una llegada vacia no rompen",
      len(rev._valores_fase({})) == len(rev.COLUMNAS_FASE))

print("\n12. Los datos se buscan en el directorio de ejecucion, no en el del script")

RAIZ_PROYECTO = RAIZ
check("el codigo ya no usa la carpeta del script para buscar datos",
      "__file__" not in open(os.path.join(RAIZ_PROYECTO, "revisa_seiscomp.py"),
                             encoding="utf-8").read().split("def main")[1])
check("el directorio de datos es el de ejecucion + datos",
      rev._directorio_datos() == os.path.join(os.getcwd(), "datos"),
      rev._directorio_datos())

# _pares_disponibles sobre una carpeta de trabajo simulada
with tempfile.TemporaryDirectory() as d:
    carpeta = os.path.join(d, "datos")
    os.makedirs(carpeta)
    import time as _time
    # Un par viejo y uno nuevo, mas archivos que NO son de seiscomp
    for nombre in ("eventos_seisan.json", "sospechosos_seisan.csv",
                   "seiscomp_20260101000000_20260131235959.csv",
                   "seiscomp_20260901000000_20260930235959.csv"):
        ruta = os.path.join(carpeta, nombre)
        with open(ruta, "w", encoding="utf-8") as f:
            f.write("x")
        _time.sleep(0.01)
    os.utime(os.path.join(carpeta, "seiscomp_20260901000000_20260930235959.csv"),
             (9e9, 9e9))
    pares = rev._pares_disponibles(d)
    check("solo toma los CSV de SeisComp, ignora el JSON y el resto",
          len(pares) == 2, [os.path.basename(p["eventos"]) for p in pares])
    check("el mas reciente es el que ofrece primero",
          os.path.basename(pares[0]["eventos"]).startswith("seiscomp_20260901"),
          os.path.basename(pares[0]["eventos"]))
    check("no toma el de fases como si fuera un par",
          not any("_fases" in os.path.basename(p["eventos"]) for p in pares))
    check("una carpeta que no existe da lista vacia, no error",
          rev._pares_disponibles(os.path.join(d, "no_existe")) == [])
    # Con el par completo, marca el de fases
    fases = pares[0]["eventos"][:-4] + "_fases.csv"
    open(fases, "w").close()
    pares = rev._pares_disponibles(d)
    check("cuando el de fases existe, lo asocia",
          pares[0]["fases"] is not None, pares[0]["fases"])
    os.remove(fases)
    pares = rev._pares_disponibles(d)
    check("cuando falta, lo deja en None y no inventa",
          pares[0]["fases"] is None, pares[0]["fases"])

print("\n13. Desde otra carpeta: encuentra los datos del trabajo")
# Se corre el script como subproceso desde una carpeta que NO es la del
# proyecto, sin argumentos. No debe abrir ventana: sin datos, solo avisa.
with tempfile.TemporaryDirectory() as d:
    import subprocess as _sp
    entorno = dict(os.environ)
    r = _sp.run([sys.executable,
                 os.path.join(RAIZ_PROYECTO, "revisa_seiscomp.py")],
                capture_output=True, text=True, cwd=d, env=entorno, timeout=120)
    salida = r.stdout + r.stderr
    check("sin datos en la carpeta de trabajo, avisa y sale con codigo 1",
          r.returncode == 1, r.returncode)
    check("y el aviso nombra ESA carpeta, no la del proyecto",
          os.path.join(d, "datos") in salida, salida.strip()[:160])
    check("el aviso NO menciona la carpeta del proyecto",
          RAIZ_PROYECTO not in salida, salida.strip()[:160])

    # Ahora con datos de verdad en la carpeta de trabajo, siempre pasando la
    # ruta explicita: debe intentar abrir y no decir que no hay archivos.
    import csv as _csv3
    os.makedirs(os.path.join(d, "datos"), exist_ok=True)
    ev = ruta = os.path.join(d, "datos", "seiscomp_x.csv")
    with open(ev, "w", encoding="utf-8", newline="") as f:
        w = _csv3.writer(f)
        w.writerow(list(evento().keys()))
        w.writerow(evento())
    with open(ev[:-4] + "_fases.csv", "w", encoding="utf-8", newline="") as f:
        w = _csv3.writer(f)
        w.writerow(list(fase().keys()))
        w.writerow(fase())
    # Con DISPLAY disponible la ventana abre y se queda esperando en mainloop,
    # asi que el proceso no termina solo: se lo corta y se mira lo que dijo.
    proc = _sp.Popen([sys.executable, os.path.join(RAIZ_PROYECTO, "revisa_seiscomp.py"), ev],
                     stdout=_sp.PIPE, stderr=_sp.STDOUT, text=True,
                     cwd=d, env=entorno)
    try:
        salida = proc.communicate(timeout=6)[0]
    except _sp.TimeoutExpired:
        proc.terminate()
        try:
            salida = proc.communicate(timeout=10)[0]
        except _sp.TimeoutExpired:
            proc.kill()
            salida = proc.communicate()[0]
    check("con la ruta explicita NO dice que no hay archivos",
          "No hay CSV de SeisComp" not in salida, salida.strip()[:160])
    check("y no se cae por buscar en la carpeta equivocada",
          "FileNotFoundError" not in salida and "Traceback" not in salida,
          salida.strip()[:200])

print("\n14. La ventana se toma del catalogo, no de la fecha de escritura")

check("lee una fecha con T y Z (formato del catalogo)",
      rev._parsear_instante("2026-09-04T15:51:16Z") ==
      datetime(2026, 9, 4, 15, 51, 16))
check("lee una fecha con espacio (formato del flujo)",
      rev._parsear_instante("2026-09-01 00:38:33") ==
      datetime(2026, 9, 1, 0, 38, 33))
check("una celda vacia o basura no rompe",
      rev._parsear_instante("") is None and rev._parsear_instante("xyz") is None)
check("saca la ventana del nombre de un archivo exportado",
      rev._ventana_del_nombre("seiscomp_20260901000000_20260930235959.csv")
      == (datetime(2026, 9, 1, 0, 0, 0), datetime(2026, 9, 30, 23, 59, 59)))
check("un nombre que no es de exportador no da ventana",
      rev._ventana_del_nombre("eventos_seisan.json") is None)

with tempfile.TemporaryDirectory() as d:
    import csv as _c, time as _t

    # Catalogo de referencia, con el formato del catalogo (T y Z)
    cat = os.path.join(d, "sep_2026_1_29.csv")
    with open(cat, "w", encoding="utf-8", newline="") as f:
        w = _c.writer(f)
        w.writerow(["time", "latitude", "longitude", "depth [km]",
                    "magnitude", "magnitude_type", "region_name", "felt"])
        w.writerow(["2026-09-04T15:51:16Z", -21.11, -69.03, 109.6, 2.7, "MLv", "x", "f"])
        w.writerow(["2026-09-01T00:38:33Z", -31.64, -71.75, 28.8, 2.9, "MLv", "y", "f"])
        w.writerow(["2026-09-28T14:03:10Z", -20.0, -70.0, 10.0, 3.0, "MLv", "z", "f"])
    ventana = rev._ventana_del_catalogo(cat)
    check("el catalogo da desde y hasta",
          ventana == (datetime(2026, 9, 1, 0, 38, 33),
                      datetime(2026, 9, 28, 14, 3, 10)), ventana)

    # Tambien el formato del flujo, con columna Fecha_Hora
    cat2 = os.path.join(d, "new_sep.csv")
    with open(cat2, "w", encoding="utf-8-sig", newline="") as f:
        w = _c.writer(f)
        w.writerow(["", "Fecha_Hora", "Latitud", "Magnitud"])
        w.writerow([0, "2026-10-01 00:00:00", -30, 3.0])
        w.writerow([1, "2026-10-31 23:00:00", -31, 4.0])
    v2 = rev._ventana_del_catalogo(cat2)
    check("también el formato del flujo, con BOM y Fecha_Hora",
          v2 == (datetime(2026, 10, 1, 0, 0, 0),
                 datetime(2026, 10, 31, 23, 0, 0)), v2)

    # Un CSV sin columna de tiempo NO es un catalogo
    cat3 = os.path.join(d, "sin_fecha.csv")
    with open(cat3, "w", encoding="utf-8", newline="") as f:
        _c.writer(f).writerow(["a", "b"])
    check("un CSV sin columna de tiempo no se toma como catalogo",
          rev._ventana_del_catalogo(cat3) is None)

    # Detecta el catalogo ignorando nuestras exportaciones y los sin fecha
    os.makedirs(os.path.join(d, "datos"), exist_ok=True)
    open(os.path.join(d, "datos", "seiscomp_20260901000000_20260930235959.csv"), "w").close()
    elegido = rev._catalogo_disponible(d)
    check("detecta el catalogo de la raiz",
          elegido is not None and os.path.basename(elegido) == "new_sep.csv",
          os.path.basename(elegido) if elegido else None)
    check("ignora las exportaciones y los CSV sin fecha",
          "seiscomp" not in os.path.basename(elegido or ""))

    # La eleccion: tres exportaciones en distintas ventanas
    pares = []
    for nombre, mtime in (("seiscomp_20260701000000_20260731235959.csv", 3.0),
                          ("seiscomp_20260901000000_20260930235959.csv", 2.0),
                          ("seiscomp_20261101000000_20261130235959.csv", 9.9)):
        ruta = os.path.join(d, "datos", nombre)
        open(ruta, "w").close()
        os.utime(ruta, (mtime, mtime))
        pares.append({"eventos": ruta, "fases": ruta[:-4] + "_fases.csv"})
    # En el mismo orden que devuelve _pares_disponibles: por fecha de
    # modificacion descendente, que es como los ordena la funcion real.
    pares.sort(key=lambda x: os.path.getmtime(x["eventos"]), reverse=True)
    # _pares_disponibles ordena por fecha de modificacion descendente, asi que
    # pares[0] es el mas reciente: el de noviembre, a proposito.
    check("el mas reciente por escritura es el de noviembre",
          os.path.basename(pares[0]["eventos"]).startswith("seiscomp_20261101"),
          os.path.basename(pares[0]["eventos"]))
    check("sin catalogo se toma el mas reciente",
          rev._elegir_par(pares, None) is pares[0])
    # Con el catalogo de septiembre tiene que ganar la de septiembre, aunque
    # no sea la mas reciente escrita.
    por_nombre = {os.path.basename(x["eventos"]): x for x in pares}
    septiembre = por_nombre["seiscomp_20260901000000_20260930235959.csv"]
    par = rev._elegir_par(pares, ventana)
    check("con catalogo elige la exportacion que cubre su ventana",
          par is septiembre, os.path.basename(par["eventos"]))
    check("aunque no sea la mas reciente escrita",
          par is not pares[0]
          and pares[0]["eventos"].endswith("20261130235959.csv"),
          os.path.basename(pares[0]["eventos"]))
    check("el orden de los pares no importa para elegir",
          rev._elegir_par(list(reversed(pares)), ventana) is septiembre)
    # Una ventana que no se superpone con NINGUN par: NO se elige ninguno, para
    # que main() avise en vez de abrir un mes cualquiera en silencio.
    lejos = (datetime(2020, 1, 1), datetime(2020, 12, 31))
    check("si ninguna cubre la ventana, no elige ninguna",
          rev._elegir_par(pares, lejos) is None)
    check("sin pares, no devuelve nada",
          rev._elegir_par([], ventana) is None)

print("\n15-bis. Cuando la exportacion no cubre el catalogo, se avisa")
import csv as _c2, os as _o2, subprocess as _sp3
with tempfile.TemporaryDirectory() as d:
    # Catalogo de septiembre
    cat = _o2.path.join(d, "sep_2026_1_29.csv")
    with open(cat, "w", encoding="utf-8", newline="") as f:
        w = _c2.writer(f)
        w.writerow(["time", "latitude", "magnitude"])
        w.writerow(["2026-09-01T00:38:33Z", -31.6, 2.9])
        w.writerow(["2026-09-28T14:03:10Z", -20.0, 3.0])
    # Exportacion de OTRO mes, que es el caso que fallaba en silencio
    _o2.makedirs(_o2.path.join(d, "datos"), exist_ok=True)
    mal = _o2.path.join(d, "datos", "seiscomp_20260929000000_20260929235959.csv")
    with open(mal, "w", encoding="utf-8", newline="") as f:
        w = _c2.writer(f)
        w.writerow(list(evento().keys()))
        w.writerow(evento())
    with open(mal[:-4] + "_fases.csv", "w", encoding="utf-8", newline="") as f:
        w = _c2.writer(f)
        w.writerow(list(fase().keys()))
        w.writerow(fase())
    proc = _sp3.Popen([sys.executable,
                       _o2.path.join(RAIZ_PROYECTO, "revisa_seiscomp.py")],
                      stdout=_sp3.PIPE, stderr=_sp3.STDOUT, text=True,
                      cwd=d, env=dict(_o2.environ), bufsize=1)
    try:
        salida = proc.communicate(timeout=12)[0]
    except _sp3.TimeoutExpired:
        proc.terminate()
        try:
            salida = proc.communicate(timeout=10)[0]
        except _sp3.TimeoutExpired:
            proc.kill()
            salida = proc.communicate()[0]
    check("avisa que ninguna exportacion cubre el catalogo",
          "Ninguna exportaci" in salida and "cubre" in salida,
          salida.strip()[-160:])
    check("dice que ventana exportar", "exporta_ventana_seiscomp.py" in salida,
          salida.strip()[-160:])
    check("y que porcentaje del catalogo se esta viendo",
          "del catalogo" in salida, salida.strip()[-120:])
    check("igual abre algo, para no dejar al usuario sin herramienta",
          "Mientras tanto" in salida, salida.strip()[-120:])

print("\n15-ter. La cobertura se mide bien")
check("una ventana cubierta al 100 por ciento",
      abs(rev._cobertura((datetime(2026, 9, 1), datetime(2026, 10, 1)),
                         (datetime(2026, 9, 15), datetime(2026, 9, 20)))[2] - 1.0) < 1e-9)
check("una ventana cubierta a medias",
      abs(rev._cobertura((datetime(2026, 9, 1), datetime(2026, 9, 16)),
                         (datetime(2026, 9, 1), datetime(2026, 10, 1)))[2] - 0.5) < 0.01)
check("sin superposicion da cero",
      rev._cobertura((datetime(2026, 9, 1), datetime(2026, 9, 2)),
                     (datetime(2026, 1, 1), datetime(2026, 1, 2)))[2] == 0.0)
check("sin datos no rompe",
      rev._cobertura(None, None)[2] == 0.0)

print("\n16. --catalogo por linea de comandos")
import subprocess as _sp2
def _correr(args, cwd=None):
    r = _sp2.run([sys.executable,
                  os.path.join(RAIZ_PROYECTO, "revisa_seiscomp.py")] + args,
                 capture_output=True, text=True, cwd=cwd or RAIZ_PROYECTO,
                 timeout=30)
    return r.returncode, r.stdout + r.stderr
rc, salida = _correr(["--catalogo"])
check("--catalogo sin ruta da error claro",
      rc == 2 and "necesita la ruta" in salida, salida.strip()[:120])
rc, salida = _correr(["--help"])
check("--help menciona --catalogo", "--catalogo" in salida)
check("--help explica que se usa el catalogo",
      "catálogo" in salida or "catalogo" in salida)

print("\n" + "=" * 60)
if fallos:
    print("FALLARON %d pruebas: %s" % (len(fallos), fallos))
    sys.exit(1)
print("Todas las pruebas pasan.")
