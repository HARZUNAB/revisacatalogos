# tests/ampliacion/bordes/

Casos borde y escenarios complejos de los módulos **puros** que ya tienen cobertura
en `../../base/`: entradas inválidas, límites de rango, combinaciones raras,
regresiones de bugs concretos.

Son tests puros (sin pantalla, sin base, sin red), así que corren siempre y
también entran al CI.

Convención de nombre: `test_<modulo>_<tema>.py` (p. ej.
`test_comparacion_bordes.py`). El sufijo evita chocar con el archivo de `base/`.

```bash
./tests/correr.sh bordes
```

## Cobertura

Un archivo por módulo de `base/`, con casos borde y regresiones de bugs:

| Archivo | Módulo |
|---|---|
| `test_comparacion_bordes.py` | `comparacion.py` |
| `test_agencias_bordes.py` | `agencias.py` |
| `test_ajuste_bordes.py` | `ajuste.py` |
| `test_sismicidad_bordes.py` | `sismicidad.py` |
| `test_asigna_perfiles_bordes.py` | `asigna_perfiles.py` |
| `test_seiscomp_a_parametros_bordes.py` | `seiscomp_a_parametros.py` |
| `test_traer_catalogos_bordes.py` | `traer_catalogos.py` |
| `test_rutas_bordes.py` | `rutas.py` |
| `test_revisa_seiscomp_bordes.py` | `revisa_seiscomp.py` (helpers puros) |
| `test_exporta_ventana_seiscomp_bordes.py` | `exporta_ventana_seiscomp.py` |

Algunos casos **fijan el comportamiento actual** de puntos que conviene revisar
más adelante (p. ej. `a_numero("nan")`, `a_iso` con 13 dígitos, `ajuste` con
posición negativa, `_banda_numero` en el borde de redondeo). Quedan anotados en
el docstring de cada test; acá solo se documentan.
