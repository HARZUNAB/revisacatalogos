"""Prueba contra el descargas.py real, pulsando los radios de verdad."""
import tkinter as tk
from tkinter import ttk
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
import descargas

root = tk.Tk()
resultados = {}


def recorrer(w):
    for hijo in w.winfo_children():
        yield hijo
        for h in recorrer(hijo):
            yield h


def correr(nombre, al_aceptar):
    """Abre el dialogo real, pulsa un radio y 'Descargar', y devuelve la eleccion."""
    def al_responder():
        top = [w for w in root.winfo_children() if isinstance(w, tk.Toplevel)]
        if not top:
            resultados[nombre] = "no se abrio el dialogo"
            return
        dlg = top[0]
        # pulsar el radio que corresponda y luego el boton principal
        for w in recorrer(dlg):
            if isinstance(w, ttk.Radiobutton) and w.cget("value") == al_aceptar:
                w.invoke()
                break
        root.update()
        for w in recorrer(dlg):
            if isinstance(w, ttk.Button) and "Descargar" in w.cget("text"):
                w.invoke()
                return
        resultados[nombre] = "no se encontro el boton Descargar"
    root.after(300, al_responder)
    return descargas.preguntar_formato(root, "prueba de formato")

print("1) marca TXT:")
resultados["txt"] = correr("txt", "txt")
print("   ->", resultados["txt"])
print("2) marca CSV:")
resultados["csv"] = correr("csv", "csv")
print("   ->", resultados["csv"])
print("3) cancela:")
def solo_cancelar():
    for w in root.winfo_children():
        if isinstance(w, tk.Toplevel):
            w.destroy()
root.after(300, solo_cancelar)
resultados["cancel"] = descargas.preguntar_formato(root, "prueba de formato")
print("   ->", resultados["cancel"])

print()
print("RESUMEN:")
print("  elegir TXT  ->", resultados["txt"], "(esperado txt)")
print("  elegir CSV  ->", resultados["csv"], "(esperado csv)")
print("  cancelar    ->", resultados["cancel"], "(esperado None)")

# la ultima eleccion quedo guardada
print("  _ultimo_formato ahora:", descargas._ultimo_formato, "(esperado txt)")
root.destroy()
