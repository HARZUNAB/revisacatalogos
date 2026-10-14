# tests/base/ — suite base (congelada)

Esta carpeta es la **suite unitaria entregada como base**: una foto de la
cobertura que ya existe, con un test por módulo puro del proyecto.

**Base congelada: no se edita.** Es la referencia conocida y verde (232 tests).
Si aparece algo nuevo por cubrir —un módulo sin tests, casos borde, GUI, base,
red— va a `../ampliacion/`, no acá. Así se distingue de un vistazo lo que ya
estaba de lo que se fue agregando.

| Archivo | Módulo |
|---|---|
| `test_comparacion.py` | `comparacion.py` |
| `test_agencias.py` | `agencias.py` |
| `test_rutas.py` | `rutas.py` |
| `test_seiscomp_a_parametros.py` | `seiscomp_a_parametros.py` |
| `test_traer_catalogos.py` | `traer_catalogos.py` |
| `test_ajuste.py` | `ajuste.py` |
| `test_sismicidad.py` | `sismicidad.py` |
| `test_asigna_perfiles.py` | `asigna_perfiles.py` |
| `test_revisa_seiscomp.py` | `revisa_seiscomp.py` (helpers puros) |
| `test_exporta_ventana_seiscomp.py` | `exporta_ventana_seiscomp.py` (geometría) |

Cómo correrla:

```bash
./tests/correr.sh base
# o
.venv/bin/python -m pytest tests/base
```

Ver `../README.md` para las convenciones y la regla base / ampliación.
