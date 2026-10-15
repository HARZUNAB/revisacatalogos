# tests/ — tests unitarios

Tests **unitarios** de las funciones puras del proyecto: sin pantalla, sin base
de datos, sin red. Se ejecutan en segundos y son la base para desarrollar con
red de seguridad.

No confundir con `verificacion/`, que son **comprobaciones end-to-end**
(ventanas reales, datos de prueba, base simulada). Regla simple:

- **Función pura / lógica de cálculo** → aquí, en `tests/`.
- **Necesita la app armada, GUI, base o datos de un flujo** → `verificacion/`.

## Dos grupos: base y ampliación

| Carpeta | Qué es | Estado |
|---|---|---|
| `base/` | La suite **entregada**, un test por módulo puro. | **Congelada** (no se edita) |
| `ampliacion/` | Todo lo que se agrega después. | En crecimiento |

Regla: **la base queda congelada**. Lo nuevo —módulos sin cubrir, casos borde,
GUI, base, red, scripts— va siempre a `ampliacion/`, nunca a `base/`. Ver
`base/README.md` y `ampliacion/README.md`.

## Cómo correrlos

```bash
./tests/correr.sh                  # todo, menos gui y db
./tests/correr.sh base             # solo la suite base
./tests/correr.sh ampliacion       # solo lo agregado, menos gui y db
./tests/correr.sh gui              # solo interfaz (necesita DISPLAY)
./tests/correr.sh db               # solo base de datos
./tests/correr.sh red              # solo red (con mock)
./tests/correr.sh -k comparacion   # filtro por nombre (mantiene el filtro por defecto)
```

O directamente con pytest:

```bash
.venv/bin/python -m pytest
.venv/bin/python -m pytest tests/base -v
```

Instalación (una vez):

```bash
.venv/bin/python -m pip install -r requirements-dev.txt
```

## Convenciones

- Un archivo por módulo o tema: `tests/base/test_<modulo>.py` y, en
  `ampliacion/`, `test_<modulo>_<tema>.py`.
- **Basename único en toda la suite**: pytest, sin `__init__.py`, lo exige. Por
  eso los archivos de `ampliacion/` llevan sufijo de tema (un
  `test_comparacion.py` en ampliación chocaría con el de `base/`).
- Los nombres de los tests y los docstrings van en español, como el resto del
  proyecto.
- Los módulos del proyecto se importan por nombre plano (`import comparacion`),
  porque así los usa la app; `conftest.py` agrega la raíz al `sys.path`.
- Las pruebas que escriben archivos usan la fixture `cwd_tmp`: `rutas.p_*()`
  resuelve contra el directorio actual, así que cada test corre en un temporal.
- Marcadores: `gui`, `db`, `red`, `lento`. La corrida por defecto evita `gui` y
  `db`; `red` usa mock y sí corre.

## Estado y pendientes

Cubierto en `base/`: `comparacion`, `agencias`, `rutas`,
`seiscomp_a_parametros`, `traer_catalogos`, `ajuste`, `sismicidad`,
`asigna_perfiles`, `revisa_seiscomp` (funciones puras) y
`exporta_ventana_seiscomp` (geometría).

Cubierto en `ampliacion/modulos/`: `generajson` (parseo de args, distancia,
analistas, `procesar_csv`/resumen), `prog` (protocolo de progreso),
`descargas` (nombres, escritura de archivos y los avisos/carpeta sin Tk) y
`traequery` (refactorizado: `solicitar`, armado de argumentos y flujo
interactivo con `main()`).

Cubierto en `ampliacion/red/`: `consultaapi` (limpieza de fechas y consulta por
cuadrante de EMSC/USGS/GFZ) y la capa SSH/SCP de `traer_catalogos` (clase
`Conexion` y las descargas de Seisan/eventquery), con `requests` y `subprocess`
mockeados y sin pandas.

Cubierto en `ampliacion/scripts/`: `compara`, `repetidos`, `repetidosexclu`,
`revisaselect`, `revisacollect`, `revisaexcluidos` y `proc_query_harz_2`
(refactorizados; helpers puros con stub de pandas/Levenshtein donde aplica, y un
arnés de regresión antes/después con goldens por caso).

Cubierto en `ampliacion/bordes/`: casos borde y regresiones de los diez módulos
de `base/` (`comparacion`, `agencias`, `ajuste`, `sismicidad`,
`asigna_perfiles`, `seiscomp_a_parametros`, `traer_catalogos`, `rutas`,
`revisa_seiscomp`, `exporta_ventana_seiscomp`), un archivo por módulo.

Cubierto en `ampliacion/db/`: la capa de consulta de `exporta_ventana_seiscomp`
(configuración, conexión, eventos, inventario, bindings, actividad, estimación y
fases) y `verifica_entorno` (venv, requirements, base), con `psycopg2` mockeado.

Cubierto en `ampliacion/gui/` (marcador `gui`, necesita pantalla): la interfaz
de `descargas` (diálogo de formato, `encima_de`, `_etiqueta_secundaria` y las
descargas de tabla/texto), `app.py` completo (ventana principal, ventanas de
consulta, diálogos, agencias y cobertura) y el panel/catálogo de
`revisa_seiscomp.py`. El resto de la interfaz (`plotear.py`, ventanas de
`revisa_seiscomp.py`, `solicita_catalogos.py`) sigue pendiente; el tablero está
en `ampliacion/gui/README.md`.

Pendiente (va a `ampliacion/`), según `ampliacion/README.md`:

- **Interfaz restante** (`plotear.py`, ventanas de `revisa_seiscomp.py`,
  `solicita_catalogos.py`): `ampliacion/gui/`, marcador `gui`. Ver la tabla de
  cobertura en `ampliacion/gui/README.md`.
