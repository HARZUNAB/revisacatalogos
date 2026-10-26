# Manual técnico — RCS

Arquitectura, scripts, interfaces y parámetros ajustables.
Versión 1.15 — 25 de octubre de 2026.

Documento de referencia para quien mantiene o extiende el sistema. Para el uso
diario, ver `manual_usuario.md`. El esquema de la base de datos está en
`esquema_seiscomp.md` (y su versión para MySQL Workbench en
`esquema_seiscomp_mysql.sql`).

---

## Índice

1. [Arquitectura general](#1-arquitectura-general)
2. [Inventario de módulos](#2-inventario-de-módulos)
3. [Directorios y archivos](#3-directorios-y-archivos)
4. [Flujo por etapa](#4-flujo-por-etapa)
5. [Interfaces de línea de comandos](#5-interfaces-de-línea-de-comandos)
6. [Conexión remota y base de datos](#6-conexión-remota-y-base-de-datos)
7. [Parámetros y dónde ajustarlos](#7-parámetros-y-dónde-ajustarlos)
8. [Entradas y formatos](#8-entradas-y-formatos)
9. [Nombres de las columnas](#9-nombres-de-las-columnas)
10. [Cómo extender el sistema](#10-cómo-extender-el-sistema)
11. [Verificación y pruebas](#11-verificación-y-pruebas)

---

## 1. Arquitectura general

La aplicación es una **GUI de escritorio** (Tkinter + `ttkbootstrap`) con una
**separación parcial por capas**:

- **Interfaz y orquestación** (`app.py`, `solicita_catalogos.py`,
  `revisa_seiscomp.py`, `plotear.py`, `descargas.py`): construye ventanas,
  atiende eventos, lanza subprocesos y presenta los resultados.
- **Dominio** (`comparacion.py`, `agencias.py`, `cruce_noact.py`,
  `cruza_nopub.py`, `asigna_perfiles.py`, `sismicidad.py`, `fronteras.py`):
  reúne cálculos y reglas reutilizables, en general independientes de Tk.
- **Procesos y datos**: scripts ejecutados como subprocesos,
  `traer_catalogos.py`, `exporta_ventana_seiscomp.py`, `rutas.py` y `prog.py`.
  Acceden a red o base, ejecutan el pipeline y persisten CSV/JSON.

**No se usa MVC formal ni un backend HTTP separado.** La interfaz también
contiene lógica de presentación, filtros, orden y parte de la orquestación; por
eso la separación es parcial, no una arquitectura de tres capas estricta.

- **Directorio de trabajo**: los subprocesos se lanzan con
  `cwd=os.getcwd()`, así que las rutas relativas (`datos/`, `informes/`,
  `trabajo/`, `ploteo/`, `descargas/`) se resuelven **contra la carpeta desde
  donde se invocó la app**, no contra el código. Ejecutar siempre desde la carpeta
  del proyecto/ejecución.
- **Progreso**: los módulos que importan `prog` emiten líneas
  `@@PROGRESO@@ <fracción>` por stdout. `app.py` las reconoce y actualiza la
  barra. La emisión se activa con la variable de entorno **`RV_PROG`**, que la
  app define en cada subproceso; ejecutado a mano, un módulo no emite progreso.
- **Entregables**: la variable **`RV_ENTREGABLES=1`** habilita la escritura de
  los entregables automáticos del pipeline. Sin ella, esas escrituras van a un
  descarte (ver `rutas.entregable`).

### Mapa de alto nivel

```
supervisor.sh ──► crea .venv e instala requirements.txt
      │
      ▼
solicita_catalogos.py ──► ventana de solicitud (SSH/SCP + exportador SeisComp)
      │                     deja el estado en JSON y abre:
      ▼
app.py ──► ventana principal (orquesta subprocesos)
   ├─ análisis:  proc_query_harz_2 → revisaselect → revisacollect →
   │             compara → (atribución SeisComp) → revisaexcluidos →
   │             repetidosexclu → repetidos
   └─ paneles:   generajson (por fuente) → plotear / revisa_seiscomp
```

**Nota histórica.** RCS nace de integrar varios programas que un mismo
desarrollador había hecho por separado para tareas puntuales de la revisión.
La reunificación se hizo en un entorno asistido por IA —Visual Studio Code,
Python y Bash, y herramientas de consulta de PostgreSQL— que permitió releer,
unificar y mejorar esos códigos base hasta convertirlos en el sistema actual.

---

## 2. Inventario de módulos

| Módulo | Responsabilidad | Entradas | Salidas | Progreso |
|---|---|---|---|---|
| `app.py` | GUI: orquesta etapas, muestra registro y paneles. | `entrada.csv`, `salida.dat`, `estado.json` | — | — |
| `solicita_catalogos.py` | Ventana de solicitud y orquestación de la bajada. | período, contraseña, radio | `datos/select_*.out`, `datos/eventquery_*.csv`, export de SeisComp | — |
| `traer_catalogos.py` | Capa de red (SSH/SCP) sin GUI. | plantilla `select.inp`, fechas | `select.out`, CSV de eventquery | — |
| `rutas.py` | Rutas de salida y flag de entregables. | — | crea carpetas | — |
| `prog.py` | Protocolo `@@PROGRESO@@` por subproceso. | — | stdout | — |
| `proc_query_harz_2.py` | Normaliza el CSV público a formato Seisan y `.dat`. | CSV eventquery | `datos/new_2_*.csv`, `.dat` | Sí |
| `revisaselect.py` | Parsea `select.out`; separa válidos de excluidos. | `select.out` | `trabajo/newcollect.txt`, `trabajo/excluidostmp1.txt` | No |
| `revisacollect.py` | Arma el CSV maestro y los CSV por analista. | `trabajo/newcollect.txt` | `datos/salida_collect.csv` | No |
| `compara.py` | Compara el público contra la solución de la fuente: **no publicados** y **no actualizados**. | CSV público, CSV de la fuente | `datos/no_pub_desde_2_5_*.csv`, `datos/atribucion_*.csv`, `informes/no_act_*.txt` | Sí |
| `cruza_nopub.py` | Cruza cada no publicado con las soluciones publicadas de la otra fuente y agrega columnas informativas. | CSV de no publicados, `datos/atribucion_<otra>.csv` | mismas CSV con `Publicado_en`, `Estado`, `Dt_otra_seg`, `Dist_otra_km`, `Analista_otra` | Sí |
| `cruce_noact.py` | Clasifica los no actualizados por publicación probable y prioridad de revisión. | atribuciones crudas de ambas fuentes, catálogos locales | columnas en memoria y en el JSON del panel | Sí |
| `comparacion.py` | Comparación numérica de parámetros (funciones puras). | — | — | — |
| `revisaexcluidos.py` | Normaliza excluidos y detecta líneas anómalas. | `informes/excluidos.txt` | `datos/excluidos.csv` | No |
| `repetidos.py` | Detecta repetidos dentro de cada fuente (amplio/estricto). | CSV público, Seisan, SeisComp | `informes/rep_*.txt` | Sí |
| `repetidosexclu.py` | Cruza excluidos contra `select.out`. | CSV excluidos, CSV select | `informes/rep_seisan_exclu.txt` | Sí |
| `generajson.py` | Asigna perfil y clasifica sospechosos; escribe el JSON. | CSV de eventos | `datos/eventos_<vista>.json`, `datos/sospechosos_*.csv`, `datos/conteo_perfiles_*.json` | Sí |
| `asigna_perfiles.py` | Detecta perfiles y asigna uno por evento. | `grillas/slabP*.tmp`, `topoP*.tmp` | — | No |
| `sismicidad.py` | Clasifica un evento como **sospechoso**. | `base_2020_2026.dat` | — | No |
| `plotear.py` | Mapas y panel de análisis (matplotlib). | `eventos_<vista>.json` | figuras / descargas | No |
| `revisa_seiscomp.py` | Revisión de SeisComp: catálogo, parámetros, estaciones, análisis rápido, no actualizados. | CSV de SeisComp | tablas / descargas | — |
| `exporta_ventana_seiscomp.py` | Exporta eventos, fases y sin arribos desde la base de SeisComp. | base PostgreSQL | `datos/seiscomp_<ini>_<fin>*.csv` | — |
| `disponibilidad.py` | Consulta formas de onda en SDS y, como respaldo, en el recordstream de tiempo real. | streams, ventana | cobertura por stream | — |
| `seiscomp_a_parametros.py` | Convierte la exportación cruda al CSV de 8 columnas. | export CSV | `datos/seiscomp_parametros.csv` | — |
| `verifica_entorno.py` | Diagnóstico de entorno (venv, paquetes, base). | `requirements.txt` | stdout | — |
| `ajuste.py` | Ajuste de tamaño de ventanas (solo crecen). | — | — | — |
| `fronteras.py` | Distancia de un evento a la frontera terrestre chilena más cercana. | Natural Earth 10m | País y km en tablas, mapas y viñetas | — |
| `traequery.py` | Bajada interactiva de eventquery (legado). | input() | CSV | — |
| `supervisor.sh` | Lanzador con entorno virtual. | `requirements.txt` | — | — |
| `agencias.py` | Consulta APIs de EMSC/USGS/GFZ y normaliza respuestas. | Nuestro catálogo publicado | Listado de eventos por agencia | — |
| `consultaapi.py` | Cliente HTTP (timeout, reintentos) para catálogos remotos. | Config | JSON de eventos | — |
| `agencias.py` / `consultaapi.py` | Comparación de agencias (UI de `app.py` + plotear). | Agencias seleccionadas | Tabla «Agencias sin contraparte» y mapas | — |

> La comparación de agencias se **reutiliza** si no cambió ningún insumo: el
> período y los parámetros salen de `datos/agencias/estado.json` (`_periodo()`
> infiere inicio/fin del nombre de los archivos cuando no vino `estado.json`) y
> `_comparacion_al_dia()`/`_consulta_agencias_al_dia()` comparan contra el
> `mtime` de `datos/comparacion_agencias.json` y de `eventos_<referencia>.json`
> / `eventos_agencia_*.json`. Además, `_comparacion_al_dia()` exige que
> `version_asociacion` de `estado.json` coincida con
> `agencias.VERSION_ASOCIACION`: un cambio en el criterio de asociación invalida
> la comparación cacheada sin volver a descargar los catálogos. La cabecera de la
> ventana muestra «Reutilizada» o
> «Ejecutada» con el `timestamp` (UTC) y `_cobertura_agencias()` resume la
> ventana solicitada y la real por agencia (min/max de
> `datos/agencias/consultaapi_<AG>.csv`, con rezago), en un popup «Cobertura por
> agencia» y en la descarga. En modo «Desde/Hasta» el usuario fija el rango
> (`desde`/`hasta`, 14 díg., en el diálogo; por defecto el inicio del análisis y
> el instante de apertura). `_abrir_catalogo_comparado()` abre el listado de `datos/agencias/consultaapi_<AG>.csv`
o de `datos/todos_eventquery.csv` desde el botón «Catálogos» del popup de
cobertura, usando `revisa_seiscomp.abrir_tabla`.
`_comparacion_al_dia()` compara `desde` y `hasta`:
> cambiar el `desde` rehace; cambiar solo el `hasta` rehace salvo que la
> comparación siga dentro del TTL (atajo para el caso «hasta = ahora»). La misma
> ventana se usa para las agencias y para re-extraer el eventquery de la
> comparación (`_actualizar_eventquery`), que queda aislado y no altera el
> eventquery del análisis.

> `entregables` (CSV/TXT) solo se escriben con `RV_ENTREGABLES=1`.

---

## 3. Directorios y archivos

`rutas.py` es la **fuente única** de las carpetas de salida (relativas al
directorio de trabajo):

| Carpeta | Contenido |
|---|---|
| `datos/` | CSV/JSON de trabajo: `salida_collect.csv`, `new_2_*.csv`, `excluidos.csv`, `seiscomp_parametros.csv`, `atribucion_*.csv`, `no_pub_desde_2_5_*.csv`, `eventos_<vista>.json`, `conteo_perfiles_<vista>.json`. |
| `informes/` | Reportes de texto: `no_pub_*.txt`, `no_act_*.txt`, `rep_*.txt`, `excluidos.txt`, `revisar.txt`, `app.log` (trazabilidad de la app; rotación > 5 MB → `.log.1`). |
| `ploteo/` | Bitácora de la sesión: `percibidos.txt`. |
| `trabajo/` | Intermedios, que se renombran o borran al terminar cada etapa. |
| `descargas/` | Entregables a mano (los botones «Descargar») y los automáticos con `RV_ENTREGABLES=1`. |

Insumos de datos grandes, con rutas **ancladas al módulo** (no dependen del
directorio de trabajo):

| Archivo | Quién lo usa | Función |
|---|---|---|
| `grillas/slabP###.tmp`, `topoP###.tmp` | `asigna_perfiles.py`, `plotear.py` | Perfiles de subducción (pares slab/topo). |
| `base_2020_2026.dat` | `sismicidad.py`, `plotear.py` | Catálogo histórico de referencia. |
| `localidades.csv` | `plotear.py` | Puntos para rotular mapas. |
| `relieve_chile.tif` | `plotear.py` | Relieve regional. |
| `NE2_LR_LC_SR_W_DR.tif` | `plotear.py` | Relieve global de respaldo. |
| `plantillas/select.inp` | `traer_catalogos.py` | Plantilla del `select` de Seisan. |

---

## 4. Flujo por etapa

1. **`proc_query_harz_2.py`** — lee el CSV público, escribe un `.dat` con
   cabecera y `datos/new_2_<base>.csv` ordenado por hora.
2. **`revisaselect.py`** — parsea `select.out` y deja los eventos revisables en
   `trabajo/newcollect.txt`; los que no cumplen (sin agencia, sin magnitud, sin
   coordenadas o sin RMS) van a `informes/excluidos.txt`.
3. **`revisacollect.py`** — normaliza y escribe `datos/salida_collect.csv` (y,
   con entregables, un CSV por analista). Unifica nombres de analista con
   distancia de Levenshtein (`DISTANCIA_MAXIMA = 1`).
4. **`compara.py`** — compara el público contra la solución de la fuente. Un
   evento es el mismo si Δdía 0 y Δsegundos ≤ tolerancia, con Δlat/Δlon ≤
   tolerancia (amplio y estricto). Escribe no publicados y
   **`datos/atribucion_<fuente>.csv`** (una fila por cruce, con `dt_seg`,
   `dlat`, `dlon` y los valores de la fuente/publicado).
5. **Atribución a SeisComp** — `seiscomp_a_parametros.py` convierte la
   exportación cruda y `compara.py` la usa como fuente.
6. **`cruza_nopub.py`** — para cada no publicado busca en
   `datos/atribucion_<otra>.csv` soluciones locales de la otra fuente. La
   confirmación exige **6 s / 0,5° y una única candidata**; si hay varias, el
   caso queda como **ambiguo**. Una ventana de revisión de **120 s / 2°**
   identifica candidatos cercanos sin marcarlos como publicados. Agrega al CSV
   `Publicado_en`, `Estado`, `Dt_otra_seg`, `Dist_otra_km` y `Analista_otra`.
   No elimina ni reordena eventos. No usa una atribución más vieja que su
   catálogo local. Si la otra fuente no tiene datos, la atribución está vieja o
   la comparación no se ejecutó, el estado es `No evaluable` con el motivo.
   Si `compara.py` no encontró catálogo publicado, no se generan listados de no
   publicados.
7. **`revisaexcluidos.py`** — normaliza excluidos a `datos/excluidos.csv`.
8. **`repetidosexclu.py`** y **`repetidos.py`** — detectan repeticiones.
9. **`generajson.py`** — por fuente: asigna perfil (vía `asigna_perfiles.py`),
   clasifica sospechosos (vía `sismicidad.es_sospechoso`) y escribe
   `datos/eventos_<vista>.json` y `datos/conteo_perfiles_<vista>.json`. En los
   no publicados copia además las cinco columnas de cruce al JSON. En los no
   actualizados, `procesar_pares` llama `cruce_noact.cargar_otra` y
   `cruce_noact.anotar`, y copia `publicacion_probable`, `revision`,
   `revision_motivo` y `revision_orden` al JSON del panel.
10. **`plotear.py` / `revisa_seiscomp.py`** — dibujan los paneles con la GUI.

---

## 5. Interfaces de línea de comandos

Ningún módulo usa `argparse`: los argumentos son posicionales y las opciones se
escriben como `--clave=valor`.

| Comando | Efecto |
|---|---|
| `python3 app.py <entrada.csv> <salida.dat> [estado.json]` | Abre la GUI principal. |
| `python3 generajson.py <csv> <fuente> [--umbral=KM] [--k=K] [--umbral-perp=KM] [--margen-borde=KM] [--salida=NOMBRE]` | Genera JSON, CSV de sospechosos y conteo (`fuente`: seisan, seiscomp, eventquery, nopub). |
| `python3 plotear.py <eventos_<fuente>.json> <fuente>` | Abre los mapas de una fuente. |
| `python3 asigna_perfiles.py --listar` | Lista los perfiles detectados en `grillas/`. |
| `python3 asigna_perfiles.py <lon> <lat> <prof>` | Asigna un perfil a una coordenada. |
| `python3 sismicidad.py [-h] [<eventos_<fuente>.json>]` | Indica si cada evento es sospechoso. |
| `python3 compara.py <csv_publico> <csv_local> [prefijo]` | Compara y escribe reportes. |
| `python3 cruza_nopub.py` | Agrega a los dos CSV de no publicados las columnas de cruce con la otra fuente. |
| `python3 repetidos.py <csv_publico> <csv_seisan> [csv_seiscomp]` | Detecta repetidos. |
| `python3 repetidosexclu.py <csv_excluidos> <csv_select>` | Cruza excluidos con select. |
| `python3 exporta_ventana_seiscomp.py <catalogo.csv>` | Exporta la ventana de SeisComp. |
| `python3 seiscomp_a_parametros.py <exportacion.csv> [salida.csv]` | Convierte la exportación. |
| `python3 traequery.py` | Bajada interactiva de eventquery (legado). |
| `./seiscomp.sh <catalogo.csv> [--reexportar] [--solo-revision]` | Extracción + revisión. |
| `./supervisor.sh [<entrada.csv> <salida.dat>]` | Lanzador con `.venv`. |

---

## 6. Conexión remota y base de datos

### Servidor de catálogos (SSH/SCP) — `traer_catalogos.py`

- Servidor: `sysopr@10.54.217.9` (`traer_catalogos.py:43-44`).
- Directorio remoto: `tmp`.
- El catálogo público se baja con el binario remoto **`eventquery2`** (la versión
  vieja, `eventquery`, traía soluciones duplicadas).
- La contraseña se pasa con `SSH_ASKPASS` + `SSH_ASKPASS_REQUIRE=force`; no va por
  la línea de comandos.

### Base de SeisComp (PostgreSQL) — `exporta_ventana_seiscomp.py`

- `connect_timeout=10` y `statement_timeout` de **60 segundos** para evitar que
  consultas largas bloqueen el hilo principal (configurados al abrir la conexión).
- Esquema detallado: `esquema_seiscomp.md`; script importable en MySQL Workbench:
  `esquema_seiscomp_mysql.sql`.

---

## 7. Parámetros y dónde ajustarlos

Todos los valores están como constantes de módulo (mayúsculas), fáciles de
ubicar y cambiar. Ubicación `archivo:línea` (puede variar con ediciones).

### Comparación y repetidos

| Constante | Archivo:línea | Valor | Efecto |
|---|---|---|---|
| `MAX_SEG_AMPLIO` | `compara.py:33`, `repetidos.py:53` | `6` | Tolerancia de tiempo (s) del filtro **amplio**. |
| `MAX_LAT_LON_AMPLIO` | `compara.py:34`, `repetidos.py:54` | `2.0` | Tolerancia de coordenadas (°) del amplio. |
| `MAX_SEG_ESTRICTO` | `compara.py:35`, `repetidos.py:55` | `3` | Tolerancia de tiempo (s) del **estricto**. |
| `MAX_LAT_LON_ESTRICTO` | `compara.py:36`, `repetidos.py:56` | `1.0` | Tolerancia de coordenadas (°) del estricto. |
| `VENTANA_SEG` | `cruza_nopub.py` | `6.0` | Tolerancia de tiempo (s) para confirmar una publicación en la otra fuente. |
| `TOL_GRADOS` | `cruza_nopub.py` | `0.5` | Tolerancia de lat/lon (°) para confirmar esa publicación. |
| `VENTANA_REVISION_SEG` | `cruza_nopub.py` | `120.0` | Ventana de tiempo (s) para avisar candidatos que requieren revisión manual. |
| `TOL_REVISION_GRADOS` | `cruza_nopub.py` | `2.0` | Tolerancia de lat/lon (°) de esa revisión; no confirma publicación. |
| Magnitud mínima de CSV | `compara.py` (~217) | `2.5` | Umbral para escribir los CSV de no publicados. |

### Precisión de comparación (`comparacion.py`)

| Constante | Línea | Valor | Efecto |
|---|---|---|---|
| `DECIMALES_COORDENADA` | `26` | `3` | Decimales de normalización de lat/lon. |
| `DECIMALES_PROFUNDIDAD` | `27` | `1` | Decimales de profundidad (se compara ignorando el signo). |
| `DECIMALES_MAGNITUD` | `28` | `1` | Decimales de magnitud. |
| `TOLERANCIA_COORDENADA` | `36` | `0.005` | Tolerancia (°) al comparar lat/lon: cubre el redondeo del publicado a 2 decimales. |
| `RADIO_TIERRA_KM` | `39` | `6371.0088` | Radio terrestre para `distancia_km`. |

La función `distancia_km(lat1, lon1, lat2, lon2)` (`comparacion.py:153`) calcula
la distancia haversine que se muestra en la columna **Dist (km)** de «No
actualizados»; `compara.py` la escribe en `atribucion_<fuente>.csv` y
`revisa_seiscomp.py` la recalcula si el CSV es viejo.

### Asignación de perfiles (`asigna_perfiles.py`)

| Constante | Línea | Valor | Efecto |
|---|---|---|---|
| `UMBRAL_DIST_KM` | `89` | `110.0` | Distancia máxima (km) para asignar un perfil. |
| `UMBRAL_PERP_KM` | `96` | `None` | Tope lateral explícito (opcional). |
| `MARGEN_BORDE_KM` | `104` | `0.0` | Margen respecto del borde de la sección. |
| `K_PESO_PROFUNDIDAD` | `116` | `1.0` | Peso del residuo de profundidad en la distancia de asociación. |
| `ANCHO_BIN_KM` | `124` | `1.0` | Ancho de bin (km) al muestrear las grillas. |
| `GRADO_KM_LAT` / `GRADO_KM_LON` | `119-120` | `111.0` | Conversión grados→km. |

### Sospechosos (`sismicidad.py`)

`CRITERIOS_SOSPECHOSO` (`sismicidad.py:76-96`) define la regla efectiva:
`"regla": "ambos_grupos"` (sospechoso si se cumple ≥1 prueba del grupo `slab`
**y** ≥1 del grupo `historica`). Pruebas: `perp_max_km` (inactiva, 55.0),
`residuo_max_km` (**activa**, 30.0), `densidad_local` (inactiva), `knn`
(**activa**, k=5, 15 km), `ventana_aislamiento` (inactiva),
`desvio_mediana_prof` (inactiva). Además, **todo evento sin perfil es
sospechoso**.

### Exportación de SeisComp (`exporta_ventana_seiscomp.py`)

| Constante | Línea | Valor | Efecto |
|---|---|---|---|
| `RADIO_ESTACIONES_KM` | `192` | `400.0` | Radio por defecto de estaciones sin arribos. |
| `ACTIVIDAD_HORAS` | `202` | `2.0` | Semiancho de la ventana de actividad (±2 h). |
| `TAMANO_LOTE` | `175` | `5000` | Filas por lote de lectura. |
| `AVISO_DE_LOTES` | `179` | `200000` | Aviso de exportaciones grandes. |
| `NO_PICADAS_BYTES_FILA` | `1138` | `154` | Bytes/fila para estimar tamaño. |
| `AVISO_NO_PICADAS_MB` | `1142` | `200.0` | Aviso (MB) antes de exportar sin arribos. |

### Interfaz de revisión (`revisa_seiscomp.py`)

| Constante | Línea | Valor | Efecto |
|---|---|---|---|
| `MAX_FILAS` | `64` | `20000` | Máximo de filas mostradas en el panel. |
| `DECIMALES_COORD` | `93` | `3` | Decimales de coordenadas en pantalla. |
| `UMBRAL_CERCANO_KM` | `187` | `50.0` | Umbral de resaltado «cerca» (configurable en la ventana). |
| `ANCHO_ESTACIONES` | `194` | `1400` | Ancho por defecto de la ventana Estaciones. |
| `UMBRAL_AVISO_AMPLIADO` | `238` | `2000` | Filas que disparan el aviso al ampliar. |
| `COLUMNAS_*`, `DETALLE_GRUPOS` | — | — | Columnas y grupos del detalle. |
| `AYUDA_*` | — | — | Textos de ayuda de la interfaz. |

En la ventana **Estaciones del evento** hay dos controles de distancia distintos:
**«Radio a mostrar (km)»** recorta la lista exportada (reconstruye la tabla) y
**«Resaltar cerca ≤ (km)»** solo cambia el color. El retinte del umbral no
reconstruye: lo hace `_retintar_no_picadas(arbol, umbral_cercano)`, que reusa las
filas guardadas en el árbol (`arbol._filas_no_picadas`) para no perder scroll ni
selección; se dispara con retardo (300 ms) al editar el campo. El check
**«Solo cercanas»** agrega el recorte por el umbral cerca. La tabla de sin
arribos tiene **tooltip por fila** (`_ayuda_filas_arbol` + `_texto_ayuda_fila`):
al pasar el mouse muestra la evidencia de esa estación (verificado con ondas,
indicio por actividad, sin evidencia o sin consultar) y, si está verificada, la
cobertura.

En las tres pestañas de **Catálogos** (`abrir_panel` para SeisComp y
`abrir_catalogo` para Seisan/eventquery) la lista comparte la ventana con una
**miniatura del perfil** del evento seleccionado. La miniatura la arma
`_panel_miniatura(parent, ttk, fuente)`, que crea una `Figure` embebida con
`FigureCanvasTkAgg` y devuelve `dibujar(evento, mostrar_hist=False)`; la lista y
la miniatura van en un `ttk.PanedWindow` horizontal (lista con peso 3, miniatura
con peso 1). El binding `<<TreeviewSelect>>` dispara `_actualizar_mini`, que
arma el evento con el formato de `plotear` y llama `plotear.dibujar_mini_evento`.
La casilla **«Sismicidad histórica»** (`var_hist`) se pasa como `mostrar_hist` y
solo afecta a la miniatura; es independiente por pestaña. El detalle difiere
según la fuente: en SeisComp, doble clic o Enter abre `_ventana_detalle` (con el
nuevo botón «Planta y perfil», ver `al_planta_perfil`); en Seisan y eventquery,
doble clic o Enter llama directo a `plotear.abrir_evento`.

Los **filtros se aplican a demanda** —botón «Aplicar» o Enter en la casilla—,
no en cada tecla. Las cuatro listas con filtro de texto (`abrir_panel`,
`abrir_catalogo`, `abrir_no_actualizados` y `app._construir_tabla_no_publicados`)
comparten el criterio y el **mismo constructor**: `revisa_seiscomp.abrir_tabla`,
que arma el árbol, los encabezados que ordenan, los filtros, la descarga y la
miniatura opcional, y devuelve los ganchos (`arbol`, `fila_actual`, `marco_mini`,
…). Cada lista aporta solo sus columnas, sus valores y su ploteo; el orden usa
`_ordenar_eventos` con un mapa de columnas (`_claves_numericas`). El mapa
funcional de la aplicación (qué hace y dónde está cada cosa) está en
`docs/proyecto/img/09_mapa_funcional.png` y en el manual de usuario.

En **No publicados**, `_construir_tabla_no_publicados` agrega sobre la tabla una
leyenda de estados y el botón **«Criterios de clasificación»**, que muestra
`AYUDA_ESTADOS_NO_PUBLICADOS` en un diálogo. Los anchos de columna se calculan
con `TkHeadingFont`/`TkDefaultFont` a partir del encabezado y los datos, con
mínimo y máximo, para no dejar columnas sobredimensionadas. La misma tabla agrega
**«Abrir en sismologia.cl»**: con una fila seleccionada, `_url_dia_sismologia`
convierte `Fecha_Hora` al catálogo diario
(`.../catalogo/AAAA/MM/AAAAMMDD.html`) y `webbrowser.open` lo abre en el
navegador. Si la fecha no se puede interpretar, el botón queda deshabilitado.
El listado reserva además un panel derecho con
`plotear.dibujar_mini_mapa_evento`, que dibuja solo el evento seleccionado en
una vista nacional con `MARGEN_MINI_MAPA_NACIONAL = 3.0` grados de margen en
latitud y longitud. Se actualiza con `<<TreeviewSelect>>`; sin selección muestra
una ayuda y no acumula eventos de otras filas. `conectar_zoom_mapa` agrega zoom
con rueda, arrastre para mover, centrado sobre el evento y restablecimiento,
limitado a la extensión nacional inicial. El `PanedWindow` fija el ancho
solicitado de la lista y del mapa para que las columnas no desplacen el panel
derecho.

En **No actualizados**, `revisa_seiscomp._no_actualizados` llama
`cruce_noact.cargar_otra(cwd, fuente)` y `cruce_noact.anotar(...)` antes de
construir la tabla. El módulo agrupa los eventos publicados por fuente, elige la
mejor candidata local de cada una y decide `Esta fuente`, `Compartida`,
`Otra fuente`, `Duplicado público` o `No evaluable`, con la prioridad
`Alta`/`Media`/`Baja`/`—`. No escribe esas columnas en los CSV de `compara.py`.
Para que el listado no se demore con catálogos grandes, `anotar` parsea cada
clave una sola vez y busca las candidatas por índice; `_clusters_publicados`
ordena por instante y recorre solo la ventana de 3 s. `_no_actualizados` además
cachea el resultado por firma (`mtime`, `ctime` y tamaño) de la atribución
propia, la de la otra fuente y el catálogo de esa otra fuente; la caché se
invalida sola cuando el análisis regenera esos archivos. La ventana de consulta
se crea una vez y se oculta al cerrarla; cada pestaña reutiliza su frame y solo
se rearma cuando cambia su firma.
El listado muestra la leyenda y el botón **«Criterios de clasificación»** con
`AYUDA_REVISION_NO_ACTUALIZADOS`; `claves_orden["revision"]` ordena por
`revision_orden`. En el panel, `plotear.abrir_panel` detecta la presencia de
`revision` (`con_prioridad`) y agrega la columna **Alta**, el conteo
`n_altas`, el filtro **«Solo alta prioridad»** y el mismo botón de ayuda. Ese
filtro se combina con **«Solo sospechosos»** y **«Inicio»** apaga ambos;
`_eventos_descarga` aplica la intersección y `COLUMNAS_DESCARGA_NOACT` agrega
las dos columnas a la descarga.

### Descargas (`descargas.py`)

Todas las descargas a `descargas/` pasan por `descargas.py`.
`preguntar_descarga(padre, etiqueta, cwd=None, con_formato=True,
sufijos=("",), titulo="Descarga")` es el diálogo único: pregunta el **nombre
base** (precargado con `etiqueta_marca`) y, si `con_formato`, CSV/TXT; la
extensión la fija el formato, no se escribe a mano. Devuelve
`(formato, nombre, sobrescribir)` o `None`. Si el destino ya existe pregunta
antes de pisarlo (`_confirmar_sobrescribir`) y no cierra hasta que el nombre no
choque o se cancele. `preguntar_formato` sobrevive como envoltorio que devuelve
solo el formato, por compatibilidad con los caminos que no necesitan el nombre.

`exportar_tabla`/`exportar_lineas` aceptan `nombre` y `sobrescribir`. Sin
`nombre` arman `etiqueta_marca`; si el destino existe y no se pidió
sobrescribir, `nombre_descarga` agrega un correlativo para no pisar. La carpeta
es siempre `descargas/` (ver §3): no se elige. Para una descarga de varios
archivos se pasa `sufijos` y cada uno usa `nombre + sufijo` (Comparar agencias →
Comparación usa `""`, `_larga` y `_cobertura`).

### Repetidos (`repetidos.py`, `repetidosexclu.py`)

Los informes `informes/rep_*.txt` y `informes/rep_seisan_exclu.txt` se escriben
**separados por tabuladores** con una cabecera de una palabra por columna (antes
iban por espacios, que no se podían partir en columnas: «fecha hora» partía en
dos y una referencia o un analista con espacios corría la fila). `repetidos.py`
expone las columnas de cada informe (`COLUMNAS_PUBLICA`, `COLUMNAS_SEISAN`,
`COLUMNAS_EXCLU`), que `app._ver_repetidos` usa para mostrar y descargar el
informe elegido como tabla ordenable (vía `revisa_seiscomp.abrir_tabla`, con
«Descargar» = lo filtrado y «Descargar todo» = el completo). Cada tabla recibe
el botón **«Abrir en sismologia.cl»** mediante `app._agregar_boton_web`, que
usa `_url_dia_sismologia` con la columna `fecha_hora`; el mismo método se usa
en No publicados.

`revisa_seiscomp.SeleccionTabla` agrega casillas usando la columna `#0` del
`Treeview`, sin agregar valores a `columns` ni a las descargas. Las marcas se
guardan por `id(fila)`, así sobreviven al filtro, al orden y al repintado;
`abrir_tabla(..., seleccionable=True)` expone «Descargar seleccionados». La
misma clase se usa en Análisis rápido y en Comparación de agencias.

Para los repetidos **publicados** (eventquery), que no traen responsable, la app
agrega dos columnas «Analista probable (Seisan)» y «Analista probable
(SeisComp)»: `app._analistas_probables_repetidos` cruza cada fila con
`datos/atribucion_seisan.csv` y `datos/atribucion_seiscomp.csv` reusando
`generajson._analistas_para_evento`, la misma lógica del catálogo. Si falta la
atribución, las columnas quedan vacías.

### Disponibilidad de formas de onda (`disponibilidad.py`)

`disponibilidad.consultar(streams, desde, hasta, al_progreso=None)` responde si
hay datos para cada `NET.STA.LOC.CHA` en una ventana, usando `scart` en modo
consulta (no escribe nada):

1. **SDS local**: `scart -d --print-streams -n … -t … <raíz>` (`NEWPT_SDS_ROOT`,
   por defecto `/mnt/sds/archive`).
2. **Tiempo real**: para los streams que no están en el SDS,
   `scart -I <recordstream> --test --print-streams …`. La URL sale de
   `NEWPT_RECORDSTREAM` o de la línea `recordstream` del `global.cfg`.

`al_progreso` es un callback opcional que recibe mensajes de fase
(`Consultando el archivo SDS…`, `Buscando en el tiempo real…`, `Listo.`). La
ventana de estaciones lo usa para una barra indeterminada, el texto de fase con
segundos transcurridos y el bloqueo temporal de los controles que reconstruyen
la tabla; el botón y la descarga se deshabilitan mientras dura la consulta. El
callback corre en el hilo de trabajo, así que la interfaz solo encola los
mensajes.

`_no_picadas.csv` trae `streams_vigentes_ids` con todos los streams vigentes (la
referencia primero), así que la consulta prueba la referencia y, si no hay datos,
los demás. Las columnas `waveform_status` (`CON_DATOS`/`SIN_DATOS`/
`NO_CONSULTADO`), `availability_source` (`SDS`/`RECORDSTREAM`) y
`cobertura_desde/hasta` se llenan con `exporta_ventana_seiscomp.py
--formas-onda`, o on-demand desde «Consultar formas de onda» en la ventana de
estaciones. Si no hay acceso a ninguna fuente, no se afirma nada y queda la
actividad ±2 h como indicador indirecto.

La columna derivada `evidencia` resume la conclusión con una jerarquía explícita
(`disponibilidad.estado_evidencia`): **VERIFICADO** (hay ondas) > **INDICIO**
(actividad ±2 h) > **SIN_EVIDENCIA** (se miraron las ondas y no hay, ni
actividad) > **NO_CONSULTADO** (no se miraron y no hay actividad). La interfaz
usa esa jerarquía para colorear: verde = verificado, ámbar = indicio, negrita =
sin evidencia. El Análisis rápido muestra tres contadores (verificadas,
indicios, sin evidencia) y la descarga larga clasifica cada estación como
`verificado`, `indicio`, `sin evidencia` o `sin consultar`.

### Ajuste de ventanas (`ajuste.py`) y arranque (`app.py`)

`app.App._ajustar_popup(top, minimo)` aplica el criterio de `ajuste.ajustar` a
las ventanas secundarias: combina el tamaño mínimo con el actual para que solo
crezcan y las acota a la pantalla. Se llama al construir cada pestaña de
**No publicados** y **No actualizados**, y al elegir un informe en **Repetidos**.
Esas ventanas fijan además un `minsize` moderado; si el contenido no entra, las
tablas mantienen su barra horizontal.

| Constante | Archivo:línea | Valor | Efecto |
|---|---|---|---|
| `TOPE_MAXIMO` | `ajuste.py:39` | `(1920, 1080)` | Tope de crecimiento de ventanas. |
| `MARGEN` | `ajuste.py:43` | `40` | Margen contra el borde de pantalla. |
| `TAMANIO_INICIAL` | `app.py:98` | `(980, 820)` | Tamaño inicial de la ventana principal. |
| `GRUPOS_PESTANAS` | `app.py:275` | — | Agrupación de pestañas. |
| `REP_FILES` | `app.py:83` | — | Archivos de repetidos que muestra «Ver repetidos». |

### Dibujo (`plotear.py`)

| Constante | Línea | Valor | Efecto |
|---|---|---|---|
| `FIG_SIZE` | `57` | `(15, 7)` | Tamaño de la figura por perfil. |
| `FIG_SIZE_NACIONAL` | `63` | `(7.0, 13.0)` | Figura vertical del Territorio Nacional. |
| `DPI` | `72` | `100` | Resolución. |
| `PROF_MAX_KM` | `78` | `250` | Profundidad máxima del eje vertical. |
| `ALT_MAR_KM` | `82` | `15` | Km sobre el nivel del mar mostrados. |
| `MARGEN_PLANTA_GRADOS` | `86` | `0.6` | Margen en grados del recorte de relieve. |
| `NIVEL_GEO` | `97` | `"50m"` | Escala de costas/fronteras. |
| `MAX_EVENTOS_ETIQUETA` | `143` | `60` | Máximo de eventos con etiqueta de `id`. |
| `HIST_*`, `COLOR_*` | — | — | Estilo de sismicidad histórica y colores. |
| `TERRITORIO_*`, `RELIEVE_LOCAL` | — | — | Límites de territorios y recorte local. |

`plotear.abrir_eventos(eventos, fuente, perfiles=None)` dibuja **planta + perfil
de uno o más eventos sueltos**; `abrir_evento(evento, …)` es el caso de uno
(delega). Es lo que dispara el **doble clic** (o Enter) en los listados de No
publicados (`app.py`), No actualizados (`revisa_seiscomp.py`) y en las pestañas
de Seisan y eventquery del catálogo. `dibujar_mini_evento(fig, evento, fuente,
mostrar_hist=False)` es la variante embebida para la **miniatura** de las
pestañas de catálogo: asigna perfil y sospechoso con `_preparar_un_evento` y
dibuja con `_mini_perfil` (el mismo del panel de análisis, con
`mostrar_hist`); sobre una `Figure` propia, no abre ventana. Con un evento:
comportamiento de siempre. Con dos que traen `rol` `'local'` y `'publicado'`
(comparación de un no actualizado): ubica **ambos** en el perfil del evento de
la fuente (con `asigna_perfiles.distancia_al_perfil`/`profundidad_slab_en`), los
pinta distinto (`_estilo_marcadores`: el Evento Seisan/SeisComp amarillo
relleno, el publicado como **anillo** —centro blanco, borde `COLOR_PUBLICADO`—),
dibuja la **línea
conectora** y el **Δ ubicación/prof/mag** (`_dibujar_diferencia` y
`_texto_diferencia`, en la esquina inferior derecha; el Δ de ubicación incluye la
**dirección cardinal** —`_direccion_cardinal`, p. ej. `Δ 10.3 km SE`— y, cuando el
Δ parte de nuestra solución publicada, la **referencia entre paréntesis**
—`_etiqueta_referencia` según el `rol`, p. ej. `Δ 10.3 km SE (ref. eventquery)`—;
el Δ mag solo si difiere, con el tipo cuando cambia), y titula
con la fuente (`titulo`). El tipo de magnitud viaja en
`datos/atribucion_<fuente>.csv` (`tipo_mag_local`/`tipo_mag_eventquery`, los
escribe `compara.py`). Si el evento de la fuente
no tiene `perfil` (o falta profundidad), cae a `plotear_planta`. Los eventos de
esos listados **no llevan `id`**, así que no se etiquetan sobre el mapa ni
muestran la línea «id:» en la viñeta (`_marcadores_planta` y
`_texto_parametros_evento` omiten el id cuando falta).

En una **superposición** (varias fuentes en la misma ubicación) la viñeta la arma
`_texto_superposicion`: además del encabezado `Soluciones superpuestas (N): …` y
el Δ de cada fuente, agrega una línea con el **`id` y la fecha/hora de nuestro
evento publicado** (la referencia) —`id: 40 · 2026-10-02 12:47:27`— para no
depender de buscar el id en el catálogo. Si no hay referencia, muestra solo la
fecha/hora (nunca el id de una agencia).

---

## 8. Entradas y formatos

- **Exportación de SeisComp** (`datos/seiscomp_<ini>_<fin>.csv`): 16 columnas
  (`id_evento, id_origen, ot_utc, magnitud, tipo_magnitud, fases, rms, azgap,
  latitud, longitud, profundidad_km, agencia, operador, region, estatus,
  base_datos`). Ver `docs/esquema_seiscomp.md`.
- **Fases** (`..._fases.csv`): 33 columnas, con `modo_pick`, `pick_autor`,
  `pick_agencia`, `pick_metodo`, `usada`, etc.
- **Sin arribos** (`..._no_picadas.csv`): 21 columnas, con `distancia_km`,
  `streams_vigentes`, `streams_vigentes_ids` (todos los vigentes, la referencia
  primero), `actividad_ventana`, `evidencia` y las de disponibilidad
  (`waveform_status`, `availability_source`, `cobertura_desde/hasta`).
- **`datos/atribucion_<fuente>.csv`**: una fila por cruce, con `fecha_local`,
  `lat_local`, `lon_local`, `prof_local`, `mag_local`, `*_eventquery`, `analista`,
  `dt_seg`.
- **`datos/no_pub_desde_2_5_*estricto.csv`**: `Fecha_Hora, Latitud, Longitud,
  Prof., Mag., Tipo_mag., Analista, Publicado_en, Estado, Dt_otra_seg,
  Dist_otra_km, Analista_otra`. Las cinco últimas las agrega `cruza_nopub.py`.
  `Publicado_en` solo se llena con una confirmación única; `Estado` distingue
  `Publicado en ...`, `Ambiguo: N candidatos en ...`, `Candidato en ...`,
  `Sin coincidencia` y `No evaluable: ...`. El diagnóstico se llena con el
  candidato más cercano (también en ambiguos y candidatos).
- **`datos/eventos_<vista>.json`**: lista de eventos con `id`, `fecha hora`,
  `latitud`, `longitud`, `prof`, `magnitud`, `tipo`, `perfil`, `along_km`,
  `perp_km`, `residuo_km`, `dist_asoc`, `sospechoso`, `percibido`. En las vistas
  `*_nopub` incluye además `publicado_en`, `estado`, `dt_otra_seg`,
  `dist_otra_km` y `analista_otra`.
- **CSV vs TXT**: CSV usa `utf-8-sig` (BOM para Excel); TXT va sin BOM y separado
  por tabulaciones.

### Catálogos sin datos

- `rutas.csv_tiene_filas(ruta)`: distingue un CSV con datos de uno que solo trae
  encabezado. Lo usan la app, la solicitud y el cruce de no publicados.
- `traer_catalogos.select_tiene_eventos(ruta)`: detecta si el `select.out` de
  Seisan tiene al menos una línea de evento.
- `exporta_ventana_seiscomp._eventos_de_la_marca(ruta)`: lee `eventos N` de la
  marca `.completo`; se usa para avisar cuando SeisComp no trajo eventos.
- `app.ESTADOS_CATALOGO["sin_datos"]`: chip `⚠ sin datos`. Se aplica a Seisan,
  eventquery y SeisComp cuando su entrada o derivado no tiene filas.
- Si el catálogo publicado (`new_2_*.csv`) está vacío, `compara.py` no genera
  listados de no publicados, borra los derivados viejos y deja los informes
  `no_act_*` con cabecera.

---

## 9. Nombres de las columnas

Definiciones exactas de las columnas y campos que aparecen en las tablas de la
interfaz y en los archivos de descarga. Los campos del JSON de eventos están en
la [sección 8](#8-entradas-y-formatos).

Las distancias al perfil (`along_km`, `perp_km`, `residuo_km` y `dist_asoc`) se
guardan con 3 decimales y se **muestran con un decimal** en la viñeta del evento,
en la descarga y en el rango «Along (km)» de la tabla de perfiles del panel.

| Columna | Definición | Origen |
|---|---|---|
| **Along (km)** (`along_km`) | Proyección del evento sobre el eje del perfil, en km desde el inicio de la sección (recortada a los extremos). | `asigna_perfiles.distancia_al_perfil` |
| **Perp (km)** (`perp_km`) | Distancia lateral (perpendicular) del evento al eje del perfil. | `asigna_perfiles.distancia_al_perfil` |
| **Residuo (km)** (`residuo_km`) | `abs(prof_evento - profundidad_slab(along))`; vacío si el *slab* no cubre esa posición. | `asigna_perfiles.profundidad_slab_en` |
| **Dist. asoc. (km)** (`dist_asoc`) | Distancia de asociación para elegir el perfil: combina `perp` y `residuo` con `K_PESO_PROFUNDIDAD`, con tope `UMBRAL_DIST_KM` (y `UMBRAL_PERP_KM` opcional). | `asigna_perfiles.asignar_perfil_evento` |
| **Motivo** (`motivo`) | Causa de «sin perfil»: `fuera_cobertura_norte`, `fuera_cobertura_sur`, `fuera_cobertura_extremo`, `fuera_cobertura`, `fuera_umbral` o `sin_perfiles`. | `asigna_perfiles` |
| **Frontera** (`Frontera_km`) | País y distancia a la frontera terrestre chilena más cercana (`Perú — 34.9 km`); `—` dentro de Chile, en mar chileno (aprox. 200 mn de la costa) o sin coordenadas. Se anota una sola vez por fila y se ordena por el km numérico. | `fronteras` |
| **Δmáx (km)** | Distancia máxima entre las soluciones agrupadas de un mismo evento (comparación de agencias). | `agencias._max_distancia` |
| **Δt (s)** | Diferencia de tiempo, en segundos, respecto de la solución de referencia. | `agencias` |
| **Dist (km)** | Distancia horizontal, en km, entre dos soluciones. | `agencias` |
| **Δprof (km)** / **Δmag** | Diferencia de profundidad (km) / de magnitud respecto de la referencia. | `agencias` |
| **Fuera de rango** | La solución asociada supera Δt > 3 s o \|Δmag\| > 0.2. La asociación exige ≤ 6 s y ≤ 75 km de distancia horizontal. | `agencias._flags` / `agencias._mismo_evento` |
| **Referencia** / **Asociado** / **Fuente** | Evento publicado de referencia del cruce / agencia asociada (formato largo) / origen de la fila. | `agencias` |
| **Agencias** / **Rezago** | Fuentes que reportaron el evento (unidas con `≡` si caen en la misma ubicación) / cuánto antes del fin solicitado terminó el catálogo de la agencia. | `agencias` / `app._cobertura_agencias` |
| **Loc** / **Cha** | Localización (2 dígitos) y canal del stream (código SEED). | `revisa_seiscomp` |
| **Resid (s)** / **Residuo** | Residual del arribo (observado − teórico), en segundos. | `revisa_seiscomp` |
| **Dist (°)** / **Azimut** | Distancia epicentral (grados) / azimut de la estación respecto del epicentro. | `revisa_seiscomp` |
| **Usada** / **Modo** / **Peso** | Si el arribo entró a la solución / manual o automático / peso en la solución. | `revisa_seiscomp` |
| **Colores de llegadas** | Rojo y negrita = pick manual usado; ámbar = manual no usado; sin resaltado = automático. | `revisa_seiscomp._colores_pick` y `_construir_arbol_fases` |
| **SNR** / **QC** | Relación señal-ruido / marca de control de calidad del *pick*. | `revisa_seiscomp` |
| **Elev (m)** | Elevación de la estación, en metros. | `revisa_seiscomp` |
| **Streams vig.** / **Loc ref.** / **Canal ref.** | Streams vigentes / localización y canal del stream de referencia. | `revisa_seiscomp` |
| **Formas de onda** | Consulta a SDS y, si no hay datos, al recordstream de tiempo real (prueba el stream de referencia y luego los demás vigentes). | `disponibilidad` |
| **Evidencia** | Jerarquía Verificado (ondas) > Indicio (actividad) > Sin evidencia > Sin consultar. | `disponibilidad` |
| **Indicio ±2 h** | Otros eventos picados por esa estación entre 2 h antes y 2 h después del origen. | `exporta_ventana_seiscomp` |
| **Verificadas** / **Indicios** / **Sin evid.** | Estaciones cercanas con ondas / solo con actividad ±2 h / sin evidencia. | `revisa_seiscomp` |
| **Dist. mín. (km)** / **Clasificación** | Distancia a la estación sin arribos más cercana / categoría del evento en el análisis. | `revisa_seiscomp` |
| **Estatus** / **Base** / **Fases** | Estado de revisión / base de datos de origen / cantidad de fases. | `exporta_ventana_seiscomp` |
| **Percib.** / **Referencia** / **Analista probable** | Percibido por la población / referencia del catálogo público / analista probable del evento. | `revisa_seiscomp` |
| **Publicación probable** / **Revisión** | Fuente que parece haber publicado (Esta fuente, Compartida, Otra fuente, Duplicado público, No evaluable) / prioridad de revisión (Alta, Media, Baja, —). | `cruce_noact` |

Las constantes de asociación (`UMBRAL_DIST_KM`, `UMBRAL_PERP_KM`,
`K_PESO_PROFUNDIDAD`) y las de sospechosos están en la
[sección 7](#7-parámetros-y-dónde-ajustarlos).

---

## 10. Cómo extender el sistema

- **Agregar una columna a una tabla**: añadir la tupla `(clave, título, ancho)`
  en la constante `COLUMNAS_*` correspondiente (`revisa_seiscomp.py`) y, si el
  valor necesita formato, actualizar la función `_valores_*` asociada.
- **Cambiar textos de ayuda**: constantes `AYUDA_*` en `revisa_seiscomp.py`.
- **Agregar una fuente/pestaña**: `VISTAS` y `GRUPOS_PESTANAS` en `app.py`.
- **Cambiar un umbral del flujo**: modificar la constante en su módulo (ver la
  tabla de la [sección 7](#7-parámetros-y-dónde-ajustarlos)).
- **Cambiar el esquema de SeisComp consultado**: las consultas están en
  `exporta_ventana_seiscomp.py` (`CONSULTA_*_SQL`), y la documentación en
  `docs/esquema_seiscomp.md`.

---

## 11. Verificación y pruebas

- **Diagnóstico de entorno**: `.venv/bin/python verifica_entorno.py` revisa el
  venv, los paquetes de `requirements.txt`, tkinter y la conexión a la base.
- **Suites automatizadas**:
  ```bash
  ./tests/correr.sh          # tests unitarios sin GUI ni base
  ./tests/correr.sh gui      # interfaz real (necesita DISPLAY)
  ./verificacion/correr.sh   # comprobaciones end-to-end
  ```
- **Capturas de los manuales**: `docs/capturas/generar_capturas.py` regenera las
  imágenes de `docs/img/` con datos de demostración.
