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
