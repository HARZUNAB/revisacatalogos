"""Repetidos: descargar_texto no debe abrir el dialogo de formato."""
import os, sys, tempfile, tkinter as tk
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
TMP = tempfile.mkdtemp(prefix='rep_')
os.chdir(TMP)
os.makedirs('informes', exist_ok=True)
lineas = ["  1   E001   2026-01-01 00:00:00   ML  3.1  E001  E001",
          "  2   E002   2026-01-02 00:00:00   ML  3.4  E002  E002"]
open('informes/rep_seisan.txt', 'w').write("\n".join(lineas) + "\n")

import descargas

info = {'dialogo': 'NO se abrio el dialogo de formato'}
orig = descargas.preguntar_formato
def guardia(*a, **k):
    info['dialogo'] = 'SE ABRIO el dialogo de formato'
    return orig(*a, **k)
descargas.preguntar_formato = guardia

# El aviso de exito es un messagebox bloqueante: se stubea para no colgar el test.
descargas._avisar_exito = lambda padre, ruta: info.update(aviso=True)

root = tk.Tk()
ruta = descargas.descargar_texto(root, lineas, 'rep_seisan')
print('dialogo      :', info['dialogo'])
print('ruta         :', ruta)
print('ext          :', os.path.splitext(ruta)[1] if ruta else None)
print('existe       :', os.path.exists(ruta) if ruta else False)
if ruta:
    print('contenido igual:', open(ruta, encoding='utf-8').read() == "\n".join(lineas) + "\n")
    print('primeros 3 bytes:', open(ruta, 'rb').read(3).hex())
print('descargas/   :', sorted(os.listdir('descargas')) if os.path.isdir('descargas') else 'NINGUNA')
root.destroy()
