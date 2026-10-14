# tests/ampliacion/scripts/

Tests de los módulos hoy **script-style**, que ejecutan código al importar y leen
`sys.argv` en el nivel superior.

**Antes de testearlos hay que refactorizarlos**: mover la lógica a funciones y
envolver la ejecución en `if __name__ == "__main__"`. Módulos pendientes:

- `compara.py`
- `repetidos.py`
- `repetidosexclu.py`
- `revisaselect.py`
- `revisacollect.py`
- `revisaexcluidos.py`
- `proc_query_harz_2.py`

Una vez refactorizado un módulo, su test va acá con nombre
`test_<modulo>.py`. Son tests puros y entran al CI.

```bash
./tests/correr.sh scripts
```
