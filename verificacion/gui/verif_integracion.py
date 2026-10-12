"""_indicador_modo_interaccion debe aplicar el estilo, y no romper el modo."""
import sys
import tkinter as tk
import ttkbootstrap as ttkb
raiz = ttkb.Window(themename='flatly'); raiz.withdraw()
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
import plotear

fig = plt.figure(figsize=(4, 3))
tb = fig.canvas.manager.toolbar
print('antes          : Home bg=%s' % tb._buttons['Home'].cget('bg'))

plotear._indicador_modo_interaccion(fig)
raiz.update()

print('tras indicador : Home bg=%s fg=%s | Zoom selectcolor=%s'
      % (tb._buttons['Home'].cget('bg'), tb._buttons['Home'].cget('fg'),
         tb._buttons['Zoom'].cget('selectcolor')))
print('modo sigue funcionando:')
tb.zoom(); raiz.update()
print('   toolbar.mode=%s  Zoom var=%s' % (tb.mode.name, tb._buttons['Zoom'].var.get()))
tb.zoom(); raiz.update()
print('   toolbar.mode=%s' % tb.mode.name)
print('indicador de texto en la figura: %r'
      % (fig.texts[0].get_text() if fig.texts else '(no hay)'))

# Figura embebida (mini-mapa del panel): sin manager, no debe romper nada.
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
fig_mini = plt.figure()
FigureCanvasTkAgg(fig_mini, master=raiz)
plotear._indicador_modo_interaccion(fig_mini)
print('figura sin manager: _indicador_modo_interaccion no lanzo error')
raiz.destroy()
