"""
Prueba end-to-end del boton 'Descargar' del panel de plotear.py.

Usa la raiz Tk real (la de matplotlib/TkAgg, via _asegurar_raiz) porque el
panel se construye como Toplevel de esa raiz, no de una tk.Tk() aparte.

argv[1] = ambito (perfil | visibles | sin_perfil | None)
argv[2] = formato (csv | txt)
"""
import json
import os
import sys
import tempfile
import tkinter as tk
from tkinter import ttk

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, RAIZ)
os.chdir(tempfile.mkdtemp(prefix="panel_"))
matplotlib.use("TkAgg") if False else None

import matplotlib
matplotlib.use("TkAgg")
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
import plotear

CASO = sys.argv[1] if len(sys.argv) > 1 else "perfil"
FORMATO = sys.argv[2] if len(sys.argv) > 2 else "csv"
SOSP = len(sys.argv) > 3 and sys.argv[3] == "sosp"
NADA = len(sys.argv) > 4 and sys.argv[4] == "nada"


def recorrer(w):
    for h in w.winfo_children():
        yield h
        for x in recorrer(h):
            yield x


eventos = []
for i in range(6):
    eventos.append({
        "id": "E%03d" % i,
        "fecha hora": "2026-01-%02d 0%d:00:00" % (1 + i, i),
        "latitud": -31.0 + i * 0.1, "longitud": -64.0 + i * 0.1,
        "prof": 10.0 + i, "magnitud": 3.0 + i * 0.2, "tipo": "ML",
        "perfil": "P001" if i < 4 else "P002",
        "sospechoso": False if NADA else (i % 2 == 0),
        "percibido": "N",
        "analistas": [{"fuente": "Seisan", "analistas": ["Gomez, J."]}],
    })
eventos.append({
    "id": "E900", "fecha hora": "2026-01-09 09:00:00",
    "latitud": -32.0, "longitud": -65.0, "prof": 5.0, "magnitud": 4.0,
    "tipo": "ML", "perfil": None, "sospechoso": False, "percibido": "N",
})
os.makedirs("datos", exist_ok=True)
json.dump(eventos, open("datos/eventos_prueba.json", "w"))

raiz = plotear._asegurar_raiz()
info = {"panel": None, "boton": None, "opciones": None, "marcadas": None,
        "tras": None, "aviso": None, "formato": None, "filtro": None}


def tops():
    return [w for w in raiz.winfo_children() if isinstance(w, tk.Toplevel)]


def pulsando_boton():
    if SOSP:
        for w in recorrer(raiz):
            if isinstance(w, ttk.Button) and w.cget("text") == "Solo sospechosos":
                w.invoke()
                info["filtro"] = "filtro de sospechosos prendido"
                break
        else:
            info["filtro"] = "NO se encontro el boton del filtro"
    hits = [w for w in recorrer(raiz)
            if isinstance(w, ttk.Button) and w.cget("text") == "Descargar"]
    if not hits:
        info["boton"] = "NO se encontro el boton Descargar"
        raiz.quit()
        return
    hits[-1].invoke()
    info["boton"] = "pulsado (%d boton(es) 'Descargar' visibles)" % len(hits)


def pulsando_ambito():
    dlgs = tops()
    if not dlgs:
        info["opciones"] = "el dialogo de ambito NO se abrio"
        raiz.quit()
        return
    dlg = dlgs[-1]
    radios = [w for w in recorrer(dlg) if isinstance(w, ttk.Radiobutton)]
    info["opciones"] = [r.cget("text") for r in radios]
    info["marcadas"] = [r.cget("value") for r in radios
                        if r.instate(["selected"])]
    for r in radios:
        if r.cget("value") == CASO:
            r.invoke()
    raiz.update()
    info["tras"] = [r.cget("value") for r in radios if r.instate(["selected"])]
    for w in recorrer(dlg):
        if isinstance(w, ttk.Button) and w.cget("text") == "Continuar":
            w.invoke()
            break


def pulsando_formato():
    dlgs = tops()
    if not dlgs:
        info["aviso"] = "no se abrio un segundo dialogo"
        raiz.quit()
        return
    dlg = dlgs[-1]
    for w in recorrer(dlg):
        if isinstance(w, ttk.Radiobutton) and w.cget("value") == FORMATO:
            w.invoke()
    for w in recorrer(dlg):
        if isinstance(w, ttk.Button) and w.cget("text") == "Descargar":
            w.invoke()
            break
    info["formato"] = FORMATO


TRAZA = open(os.path.join(tempfile.gettempdir(),
                           "verif_panel_%s_%s.log" % (CASO, FORMATO)), "w")


def anot(msg):
    TRAZA.write(msg + "\n")
    TRAZA.flush()


def t_boton():
    anot("[t=%d] llega el primer callback" % t0)
    pulsando_boton()
    anot("[t=%d] boton: %s" % (t0, info["boton"]))


def t_ambito():
    pulsando_ambito()
    anot("[t=%d] ambito ok, opciones=%s" % (t0, info["opciones"]))


def t_formato():
    pulsando_formato()
    anot("[t=%d] formato ok" % t0)


def t_salir():
    import os as _os
    for w in raiz.winfo_children():
        if isinstance(w, tk.Toplevel):
            anot("toplevel abierto al final: %r" % w.title())
    d = "descargas"
    info["descargas"] = sorted(_os.listdir(d)) if _os.path.isdir(d) else "NINGUNA"
    for k in ("panel", "boton", "filtro", "opciones", "marcadas", "tras",
              "aviso", "descargas"):
        anot("%-10s: %s" % (k, info.get(k)))
    anot("fin de la prueba")
    _os._exit(0)


import time as _time
t0 = int(_time.time())
anot("antes de abrir_panel")
raiz.after(2500, t_boton)
raiz.after(4500, t_ambito)
raiz.after(6500, t_formato)
raiz.after(8500, t_salir)

info["panel"] = plotear.abrir_panel(None, "datos/eventos_prueba.json", "seisan")
anot("[t=%d] abrir_panel devolvio %s" % (t0, info["panel"]))
raiz.mainloop()