#!/usr/bin/env python3
"""
conftest.py
===========
Configuración común de los tests unitarios de RCS.

Los módulos del proyecto se importan por nombre plano (``import comparacion``),
no como paquete, porque así los usa la aplicación. Por eso este archivo agrega
la raíz del proyecto al ``sys.path`` antes de que pytest colecte los tests.

Fixtures
--------
``raiz``
    Ruta de la raíz del proyecto.
``cwd_tmp``
    Ejecuta el test en un directorio temporal: las funciones que escriben usan
    ``rutas.p_*()``, que resuelven contra el directorio actual (CWD).
``sin_entregables`` / ``con_entregables``
    Fijan ``rutas.ENTREGABLES`` (se lee al importar el módulo, así que se
    parchea el atributo, no la variable de entorno).
``salta_sin_display``
    Marca como *skip* los tests que necesitan pantalla si no hay ``DISPLAY``.
"""

import os
import sys

import pytest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)


@pytest.fixture
def raiz():
    """Ruta absoluta de la raíz del proyecto."""
    return RAIZ


@pytest.fixture
def cwd_tmp(tmp_path, monkeypatch):
    """Trabaja en un directorio temporal: ``rutas.p_*()`` escriben ahí."""
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture
def sin_entregables(monkeypatch):
    """Desactiva la escritura de entregables automáticos (caso por defecto)."""
    import rutas
    monkeypatch.setattr(rutas, "ENTREGABLES", False)
    return False


@pytest.fixture
def con_entregables(monkeypatch):
    """Activa la escritura de entregables automáticos."""
    import rutas
    monkeypatch.setattr(rutas, "ENTREGABLES", True)
    return True


@pytest.fixture
def salta_sin_display():
    """Salta el test si no hay pantalla (para los marcados ``gui``)."""
    if not os.environ.get("DISPLAY"):
        pytest.skip("necesita pantalla (DISPLAY); usa xvfb o un escritorio")
