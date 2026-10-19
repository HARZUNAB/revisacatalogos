# Tests unitarios de RCS

**Documento de la suite de tests unitarios**

H. Riquelme — OPA-CSN, Centro Sismológico Nacional, Universidad de Chile.

Versión 1.1 — 19 de octubre de 2026.

---

## 1. Introducción

Los **tests unitarios** de RCS son un conjunto de pruebas automáticas escritas
con **pytest** que verifican las funciones puras del sistema y su interfaz sin
necesidad de pantalla, base de datos ni red en la corrida por defecto. Se
ejecutan en segundos y constituyen la red de seguridad para desarrollar y
refactorizar con confianza.

La suite vive en la carpeta `tests/`, en la raíz del proyecto, y se organiza en
dos niveles:

- `tests/base/` — la **suite entregada**: una foto de la cobertura que ya existía,
  con un test por módulo puro (232 tests). Queda **congelada**.
- `tests/ampliacion/` — todo lo que se agrega después: módulos sin cubrir, casos
  borde, interfaz, base, red y scripts refactorizados.

**Regla base / ampliación**: `tests/base/` no se edita. Lo nuevo va siempre a
`tests/ampliacion/`, de modo que se distingue de un vistazo lo que ya estaba de
lo que se fue agregando. El detalle de las convenciones está en `tests/README.md`
y el mapa transversal en `tests/COBERTURA.md`.

No confundir con `verificacion/`, que son **comprobaciones end-to-end** (ventanas
reales, base simulada, datos de prueba), no tests unitarios.

## 2. Grupos

Los tests se agrupan por carpeta y, en algunos casos, por un **marcador** de
pytest que permite incluirlos o excluirlos de la corrida. La corrida por defecto
(`./tests/correr.sh`) usa el filtro `-m "not gui and not db"`.

| Grupo | Marcador | Corre en CI | Qué cubre |
|---|---|---|---|
| `base/` | — | sí | Suite entregada, congelada (232 tests). Módulos puros. |
| `ampliacion/modulos/` | — | sí | Módulos puros nuevos (`generajson`, `prog`, `descargas`, `traequery`). |
| `ampliacion/bordes/` | — | sí | Casos borde de los diez módulos de `base/`. |
| `ampliacion/red/` | `red` | sí (mock) | `consultaapi` y las descargas SSH/SCP de `traer_catalogos`. |
| `ampliacion/db/` | `db` | no | Capa de base (`psycopg2` mockeado). |
| `ampliacion/gui/` | `gui` | no (`DISPLAY`) | Interfaz Tk/ttkbootstrap. |
| `ampliacion/scripts/` | — | sí | Scripts refactorizados + arnés de regresión con goldens. |

Los grupos `red`, `modulos`, `bordes` y `scripts` sí entran al CI; `gui` y `db`
quedan fuera porque necesitan pantalla o base (o dependencias pesadas).

## 3. Índice por módulo

Cada fila indica en qué grupo(s) está cubierto un módulo, los archivos de test
que lo cubren y si eso corre en CI. «parcial» significa que una parte corre en
CI (los grupos sin marcador) y otra no (`gui`/`db`).

| Módulo | Grupo(s) | Archivo(s) | CI |
|---|---|---|---|
| `agencias.py` | base, bordes | `base/test_agencias.py`, `bordes/test_agencias_bordes.py` | sí |
| `ajuste.py` | base, bordes | `base/test_ajuste.py`, `bordes/test_ajuste_bordes.py` | sí |
| `app.py` | gui | `gui/test_app_principal.py`, `gui/test_app_ventanas.py`, `gui/test_app_dialogos.py`, `gui/test_app_agencias.py` | no |
| `asigna_perfiles.py` | base, bordes | `base/test_asigna_perfiles.py`, `bordes/test_asigna_perfiles_bordes.py` | sí |
| `comparacion.py` | base, bordes | `base/test_comparacion.py`, `bordes/test_comparacion_bordes.py` | sí |
| `compara.py` | scripts | `scripts/test_compara_helpers.py` | sí |
| `consultaapi.py` | red | `red/test_consultaapi_fechas.py`, `red/test_consultaapi_cuadrantes.py` | sí |
| `descargas.py` | modulos, gui | `modulos/test_descargas_archivos.py`, `modulos/test_descargas_interfaz.py`, `gui/test_descargas_dialogo.py`, `gui/test_descargas_widgets.py` | parcial |
| `disponibilidad.py` | modulos | `modulos/test_disponibilidad.py` | sí |
| `exporta_ventana_seiscomp.py` | base, bordes, db | `base/test_exporta_ventana_seiscomp.py`, `bordes/test_exporta_ventana_seiscomp_bordes.py`, `db/test_exporta_ventana_db.py` | parcial |
| `generajson.py` | modulos | `modulos/test_generajson_args.py`, `modulos/test_generajson_distancia.py`, `modulos/test_generajson_analistas.py`, `modulos/test_generajson_procesar.py` | sí |
| `plotear.py` | gui | `gui/test_plotear_helpers.py`, `gui/test_plotear_figuras.py`, `gui/test_plotear_panel.py`, `gui/test_plotear_abrir.py` | no |
| `proc_query_harz_2.py` | scripts | `scripts/test_proc_query_harz_2_helpers.py` | sí |
| `prog.py` | modulos | `modulos/test_prog.py` | sí |
| `repetidosexclu.py` | scripts | `scripts/test_repetidosexclu_helpers.py` | sí |
| `repetidos.py` | scripts | `scripts/test_repetidos_helpers.py` | sí |
| `revisacollect.py` | scripts | `scripts/test_revisacollect_helpers.py` | sí |
| `revisaexcluidos.py` | scripts | `scripts/test_revisaexcluidos_helpers.py` | sí |
| `revisa_seiscomp.py` | base, bordes, gui | `base/test_revisa_seiscomp.py`, `bordes/test_revisa_seiscomp_bordes.py`, `gui/test_rs_panel.py`, `gui/test_rs_no_actualizados.py`, `gui/test_rs_detalle.py`, `gui/test_rs_estaciones.py`, `gui/test_rs_analisis.py`, `gui/test_rs_main.py` | parcial |
| `revisaselect.py` | scripts | `scripts/test_revisaselect_helpers.py` | sí |
| `rutas.py` | base, bordes | `base/test_rutas.py`, `bordes/test_rutas_bordes.py` | sí |
| `seiscomp_a_parametros.py` | base, bordes | `base/test_seiscomp_a_parametros.py`, `bordes/test_seiscomp_a_parametros_bordes.py` | sí |
| `sismicidad.py` | base, bordes | `base/test_sismicidad.py`, `bordes/test_sismicidad_bordes.py` | sí |
| `solicita_catalogos.py` | gui | `gui/test_solicita_catalogos.py` | no |
| `traequery.py` | modulos | `modulos/test_traequery.py` | sí |
| `traer_catalogos.py` | base, bordes, red | `base/test_traer_catalogos.py`, `bordes/test_traer_catalogos_bordes.py`, `red/test_traer_catalogos_conexion.py`, `red/test_traer_catalogos_descargas.py` | sí |
| `verifica_entorno.py` | db | `db/test_verifica_entorno.py` | no |

Todos los módulos del proyecto tienen al menos un test.

La cobertura de la última ampliación incluye `test_disponibilidad.py` (parser de
`scart`, fallback SDS→tiempo real, evidencia y mensajes de progreso),
`test_rs_estaciones.py` (tooltip por fila y consulta on-demand con barra de
progreso) y `test_rs_analisis.py` (tres contadores de evidencia: verificadas,
indicios y sin evidencia).

## 4. Arnés de regresión

`tests/ampliacion/scripts/arnes_refactor.py` compara la salida de los siete
scripts refactorizados contra un **golden** guardado en
`tests/ampliacion/scripts/golden/` (stdout, código de salida y un manifiesto
sha256 de lo generado). Son **8 casos**:

| Módulo | Caso |
|---|---|
| `compara.py` | `compara -- eventquery.csv local.csv` |
| `repetidos.py` | `repetidos_2csv -- publica.csv seisan.csv` |
| `repetidos.py` | `repetidos_3csv -- publica.csv seisan.csv seiscomp.csv` |
| `repetidosexclu.py` | `repetidosexclu -- excluidos.csv select.csv` |
| `proc_query_harz_2.py` | `proc_query_harz_2 -- eventquery.csv ../salida.dat` |
| `revisaselect.py` | `revisaselect` |
| `revisacollect.py` | `revisacollect` |
| `revisaexcluidos.py` | `revisaexcluidos` |

Es una herramienta local: correr el script de verdad necesita sus dependencias
(p. ej. pandas), que el CI no instala; los unit tests de las funciones extraídas
sí corren en CI.

## 5. Documentación relacionada

La documentación de los tests unitarios vive casi toda dentro de `tests/`, más
una referencia en el README raíz y la frontera con `verificacion/`.

| Archivo | Qué documenta |
|---|---|
| `tests/README.md` | Doc principal: niveles base/ampliación, convenciones, cómo correrlos y marcadores. |
| `tests/COBERTURA.md` | Índice transversal módulo → grupo → archivo + leyenda de grupos + arnés. |
| `tests/base/README.md` | La suite entregada, congelada (232 tests) y su tabla archivo → módulo. |
| `tests/ampliacion/README.md` | Subcarpetas de ampliación, marcadores y cómo agregar un test. |
| `tests/ampliacion/modulos/README.md` | Módulos puros nuevos que corren en CI. |
| `tests/ampliacion/bordes/README.md` | Casos borde de los diez módulos de `base/`. |
| `tests/ampliacion/red/README.md` | Capa de red con mock y los stubs de pandas/requests para CI. |
| `tests/ampliacion/db/README.md` | Capa de base (PostgreSQL/`psycopg2` mockeado). |
| `tests/ampliacion/gui/README.md` | Interfaz: tablero de cobertura, principio «interfaz real» y nota «no todos necesitan DISPLAY». |
| `tests/ampliacion/scripts/README.md` | Scripts refactorizados y el arnés de regresión con goldens. |
| `verificacion/README.md` | Aclara que las comprobaciones end-to-end NO son tests unitarios. |
| `README.md` (raíz) | Sección «Tests»: los dos niveles y comandos del corredor. |

Artefactos de apoyo (no son documentación, pero forman parte del andamiaje):

- `pytest.ini` — configuración y registro de marcadores (`gui`, `db`, `red`, `lento`).
- `tests/correr.sh` — corredor y definición de los grupos.
- `tests/ampliacion/_plantilla.py` — molde de test.
- `conftest.py` (raíz y por grupo) — fixtures compartidas.
- `requirements-dev.txt` — dependencias de test (lo único que instala el CI).

## 6. Cómo correrlos

```bash
./tests/correr.sh                  # todo, menos gui y db
./tests/correr.sh base             # solo la suite base (congelada)
./tests/correr.sh ampliacion       # lo agregado, menos gui y db
./tests/correr.sh modulos          # módulos puros nuevos
./tests/correr.sh bordes           # casos borde
./tests/correr.sh scripts          # scripts refactorizados + arnés
./tests/correr.sh red              # red (con mock)
./tests/correr.sh gui              # interfaz (necesita DISPLAY)
./tests/correr.sh db               # base de datos
./tests/correr.sh -k comparacion   # filtro por nombre
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
