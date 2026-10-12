"""End-to-end: abrir el panel, abrir detalle y confirmar el toolbar del detalle."""
import json, os, sys, tempfile, tkinter as tk
from tkinter import ttk
import ttkbootstrap as ttkb
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
os.chdir(tempfile.mkdtemp(prefix='tb_'))
import matplotlib
matplotlib.use('TkAgg')

ev = [{'id': 'E%03d' % i, 'fecha hora': '2026-01-0%d 0%d:00:00' % (1 + i, i),
       'latitud': -31.0 + i * 0.1, 'longitud': -64.0 + i * 0.1, 'prof': 10.0 + i,
       'magnitud': 3.0 + i * 0.2, 'tipo': 'ML',
       'perfil': 'P001' if i < 4 else 'P002', 'sospechoso': i % 2 == 0,
       'percibido': 'N',
       'analistas': [{'fuente': 'Seisan', 'analistas': ['Gomez, J.']}]} for i in range(6)]
ev.append({'id': 'E900', 'fecha hora': '2026-01-09 09:00:00', 'latitud': -32.0,
           'longitud': -65.0, 'prof': 5.0, 'magnitud': 4.0, 'tipo': 'ML',
           'perfil': None, 'sospechoso': False, 'percibido': 'N'})
os.makedirs('datos', exist_ok=True)
json.dump(ev, open('datos/eventos_prueba.json', 'w'))

raiz = ttkb.Window(themename='flatly')
raiz.withdraw()
import plotear

TRAZA = open('/tmp/opencode/tb_panel.log', 'w')


def anot(m):
    TRAZA.write(m + '\n')
    TRAZA.flush()


def rec(w):
    for h in w.winfo_children():
        yield h
        for x in rec(h):
            yield x


_orig = plotear._estilar_toolbar_figura
def _traced(fig):
    import sys as _s
    tb = getattr(getattr(fig.canvas, 'manager', None), 'toolbar', None)
    print('ESTILANDO fig num=%s toolbar=%s ttkboot=%s style=%s'
          % (getattr(fig, 'number', '?'), tb is not None,
             'ttkbootstrap' in _s.modules,
             __import__('ttkbootstrap').style.Style.get_instance()),
          flush=True)
    _orig(fig)
    if tb is not None:
        print('   -> Home bg=%s' % tb._buttons['Home'].cget('bg'), flush=True)
plotear._estilar_toolbar_figura = _traced

real_raiz = plotear._asegurar_raiz()
real_raiz.withdraw()


def abrir_detalle():
    for w in rec(real_raiz):
        if isinstance(w, ttk.Button) and w.cget('text') == 'Abrir detalle':
            w.invoke()
            anot('se pulso Abrir detalle')
            return
    anot('NO se encontro el boton Abrir detalle')


def revisar():
    import matplotlib.pyplot as plt
    # La ventana de detalle es la que se creo al pulsar 'Abrir detalle':
    # se toma la de mayor numero, que es la ultima en crearse.
    num = max(plt.get_fignums())
    fig = plt.figure(num)
    tb = getattr(fig.canvas, 'manager', None)
    tb = getattr(tb, 'toolbar', None)
    ventana = getattr(fig.canvas.manager, 'window', None)
    anot('figura de detalle num=%d titulo=%r'
         % (num, ventana.title() if ventana is not None else None))
    anot('toolbar bg=%s' % tb.cget('bg'))
    for texto, b in tb._buttons.items():
        anot('  %-9s %-13s bg=%-9s fg=%-9s relief=%s bd=%s selectcolor=%s'
             % (texto, b.winfo_class(), b.cget('bg'), b.cget('fg'),
                b.cget('relief'), b.cget('borderwidth'),
                b.cget('selectcolor') if b.winfo_class() == 'Checkbutton' else '-'))
    anot('label de mensajes: bg=%s fg=%s'
         % (tb._message_label.cget('bg'), tb._message_label.cget('fg')))
    anot('fin')
    os._exit(0)


real_raiz.after(1500, abrir_detalle)
real_raiz.after(4500, revisar)
plotear.abrir_panel(None, 'datos/eventos_prueba.json', 'seisan')
real_raiz.mainloop()
