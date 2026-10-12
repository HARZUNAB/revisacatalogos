import tkinter as tk
from tkinter import ttk

root = tk.Tk()
print("sin ttkbootstrap:")
try:
    ttk.Label(root, text="x", bootstyle="secondary")
    print("  bootstyle ACEPTADO")
except Exception as e:
    print("  bootstyle RECHAZADO:", type(e).__name__)

import ttkbootstrap   # lo importa la app
print("con ttkbootstrap:")
try:
    ttk.Label(root, text="x", bootstyle="secondary")
    print("  bootstyle ACEPTADO")
except Exception as e:
    print("  bootstyle RECHAZADO:", type(e).__name__)
root.destroy()
