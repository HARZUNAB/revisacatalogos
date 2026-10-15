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

| Módulo | Superficie | Archivo de test | Estado |
|---|---|---|---|
| `descargas.py` | Diálogo de formato (`preguntar_formato`) | `test_descargas_dialogo.py` | cubierto |
| `app.py` | Ventana principal + toggles + tooltip | `test_app_principal.py` | pendiente |
| `app.py` | No publicados / No actualizados / Catálogos / Repetidos | `test_app_ventanas.py` | pendiente |
| `app.py` | Comparar agencias + Cobertura por agencia | `test_app_agencias.py` | pendiente |
| `app.py` | Diálogos (contraseña, radio) | `test_app_dialogos.py` | pendiente |
| `plotear.py` | Helpers puros (agrupado por perfil, huérfanos) | `test_plotear_helpers.py` | pendiente |
| `plotear.py` | Figuras (backend Agg) | `test_plotear_figuras.py` | pendiente |
| `plotear.py` | Panel de análisis + aviso "Sin datos" | `test_plotear_panel.py` | pendiente |
| `revisa_seiscomp.py` | Panel y catálogo | `test_rs_panel.py` | pendiente |
| `revisa_seiscomp.py` | No actualizados | `test_rs_no_actualizados.py` | pendiente |
| `revisa_seiscomp.py` | Ventana detalle | `test_rs_detalle.py` | pendiente |
| `revisa_seiscomp.py` | Estaciones + sin arribos ampliada | `test_rs_estaciones.py` | pendiente |
| `revisa_seiscomp.py` | Análisis rápido | `test_rs_analisis.py` | pendiente |
| `revisa_seiscomp.py` | `main` (ventana propia) | `test_rs_main.py` | pendiente |
| `solicita_catalogos.py` | Ventana de solicitud de catálogos | `test_solicita_catalogos.py` | pendiente |

Orden de ejecución: **descargas → app → revisa_seiscomp → plotear →
solicita_catalogos** (de lo chico y aislado a lo grande y acoplado).
