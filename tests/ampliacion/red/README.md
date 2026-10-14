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

## Sin pandas ni requests en CI

`consultaapi.py` importa `pandas` y `requests` a nivel de módulo, pero el CI
solo instala `numpy` y `pytest`. Por eso el `conftest.py` de esta carpeta trae
una fixture `consultaapi` que importa el módulo con **stubs mínimos** de esas
dos dependencias. Los tests nunca ejercitan pandas (las ramas de pandas —
`_guardar` con filas, el parseo de GFZ— quedan fuera del alcance) y reemplazan
`requests.get` con `monkeypatch`. Así el grupo `red` corre en CI sin red real
ni dependencias pesadas.

