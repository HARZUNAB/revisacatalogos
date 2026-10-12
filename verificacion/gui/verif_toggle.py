"""Zoom/Pan: el estado de los botones debe comportarse igual con y sin el estilo."""
import sys
import ttkbootstrap as ttkb
raiz = ttkb.Window(themename='flatly'); raiz.withdraw()
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
import plotear

def secuencia(tb):
    z, p = tb._buttons['Zoom'], tb._buttons['Pan']
    out = []
    tb.zoom(); out.append(('zoom', z.var.get(), p.var.get()))
    tb.pan();  out.append(('pan',  z.var.get(), p.var.get()))
    tb.zoom(); out.append(('zoom', z.var.get(), p.var.get()))
    tb.pan();  out.append(('pan',  z.var.get(), p.var.get()))
    return out

fig1 = plt.figure(); tb1 = fig1.canvas.manager.toolbar
sin = list(secuencia(tb1))

fig2 = plt.figure(); tb2 = fig2.canvas.manager.toolbar
plotear._estilar_toolbar_figura(fig2)
con = list(secuencia(tb2))

print('sin estilo :', sin)
print('con estilo :', con)
print('identico   :', sin == con)
raiz.destroy()
