#!/usr/bin/env python3
"""
_plantilla.py — molde para un test de la suite en ampliación
============================================================
NO se colecta (no empieza con ``test_`` ni termina en ``_test``). Cópialo a la
subcarpeta que corresponda y renómbralo ``test_<modulo>_<tema>.py``.

Recordatorios
-------------
* Los módulos del proyecto se importan por nombre plano (``import comparacion``):
  ``tests/conftest.py`` ya agregó la raíz al ``sys.path``.
* Nombres y docstrings en español, como el resto del proyecto.
* Basename único en toda la suite (pytest sin ``__init__.py`` lo exige): por eso
  los archivos de ampliación llevan sufijo de tema.
* Elige la subcarpeta y descomenta el/los marcadores que correspondan.
"""

import pytest

# Descomenta según la carpeta:
#   gui/     -> pytestmark = pytest.mark.gui
#   db/      -> pytestmark = pytest.mark.db
#   red/     -> pytestmark = pytest.mark.red
#   bordes/, scripts/ -> sin marcador

# import el_modulo
#
# from el_modulo import funcion_a_probar


def test_descripcion_del_caso():
    """Una frase que diga qué se prueba y por qué."""
    # Arrange / Act / Assert
    # assert funcion_a_probar(...) == ...
    raise NotImplementedError("reemplaza este test")


# Fixtures disponibles (definidas en tests/conftest.py):
#   raiz                 ruta de la raíz del proyecto
#   cwd_tmp              corre el test en un directorio temporal (rutas.p_*())
#   sin_entregables      rutas.ENTREGABLES = False
#   con_entregables      rutas.ENTREGABLES = True
#   salta_sin_display    salta el test si no hay DISPLAY (para los marcados gui)
