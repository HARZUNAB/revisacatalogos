"""Verifica el dialogo REAL de descargas.py: localiza el radio y lo pulsa."""
import tkinter as tk
from tkinter import ttk
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
import descargas

root = tk.Tk()


def recorrer(w):
    for hijo in w.winfo_children():
        yield hijo
        for h in recorrer(hijo):
            yield h


def probar(elegir):
    info = {"radio": "no encontrado", "descargar": False}

    def responder():
        tops = [w for w in root.winfo_children() if isinstance(w, tk.Toplevel)]
        if not tops:
            info["radio"] = "el dialogo NO se abrio"
            return
        dlg = tops[-1]
        for w in recorrer(dlg):
            if isinstance(w, ttk.Radiobutton) and w.cget("value") == elegir:
                w.invoke()
                info["radio"] = "pulsado"
                break
        root.update()
        for w in recorrer(dlg):
            if isinstance(w, ttk.Button) and w.cget("text") == "Descargar":
                w.invoke()
                info["descargar"] = True
                break

    root.after(400, responder)
    return descargas.preguntar_formato(root, "prueba"), info


for elegir in ("txt", "csv"):
    formato, info = probar(elegir)
    print("elijo %-4s -> formato=%-5r  (radio: %s, Descargar pulsado: %s)"
          % (elegir, formato, info["radio"], info["descargar"]))

print("_ultimo_formato:", descargas._ultimo_formato)
root.destroy()