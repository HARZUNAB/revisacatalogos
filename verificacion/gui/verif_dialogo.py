"""Verifica el grupo de radios contra un display real."""
import tkinter as tk
from tkinter import ttk

root = tk.Tk(); root.geometry("+50+50")

def escenario(nombre, compartido):
    top = tk.Toplevel(root); top.title(nombre)
    m = ttk.Frame(top, padding=12); m.pack()
    opciones = [("csv", "CSV (.csv)"), ("txt", "TXT (.txt) separado por tab")]
    if compartido:
        var = tk.StringVar(value="csv")
        for c, t in opciones:
            ttk.Radiobutton(m, text=t, value=c, variable=var).pack(anchor="w")
        leer = var.get
    else:
        variables = {}
        for c, t in opciones:
            v = tk.StringVar(value="csv")
            variables[c] = v
            ttk.Radiobutton(m, text=t, value=c, variable=v).pack(anchor="w")
        def leer():
            return "csv" if variables["csv"].get() == "csv" else "txt"
    root.update()
    return top, leer, opciones

for compartido in (False, True):
    nombre = "COMPARTIDO (arreglado)" if compartido else "POR OPCION (viejo)"
    print("--- %s ---" % nombre)
    # el usuario marca TXT
    top, leer, opciones = escenario(nombre, compartido)
    var = None
    if compartido:
        for w in top.winfo_children():
            for sub in w.winfo_children():
                if isinstance(sub, ttk.Radiobutton) and sub.cget("value") == "txt":
                    sub.invoke()
    root.update()
    marcados = [o for o in opciones if True]
    print("  marco TXT  -> valor leido: %s" % leer())
    top.destroy()
    # el usuario vuelve a marcar CSV
    top, leer, opciones = escenario(nombre, compartido)
    if compartido:
        for w in top.winfo_children():
            for sub in w.winfo_children():
                if isinstance(sub, ttk.Radiobutton) and sub.cget("value") == "csv":
                    sub.invoke()
    root.update()
    print("  marco CSV  -> valor leido: %s" % leer())
    top.destroy()

root.destroy()
