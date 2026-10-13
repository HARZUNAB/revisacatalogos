"""Pan/Zoom: comprueba que el estado pulsado ahora se distinga del reposo."""
import sys
import ttkbootstrap as ttkb
# El tema se puede pasar como argumento; sin argumento (p. ej. al correr la
# suite) se usa el mismo tema por defecto del resto de la app.
tema = sys.argv[1] if len(sys.argv) > 1 else "flatly"
raiz = ttkb.Window(themename=tema)
raiz.withdraw()
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
import plotear

fig = plt.figure(figsize=(4, 3))
tb = fig.canvas.manager.toolbar
plotear._estilar_toolbar_figura(fig)

zoom = tb._buttons['Zoom']
pan = tb._buttons['Pan']
print('tema %s' % tema)
print('  reposo   -> Zoom selectcolor=%s  Pan selectcolor=%s'
      % (zoom.cget('selectcolor'), pan.cget('selectcolor')))

tb.zoom()
raiz.update()
print('  tras zoom-> Zoom var=%s (fondo efectivo=%s)  Pan var=%s'
      % (zoom.var.get(), zoom.cget('selectcolor'), pan.var.get()))
tb.pan()
raiz.update()
print('  tras pan -> Zoom var=%s                  Pan var=%s (fondo efectivo=%s)'
      % (zoom.var.get(), pan.var.get(), pan.cget('selectcolor')))
tb.zoom(); tb.pan()
raiz.update()
print('  apagado  -> Zoom var=%s                  Pan var=%s'
      % (zoom.var.get(), pan.var.get()))
raiz.destroy()
