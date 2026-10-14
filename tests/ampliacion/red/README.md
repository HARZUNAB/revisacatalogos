# tests/ampliacion/red/

Tests de la capa de red: `consultaapi.py` (EMSC, USGS, GFZ) y las descargas
SSH/SCP de `traer_catalogos.py`, **con mock**.

Van marcados con `red`. **No** se excluyen del CI, porque se mockean las
llamadas (`requests.get`, `subprocess`) y no se toca la red real. Nunca hacer
una llamada real en un test.

```python
import pytest

pytestmark = pytest.mark.red
```

```bash
./tests/correr.sh red
```

Convención de nombre: `test_<modulo>_<tema>.py`.
