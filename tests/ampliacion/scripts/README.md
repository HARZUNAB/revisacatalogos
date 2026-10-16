# tests/ampliacion/scripts/

Tests de los módulos hoy **script-style**, que ejecutan código al importar y leen
`sys.argv` en el nivel superior.

**Antes de testearlos hay que refactorizarlos**: mover la lógica a `main(argv=None)`
y envolver la ejecución en `if __name__ == "__main__"`. Módulos pendientes:

- `compara.py` (refactorizado)
- `repetidos.py` (refactorizado)
- `repetidosexclu.py` (refactorizado)
- `revisaselect.py` (refactorizado)
- `revisacollect.py` (refactorizado)
- `revisaexcluidos.py` (refactorizado)
- `proc_query_harz_2.py` (refactorizado)

Una vez refactorizado un módulo, su test va aquí con nombre
`test_<modulo>_<tema>.py` (con **stub de pandas** si el módulo lo importa, para
que corra en CI).

```bash
./tests/correr.sh scripts
```

## Arnes de regresión antes/después (`arnes_refactor.py`)

Refactorizar un script no debe cambiar lo que ve `app.py`: mismos argumentos,
mismo stdout (incluidos los marcadores `@@PROGRESO@@`) y mismos archivos. Para
garantizarlo, antes de tocar el código se **captura la salida actual como golden**
y después se verifica que siga idéntica.

```bash
# Antes del refactor: captura y versiona el golden (estado actual).
python3 tests/ampliacion/scripts/arnes_refactor.py capturar compara.py compara \
    -- eventquery.csv local.csv

# Después del refactor: debe decir "OK: la salida es idéntica".
python3 tests/ampliacion/scripts/arnes_refactor.py verificar compara.py compara \
    -- eventquery.csv local.csv
```

Cada *caso* es una carpeta `casos/<caso>/`. Los archivos de primer nivel son las
fixtures que se pasan por argumento (se copian a `entrada/`). Si el caso tiene
una subcarpeta `cwd/`, su contenido se copia a la raíz del temporal: es para los
scripts que leen rutas fijas relativas al cwd y que `app.py` invoca **sin
argumentos** (`revisaselect.py` y su `select.out`). El script se corre como
subproceso (igual que `app.py`): `RV_PROG=1`, en un temporal, en dos
modos —**app** (sin `RV_ENTREGABLES`) y **entregables** (`RV_ENTREGABLES=1`)— y
se guarda stdout + código de salida + un manifiesto sha256 de todo lo generado.
El golden queda en `golden/<caso>.txt`, versionado como regresión permanente.
Los *timestamps de impresión* (fechas recientes, como el `Impresion:` del `.dat`)
se normalizan a `<TS>` tanto en stdout como en el contenido de los archivos, así
el golden es reproducible; las fechas históricas de los fixtures no se tocan.

Un módulo puede tener **varios casos** (cada uno con su golden), p. ej.
`repetidos_3csv` y `repetidos_2csv` para cubrir con y sin el catálogo de
SeisComp; el nombre del caso ya incluye el módulo.

Es una herramienta **local**: correr el script de verdad necesita sus
dependencias (p. ej. pandas), que el CI no instala. Los unit tests de las
funciones extraídas sí corren en CI.

Procedimiento por módulo:

1. Fixtures en `casos/<modulo>[...]/` (uno o más casos por módulo).
2. `capturar` → commit del golden (pre-refactor).
3. Refactor (`main(argv)` + guard).
4. `verificar` → idéntico.
5. Unit tests de lo extraído.
6. Commit (golden + refactor + tests).
