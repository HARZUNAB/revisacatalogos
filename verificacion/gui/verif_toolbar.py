"""
Verifica _estilar_toolbar_figura con la app cargada (ttkbootstrap activo).

argv[1] = 'app'  -> con ttkbootstrap: el toolbar debe quedar con los colores del tema
argv[1] = 'solo' -> sin ttkbootstrap: el toolbar debe quedar como matplotlib
argv[2] = tema opcional (por defecto flatly)
"""
import sys

if len(sys.argv) > 1 and sys.argv[1] == 'app':
    import ttkbootstrap as ttkb
    TEMA = sys.argv[2] if len(sys.argv) > 2 else 'flatly'
    raiz = ttkb.Window(themename=TEMA)
    raiz.withdraw()
else:
    raiz = None

import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt

import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
import plotear

fig = plt.figure(figsize=(4, 3))
toolbar = fig.canvas.manager.toolbar

print('modo    :', sys.argv[1] if len(sys.argv) > 1 else 'solo',
      '| tema:', sys.argv[2] if len(sys.argv) > 2 else '(ninguno)')
print('antes   : toolbar bg=%s  Home bg=%s fg=%s'
      % (toolbar.cget('bg'), toolbar._buttons['Home'].cget('bg'),
         toolbar._buttons['Home'].cget('fg')))

plotear._estilar_toolbar_figura(fig)
raiz and raiz.update()

print('despues : toolbar bg=%s' % toolbar.cget('bg'))
for texto, b in toolbar._buttons.items():
    extra = ''
    if b.winfo_class() == 'Checkbutton':
        extra = ' selectcolor=%s' % b.cget('selectcolor')
    print('  %-9s %-13s bg=%-9s fg=%-9s relief=%s bd=%s%s'
          % (texto, b.winfo_class(), b.cget('bg'), b.cget('fg'),
             b.cget('relief'), b.cget('borderwidth'), extra))
if raiz is not None:
    c = __import__('ttkbootstrap').style.Style.get_instance().colors
    print('tema    : bg=%s fg=%s selectbg=%s border=%s'
          % (c.bg, c.fg, c.selectbg, c.border))
    print('label   : bg=%s fg=%s'
          % (toolbar._message_label.cget('bg'),
             toolbar._message_label.cget('fg')))
