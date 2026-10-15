"""
conftest.py de tests/ampliacion/db/
==================================
Tests de la capa de base de datos (marcador `db`, excluidos del CI porque no hay
PostgreSQL en el servidor de integración). Se prefiere un mock de `psycopg2` a
una base real, para que sean reproducibles.

La fixture `psycopg2_falso` instala un módulo `psycopg2` falso en `sys.modules`
y lo restaura al terminar. Expone:
  * `conexiones`: lista de kwargs de cada `connect`.
  * `conexion`: objeto que devuelve `connect`.
  * `error_conectar`: excepción a lanzar en `connect` (o None).
  * `extras.RealDictCursor`: sentinela para `crear_cursor`.
"""

import sys
import types

import pytest


class _ExtrasFalso(types.ModuleType):
    def __init__(self):
        super().__init__("psycopg2.extras")
        self.RealDictCursor = object


class Psycopg2Falso(types.ModuleType):
    def __init__(self):
        super().__init__("psycopg2")
        self.extras = _ExtrasFalso()
        self.conexiones = []
        self.conexion = None
        self.error_conectar = None

    def connect(self, **kwargs):
        self.conexiones.append(kwargs)
        if self.error_conectar is not None:
            raise self.error_conectar
        return self.conexion


@pytest.fixture
def psycopg2_falso():
    previo = sys.modules.get("psycopg2")
    previo_extras = sys.modules.get("psycopg2.extras")
    fake = Psycopg2Falso()
    sys.modules["psycopg2"] = fake
    sys.modules["psycopg2.extras"] = fake.extras
    try:
        yield fake
    finally:
        for nombre, valor in (("psycopg2", previo),
                              ("psycopg2.extras", previo_extras)):
            if valor is None:
                sys.modules.pop(nombre, None)
            else:
                sys.modules[nombre] = valor
