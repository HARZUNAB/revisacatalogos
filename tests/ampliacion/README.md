# tests/ampliacion/ — suite en ampliación

Acá va **todo lo que se agrega después de la base**. La base
(`../base/`) queda congelada; lo nuevo se desarrolla en esta carpeta, bajo
supervisión, a medida que se cubren módulos que hoy no tienen tests o se
profundiza en los que sí.

## Subcarpetas

| Carpeta | Qué va acá | Marcador | Corre en CI |
|---|---|---|---|
| `bordes/` | Casos borde y escenarios complejos de módulos puros ya cubiertos en `base/` | — | Sí |
| `gui/` | Interfaz: ventanas de Tk (`app.py`, `plotear.py`, ventanas de `revisa_seiscomp.py`) | `gui` | No (necesita `DISPLAY`) |
| `db/` | Base de datos: `exporta_ventana_seiscomp.py`, `verifica_entorno.py` | `db` | No (necesita PostgreSQL o mock) |
| `red/` | `consultaapi.py` y descargas, con **mock** de `requests`/SSH | `red` | Sí (es mock, sin red real) |
| `scripts/` | Módulos hoy script-style (`compara.py`, `repetidos.py`, `revisaselect.py`, …) **después** de refactorizarlos | — | Sí |

Cada subcarpeta tiene su propio `README.md` con más detalle.

## Cómo agregar un test

1. Elegí la subcarpeta según la tabla.
2. Copiá `_plantilla.py` (al lado de este README) y renombralo.
3. Nombrá el archivo **`test_<modulo>_<tema>.py`**, p. ej.
   `bordes/test_comparacion_bordes.py`, `gui/test_revisa_seiscomp_ventana.py`.

> **Ojo con los nombres de archivo.** pytest, sin `__init__.py`, exige que el
> basename sea único en toda la suite. Por eso en `ampliacion/` los archivos
> llevan sufijo de tema: un `test_comparacion.py` acá chocaría con el de
> `base/` y pytest falla con «import file mismatch».

## Marcadores

`gui` y `db` ya existen y quedan **excluidos** de la corrida por defecto y del
CI. `red` está registrado y **no** se excluye (usa mock). `lento` es para tests
informativamente costosos.

```bash
./tests/correr.sh ampliacion   # todo lo agregado, menos gui/db
./tests/correr.sh gui          # solo interfaz
./tests/correr.sh db           # solo base de datos
./tests/correr.sh red          # solo red (mock)
```

## Plantilla

`_plantilla.py` es el molde: encabezado, docstring, uso de fixtures y una nota
de cómo marcar. **No se colecta** (no empieza con `test_` ni termina en `_test`).
