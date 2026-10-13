import tkinter as tk
from tkinter import ttk
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
import descargas

root = tk.Tk()

def recorrer(w):
    for h in w.winfo_children():
        yield h
        for x in recorrer(h):
            yield x

def probar(elegir):
    def responder():
        tops = [w for w in root.winfo_children() if isinstance(w, tk.Toplevel)]
        if not tops:
            return
        dlg = tops[-1]
        marcado = "NINGUNO"
        for w in recorrer(dlg):
            if isinstance(w, ttk.Radiobutton) and w.cget("value") == elegir:
                marcado = str(w.instate(["selected"]))
                break
        print("   al abrir el dialogo, '%s' marcado: %s" % (elegir, marcado))
        for w in recorrer(dlg):
            if isinstance(w, ttk.Radiobutton) and w.cget("value") == elegir:
                w.invoke()
        root.update()
        for w in recorrer(dlg):
            if isinstance(w, ttk.Button) and w.cget("text") == "Descargar":
                w.invoke()
                break
    root.after(400, responder)
    return descargas.preguntar_formato(root, "p")

print("1) primera vez, elijo TXT:")
print("   ->", probar("txt"))
print("   _ultimo_formato:", descargas._ultimo_formato)
print("2) la siguiente descarga, sin tocar nada (debe arrancar en TXT):")
print("   ->", probar("txt"))
print("   _ultimo_formato:", descargas._ultimo_formato)
print("3) ahora elijo CSV:")
print("   ->", probar("csv"))
print("   _ultimo_formato:", descargas._ultimo_formato)
print("4) la siguiente, sin tocar nada (debe arrancar en CSV):")
print("   ->", probar("csv"))
print("   _ultimo_formato:", descargas._ultimo_formato)
root.destroy()
