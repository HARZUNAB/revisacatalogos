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
