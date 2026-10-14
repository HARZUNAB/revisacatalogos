# verificacion/ — comprobaciones end-to-end de la app

**Esto NO son tests unitarios.** Son scripts de comprobación que ejercitan la
aplicación de punta a punta (ventanas reales, datos de prueba, base simulada)
y sirven de red de seguridad cuando se toca código de la interfaz o del flujo
de revisión.

Los **tests unitarios** (pytest, funciones sueltas, sin pantalla) viven en
`tests/`, en la raíz del proyecto. No mezclar: esta carpeta es para lo que
necesita la app armada o datos de prueba.

## Contenido

| Carpeta | Qué hay | Pantalla |
|---|---|---|
| `offline/` | 7 scripts: lógica de exportación, sin arribos, integración con base simulada, verificador de entorno, decimales | No |
| `gui/` | 13 scripts: ventanas reales (Estaciones, panel, descargas, toolbars, diálogos) | Sí (`DISPLAY`) |

## Cómo correrlos

Todo (offline siempre; gui solo si hay `DISPLAY`):

```bash
./verificacion/correr.sh
```

Uno suelto:

```bash
# offline: directo
.venv/bin/python verificacion/offline/verif_no_picadas.py

# gui: necesita display (en esta máquina, :1)
DISPLAY=:1 .venv/bin/python verificacion/gui/verif_ventana_estaciones.py
```

## Convenciones

- Cada script imprime líneas `OK` / `FALLA` y termina con un resumen
  (`FALLARON n: [...]` o similar). Si no imprime nada de eso, es un script
  de inspección, no un test.
- Los scripts **no tocan el directorio de trabajo real**: trabajan en
  temporales (`tempfile.mkdtemp`) o en el directorio de ejecución con datos
  de prueba que generan ellos mismos.
- Los que necesitan `DISPLAY` se cuelgan en `mainloop` si todo sale bien:
  el runner los mata con `timeout` y eso es esperado.
- Los paths al proyecto son relativos a `__file__`, así que funcionan en
  cualquier máquina (incluido el repo en GitHub).

## Relación con `tests/`

Los tests unitarios ya existen en `tests/` (pytest, funciones puras) y cubren
la lógica de cálculo: comparación, rutas, agencias, perfiles, sismicidad,
exportación y los ayudantes puros de `revisa_seiscomp.py`. Los scripts de esta
carpeta siguen siendo los que ejercitan la app armada y la base simulada; no se
reemplazan entre sí. Para saber qué está cubierto y qué falta, ver
`tests/README.md`.
