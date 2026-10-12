import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
import csv
import revisa_seiscomp as R

print("DECIMALES_COORD =", R.DECIMALES_COORD)
print()

# --- _numero: coordenadas a 3, profundidad/magnitud a 1 ---
casos = [
    ("_numero coord lat", R._numero("-26.155641555786133", R.DECIMALES_COORD)),
    ("_numero coord lon", R._numero("-26.16", R.DECIMALES_COORD)),
    ("_numero coord int", R._numero("-22.2", R.DECIMALES_COORD)),
    ("_numero prof", R._numero("96.04", 1)),
    ("_numero mag", R._numero("2.94", 1)),
    ("_numero mag_est", R._numero("1.237", 1)),
    ("_numero vacio", R._numero("", R.DECIMALES_COORD)),
]
for n, v in casos:
    print("%-18s -> %r" % (n, v))
print()

# --- _banda_numero a 3 decimales ---
print("_banda_numero (token, valor) -> bool")
banda = [
    ("-26", "-26.155641555786133"),   # redondea -26.156 -> int -26 -> True
    ("-26", "-26.9999"),              # round3 -27.0 -> int -27 -> False
    ("-27", "-26.9999"),              # -> banda -27 -> True
    ("-26.156", "-26.155641555786133"),  # punto exacto a 3 decimales
    ("-26.16", "-26.155641555786133"),   # token con 2 decimales
    ("-25", "-25.74"),                # int trunc -> -25 -> True
    ("-26", "-25.74"),                # -25.74 -> -25 -> False
]
for tok, val in banda:
    print("  %-10s %-20s -> %s" % (tok, val, R._banda_numero(val, tok)))
