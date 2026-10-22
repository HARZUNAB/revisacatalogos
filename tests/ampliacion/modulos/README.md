# tests/ampliacion/modulos/

Cobertura nueva de **módulos puros** que no estaban en la suite base:
`generajson.py`, `cruza_nopub.py` (cruce de no publicados con la otra fuente),
`cruce_noact.py` (clasificación de no actualizados), `prog.py`, `descargas.py` (nombres, escritura y la lógica de interfaz con dobles,
sin Tk real), `disponibilidad.py` (parser de `scart`, fallback SDS→tiempo real,
evidencia y progreso) y `traequery.py` (refactorizado a `main()` + guard). Son tests sin pantalla, sin base y sin red, así que corren
siempre y entran al CI.

Van aquí y no en `bordes/` porque `bordes/` es para casos borde de módulos **ya
cubiertos** por la base; esto es cubrir lógica que todavía no tenía ningún
test.

Distinción con `scripts/`: los de `scripts/` son módulos que ejecutan código al
importar y hay que refactorizar antes; estos ya son importables tal cual.

Convención de nombre: `test_<modulo>_<tema>.py` para que el basename no choque
con otro archivo de la suite.

```bash
./tests/correr.sh modulos
```
