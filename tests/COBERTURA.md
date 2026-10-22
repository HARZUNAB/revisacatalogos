# tests/COBERTURA.md — índice de cobertura

Vista transversal de la suite de tests: **qué prueba cada grupo** y **qué
archivo cubre cada módulo** del proyecto. Es el mapa rápido para saber dónde
está el test de algo y a qué grupo pertenece.

- El **detalle por grupo** (convenciones, dependencias real/sintético/mock,
  tableros) vive en el `README.md` de cada carpeta.
- Se **mantiene a mano**: al agregar, mover o renombrar un test, se actualiza la
  fila del módulo correspondiente aquí.
- Convenciones generales y regla base/ampliación: `README.md`.

## Grupos

| Grupo | Marcador | Corre en CI | Qué cubre |
|---|---|---|---|
| `base/` | — | sí | Suite entregada, **congelada** (232 tests). Módulos puros. |
| `ampliacion/modulos/` | — | sí | Módulos puros nuevos (`generajson`, `prog`, `descargas`, `traequery`). |
| `ampliacion/bordes/` | — | sí | Casos borde de los diez módulos de `base/`. |
| `ampliacion/red/` | `red` | sí (mock) | `consultaapi` y las descargas SSH/SCP de `traer_catalogos`. |
| `ampliacion/db/` | `db` | no | Capa de base (`psycopg2` mockeado). |
| `ampliacion/gui/` | `gui` | no (`DISPLAY`) | Interfaz Tk/ttkbootstrap. |
| `ampliacion/scripts/` | — | sí | Scripts refactorizados + arnés de regresión con goldens. |

La corrida por defecto (`./tests/correr.sh`) usa `-m "not gui and not db"`; por
eso `red`, `modulos`, `bordes` y `scripts` sí entran al CI.

## Índice por módulo

Cada fila dice en qué grupo(s) está cubierto el módulo, los archivos de test que
lo cubren y si eso corre en CI. «parcial» = una parte corre en CI (los grupos
sin marcador) y otra no (`gui`/`db`).

| Módulo | Grupo(s) | Archivo(s) | CI |
|---|---|---|---|
| `agencias.py` | base, bordes | `base/test_agencias.py`, `bordes/test_agencias_bordes.py` | sí |
| `ajuste.py` | base, bordes | `base/test_ajuste.py`, `bordes/test_ajuste_bordes.py` | sí |
| `app.py` | gui | `gui/test_app_principal.py`, `gui/test_app_ventanas.py`, `gui/test_app_dialogos.py`, `gui/test_app_agencias.py` | no |
| `asigna_perfiles.py` | base, bordes | `base/test_asigna_perfiles.py`, `bordes/test_asigna_perfiles_bordes.py` | sí |
| `comparacion.py` | base, bordes | `base/test_comparacion.py`, `bordes/test_comparacion_bordes.py` | sí |
| `compara.py` | scripts | `scripts/test_compara_helpers.py` | sí |
| `consultaapi.py` | red | `red/test_consultaapi_fechas.py`, `red/test_consultaapi_cuadrantes.py` | sí |
| `cruza_nopub.py` | modulos | `modulos/test_cruza_nopub.py` | sí |
| `cruce_noact.py` | modulos, gui, bordes | `modulos/test_cruce_noact.py`, `gui/test_rs_no_actualizados.py`, `gui/test_plotear_panel.py`, `gui/test_plotear_helpers.py`, `modulos/test_generajson_procesar.py` | parcial |
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

## Arnés de regresión

`scripts/arnes_refactor.py` compara la salida de los siete scripts
refactorizados contra un **golden** guardado en `scripts/golden/` (stdout, código
de salida y manifiesto sha256 de lo generado). Son **8 casos**:

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

Verificación: `./tests/correr.sh scripts` (los `test_*_helpers.py` de `scripts/`
corren además el arnés como parte de la suite).

## Cómo regenerar

No hay generación automática: el índice se arma a mano. Para revisarlo o
actualizarlo:

```bash
# Listar los tests que se colectan, por grupo
./tests/correr.sh todo --collect-only -q      # necesita DISPLAY

# Contar las funciones de test por archivo
grep -rc "def test_" tests --include='*.py'
```

Los conteos de `def test_` son aproximados (los `parametrize` expanden a más
casos).

## Ver también

- `README.md` — convenciones, cómo correrlos y regla base/ampliación.
- `base/README.md` — la suite entregada (congelada).
- `ampliacion/README.md` — subcarpetas y marcadores.
- `ampliacion/{modulos,bordes,red,db,gui,scripts}/README.md` — detalle por grupo.
