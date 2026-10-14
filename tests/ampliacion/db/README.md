# tests/ampliacion/db/

Tests que necesitan una **base de datos** (PostgreSQL/SeisComp) o un mock de
`psycopg2`: capa de consulta de `exporta_ventana_seiscomp.py`, inventario,
bindings, actividad, `verifica_entorno.py`.

Todos los tests van marcados con `db`:

```python
import pytest

pytestmark = pytest.mark.db
```

El marcador `db` los excluye de la corrida por defecto y del CI (no hay base en
el servidor de integración). Se prefieren **mocks** de `psycopg2` a una base real
para que sean reproducibles; si hace falta base real, documentar los datos de
prueba en el encabezado del test.

```bash
./tests/correr.sh db
```

Referencia de armado: `verificacion/offline/` (hay una integración con base
simulada).
