# tests/ampliacion/modulos/

Cobertura nueva de **módulos puros** que no estaban en la suite base:
`generajson.py`, `prog.py`, `descargas.py` y `traequery.py` (refactorizado a
`main()` + guard). Son tests sin pantalla, sin base y sin red, así que corren
siempre y entran al CI.

Van acá y no en `bordes/` porque `bordes/` es para casos borde de módulos **ya
cubiertos** por la base; esto es cubrir lógica que todavía no tenía ningún
test.

Distinción con `scripts/`: los de `scripts/` son módulos que ejecutan código al
importar y hay que refactorizar antes; estos ya son importables tal cual.

Convención de nombre: `test_<modulo>_<tema>.py` para que el basename no choque
con otro archivo de la suite.

```bash
./tests/correr.sh modulos
```
