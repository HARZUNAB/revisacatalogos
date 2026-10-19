# tests/ampliacion/gui/

Tests de la **interfaz** (Tk/ttkbootstrap): `app.py`, `plotear.py` y las ventanas
de `revisa_seiscomp.py`. Necesitan pantalla.

Todos los tests de esta carpeta van marcados con `gui`:

```python
import pytest

pytestmark = pytest.mark.gui


def test_algo(salta_sin_display):
    ...
```

El marcador `gui` los excluye de la corrida por defecto y del CI. La fixture
`salta_sin_display` (en `../../conftest.py`) los saltea si no hay `DISPLAY`.

```bash
./tests/correr.sh gui
# o, con display explícito:
DISPLAY=:1 .venv/bin/python -m pytest tests/ampliacion/gui
```

Se apoyan en `verificacion/gui/` (script end-to-end) como referencia de qué
armar y qué verificar.

## Cobertura

Tablero de las superficies de GUI del proyecto. Cada fila pasa a **cubierto**
cuando su archivo existe y pasa; el resto queda **pendiente**.

La columna **Dependencias** dice qué se sustituye: `real` (nada), `sintético`
(datos/estado dummy, sin efectos) o `mock` (dependencia externa mockeada).

**Principio**: se prioriza la **interfaz real** (ventana Tk/ttkbootstrap de
verdad) sobre los mocks. Solo se sustituye cuando la dependencia real no está
disponible (PostgreSQL, red) o es bloqueante/externa (messagebox modal, abrir el
explorador).

**No todos necesitan `DISPLAY`**: la carpeta agrupa lo que depende de las
librerías pesadas de la app (Tk/ttkbootstrap, matplotlib/cartopy) y por eso se
excluye del CI. Archivos que **no** necesitan pantalla (solo las librerías):

- `test_plotear_helpers.py` — helpers puros de `plotear.py` (matplotlib/cartopy
  al importar).
- `test_plotear_figuras.py` — figuras con backend `Agg` (se arman sin pantalla).

El resto sí necesita pantalla (`raiz_tk`/`app_factory`).

| Módulo | Superficie | Archivo de test | Dependencias | Estado |
|---|---|---|---|---|
| `descargas.py` | Diálogo de formato (`preguntar_formato`) | `test_descargas_dialogo.py` | real | cubierto |
| `descargas.py` | `encima_de`, `_etiqueta_secundaria`, `descargar_tabla`/`_texto` | `test_descargas_widgets.py` | real | cubierto |
| `app.py` | Ventana principal + toggles + tooltip | `test_app_principal.py` | sintético | cubierto |
| `app.py` | No publicados / No actualizados / Catálogos / Repetidos | `test_app_ventanas.py` | sintético | cubierto |
| `app.py` | Comparar agencias + Cobertura por agencia | `test_app_agencias.py` | sintético | cubierto |
| `app.py` | Diálogos (contraseña, radio) | `test_app_dialogos.py` | real | cubierto |
| `plotear.py` | Helpers puros (agrupado por perfil, huérfanos) | `test_plotear_helpers.py` | real | cubierto |
| `plotear.py` | Figuras (backend Agg) | `test_plotear_figuras.py` | real | cubierto |
| `plotear.py` | Panel de análisis + aviso "Sin datos" | `test_plotear_panel.py` | sintético | cubierto |
| `plotear.py` | `abrir_eventos`/`abrir_evento`/`abrir_comparacion`/`dibujar_mini_evento` | `test_plotear_abrir.py` | sintético | cubierto |
| `revisa_seiscomp.py` | Panel y catálogo (miniatura del perfil, casilla «Sismicidad histórica» y divisor) | `test_rs_panel.py` | sintético | cubierto |
| `revisa_seiscomp.py` | No actualizados | `test_rs_no_actualizados.py` | sintético | cubierto |
| `revisa_seiscomp.py` | Ventana detalle (botones «Estaciones» y «Planta y perfil») | `test_rs_detalle.py` | sintético | cubierto |
| `revisa_seiscomp.py` | Estaciones + sin arribos ampliada (tooltip por fila, consulta de formas de onda con progreso) | `test_rs_estaciones.py` | sintético | cubierto |
| `revisa_seiscomp.py` | Análisis rápido (tres contadores de evidencia) | `test_rs_analisis.py` | sintético | cubierto |
| `revisa_seiscomp.py` | `main` (ventana propia) | `test_rs_main.py` | sintético | cubierto |
| `solicita_catalogos.py` | Ventana de solicitud + helpers | `test_solicita_catalogos.py` | sintético/mock | cubierto |

Orden de ejecución: **descargas → app → revisa_seiscomp → plotear →
solicita_catalogos** (de lo chico y aislado a lo grande y acoplado).

Nota: construir la ventana principal de `app.py` es costoso (~5 s por test), así
que `gui/` tarda; por eso no corre en el CI.
