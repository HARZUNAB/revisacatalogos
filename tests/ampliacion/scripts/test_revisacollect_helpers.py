#!/usr/bin/env python3
"""
Tests de revisacollect.py
=========================
Cubre los ayudantes puros extraidos de `revisacollect.py`. La corrida completa
(4 pases sobre newcollect.txt, CSV maestro y CSV por analista) se valida con el
golden del arnes (`golden/revisacollect.txt`), que corre el script sin
argumentos con un `trabajo/newcollect.txt` en el temporal.

Los tests importan el modulo con pandas y Levenshtein stubbeados (fixture
`revisacollect`), asi que corren en CI. La unificacion de analistas se prueba
monkeypatcheando `Levenshtein.distance` por una distancia falsa.
"""


def test_separar_dia_mes_agrega_cero(revisacollect):
    assert revisacollect._separar_dia_mes(
        "2026 10 2 1728 18.23L -32.750 -71.739 37.7 GUC 24 0.3 4.5LGUC 1 ana\n"
    ) == "2026 10 02 1728 18.23L -32.750 -71.739 37.7 GUC 24 0.3 4.5LGUC 1 ana"


def test_separar_dia_mes_desdobla_ddmm(revisacollect):
    assert revisacollect._separar_dia_mes(
        "2026 1013 0955 59.10L -23.007 -69.027128.5 GUC 8 0.8 2.8LGUC 1 elena\n"
    ) == "2026 10 13 0955 59.10L -23.007 -69.027128.5 GUC 8 0.8 2.8LGUC 1 elena"


def test_partir_profundidad_corta_no_cambia(revisacollect):
    linea = ("2026 10 02 1728 18.23L -32.750 -71.739 37.7 GUC 24 0.3 "
             "4.5LGUC 1 ana\n")
    assert revisacollect._partir_profundidad(linea) == linea


def test_partir_profundidad_fusionada(revisacollect):
    assert revisacollect._partir_profundidad(
        "2026 10 13 0955 59.10L -23.007 -69.027128.5 GUC 8 0.8 2.8LGUC 1 elena\n"
    ) == "2026 10 13 0955 59.10L -23.007 -69.027 128.5 GUC 8 0.8 2.8LGUC 1 elena\n"


def test_fecha_hora_rellena_dia_y_segundos(revisacollect):
    sismo = ("2026 10 2 1728 18.23L -32.750 -71.739 37.7 GUC 24 0.3 "
             "4.5LGUC 1 ana").split()
    assert revisacollect._fecha_hora_desde_sismo(sismo) == "2026-10-02  17:28:18"


def test_fecha_hora_segundos_menores_a_diez(revisacollect):
    sismo = ("2026 10 14 0452 5.8pL -22.382 -68.592 78.1 GUC 4 0.4 "
             "2.0LGUC 1 caro").split()
    assert revisacollect._fecha_hora_desde_sismo(sismo) == "2026-10-14  04:52:05"


def test_unificar_analistas_une_cercanos(revisacollect, monkeypatch):
    monkeypatch.setattr(revisacollect.Levenshtein, "distance",
                        lambda a, b: 1 if {a, b} == {"jere", "jeree"} else 5)
    mapeo = revisacollect._unificar_analistas(["jeree", "jere", "ana"], 1)
    assert mapeo == {"jeree": "jeree", "jere": "jeree", "ana": "ana"}


def test_unificar_analistas_no_une_lejanos(revisacollect, monkeypatch):
    monkeypatch.setattr(revisacollect.Levenshtein, "distance", lambda a, b: 5)
    assert revisacollect._unificar_analistas(["ana", "beto"], 1) == \
        {"ana": "ana", "beto": "beto"}
