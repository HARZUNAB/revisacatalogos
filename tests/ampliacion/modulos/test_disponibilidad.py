#!/usr/bin/env python3
"""
Tests de disponibilidad.py
==========================
Cubre el parser de `scart --print-streams`, la cadena SDS → tiempo real y el
volcado del resultado en una fila de sin arribos. No necesita SeisComp, red ni
SDS: todo se mockea.
"""

from datetime import datetime

import disponibilidad


# --------------------------------------------------------------------------
# Parser
# --------------------------------------------------------------------------
SALIDA_SCART = """\
Test mode: Found errors were stated above, if any
# streamID       start                       end                         records samples samplingRate
C.CCSP.18.HNE    2026-02-11T00:00:00.635Z    2026-02-11T00:01:00.92Z     30 12057 200.0
C.GO01..HNZ      2026-01-01T12:40:18.968Z    2026-01-01T23:23:33.968Z    5946 3859500 100.0
Info: skipping streams 'C.GO10.*.HNZ on 2026-01-01' - no data found
# Summary
"""


def test_parsear_salida_ignora_logs_y_cabecera():
    datos = disponibilidad._parsear_salida(SALIDA_SCART)
    assert list(datos) == ["C.CCSP.18.HNE", "C.GO01..HNZ"]
    assert datos["C.CCSP.18.HNE"]["records"] == 30
    assert datos["C.CCSP.18.HNE"]["desde"].endswith("Z")
    assert datos["C.GO01..HNZ"]["hasta"] == "2026-01-01T23:23:33.968Z"


def test_parsear_salida_vacia():
    assert disponibilidad._parsear_salida("") == {}
    assert disponibilidad._parsear_salida(None) == {}


# --------------------------------------------------------------------------
# Cadena de fuentes
# --------------------------------------------------------------------------
def _preparar(monkeypatch, tmp_path, recordstream="combined://x"):
    monkeypatch.setattr(disponibilidad, "ruta_scart", lambda: "/fake/scart")
    monkeypatch.setattr(disponibilidad, "raiz_sds", lambda: str(tmp_path))
    monkeypatch.setattr(disponibilidad, "recordstream", lambda: recordstream)


def test_consultar_usa_sds(monkeypatch, tmp_path):
    _preparar(monkeypatch, tmp_path)
    monkeypatch.setattr(
        disponibilidad, "_correr",
        lambda *a: ({"A.B..HHZ": {"desde": "d", "hasta": "h", "records": 1}},
                    ["A.B..HHZ"]))
    res = disponibilidad.consultar(["A.B..HHZ"], None, None)
    assert res["A.B..HHZ"]["status"] == disponibilidad.ESTADO_CON_DATOS
    assert res["A.B..HHZ"]["source"] == disponibilidad.FUENTE_SDS


def test_consultar_cae_al_tiempo_real(monkeypatch, tmp_path):
    _preparar(monkeypatch, tmp_path)

    def _correr(_scart, modo, streams, *_resto):
        if modo[0] == "-d":
            return {}, list(streams)          # SDS respondió, sin datos
        return ({"A.B..HHZ": {"desde": "d", "hasta": "h", "records": 2}},
                list(streams))

    monkeypatch.setattr(disponibilidad, "_correr", _correr)
    res = disponibilidad.consultar(["A.B..HHZ"], None, None)
    assert res["A.B..HHZ"]["status"] == disponibilidad.ESTADO_CON_DATOS
    assert res["A.B..HHZ"]["source"] == disponibilidad.FUENTE_RECORDSTREAM


def test_consultar_sin_datos_en_ninguna_fuente(monkeypatch, tmp_path):
    _preparar(monkeypatch, tmp_path)
    monkeypatch.setattr(disponibilidad, "_correr",
                        lambda _s, _m, streams, *_r: ({}, list(streams)))
    res = disponibilidad.consultar(["A.B..HHZ"], None, None)
    assert res["A.B..HHZ"]["status"] == disponibilidad.ESTADO_SIN_DATOS


def test_consultar_sin_scart_no_afirma_nada(monkeypatch, tmp_path):
    _preparar(monkeypatch, tmp_path)
    monkeypatch.setattr(disponibilidad, "ruta_scart", lambda: None)
    res = disponibilidad.consultar(["A.B..HHZ"], None, None)
    assert res["A.B..HHZ"]["status"] == disponibilidad.ESTADO_NO_CONSULTADO


# --------------------------------------------------------------------------
# Progreso
# --------------------------------------------------------------------------
def test_progreso_sds_y_listo(monkeypatch, tmp_path):
    _preparar(monkeypatch, tmp_path)
    monkeypatch.setattr(
        disponibilidad, "_correr",
        lambda *a: ({"A.B..HHZ": {"desde": "d", "hasta": "h", "records": 1}},
                    ["A.B..HHZ"]))
    avisos = []
    disponibilidad.consultar(["A.B..HHZ"], None, None,
                             al_progreso=avisos.append)
    assert avisos == ["Consultando el archivo SDS…", "Listo."]


def test_progreso_con_tiempo_real(monkeypatch, tmp_path):
    _preparar(monkeypatch, tmp_path)

    def _correr(_scart, modo, streams, *_resto):
        if modo[0] == "-d":
            return {}, list(streams)
        return ({"A.B..HHZ": {"desde": "d", "hasta": "h", "records": 1}},
                list(streams))

    monkeypatch.setattr(disponibilidad, "_correr", _correr)
    avisos = []
    disponibilidad.consultar(["A.B..HHZ"], None, None,
                             al_progreso=avisos.append)
    assert avisos == ["Consultando el archivo SDS…",
                      "Buscando en el tiempo real…", "Listo."]


def test_progreso_sin_fuentes(monkeypatch, tmp_path):
    monkeypatch.setattr(disponibilidad, "ruta_scart", lambda: "/fake/scart")
    monkeypatch.setattr(disponibilidad, "raiz_sds",
                        lambda: str(tmp_path / "no_existe"))
    monkeypatch.setattr(disponibilidad, "recordstream", lambda: None)
    avisos = []
    disponibilidad.consultar(["A.B..HHZ"], None, None,
                             al_progreso=avisos.append)
    assert avisos == ["No hay fuentes de formas de onda disponibles."]


def test_progreso_sin_scart(monkeypatch, tmp_path):
    _preparar(monkeypatch, tmp_path)
    monkeypatch.setattr(disponibilidad, "ruta_scart", lambda: None)
    avisos = []
    disponibilidad.consultar(["A.B..HHZ"], None, None,
                             al_progreso=avisos.append)
    assert avisos == ["No hay scart disponible; no se pudo consultar."]


class _Proceso:
    def __init__(self, returncode, stderr=""):
        self.returncode = returncode
        self.stderr = stderr


def test_correr_conserva_lo_encontrado_aunque_falle(monkeypatch):
    monkeypatch.setattr(
        disponibilidad.subprocess, "run",
        lambda *a, **k: _Proceso(
            1, "C.CCSP.18.HNE  d  h  3 100 200.0\n"))
    encontrados, consultados = disponibilidad._correr(
        "/fake/scart", ["-d", "/x"], ["C.CCSP.18.HNE"],
        datetime(2020, 1, 1), datetime(2020, 1, 1, 0, 10), 5)
    assert "C.CCSP.18.HNE" in encontrados
    assert consultados == []


def test_correr_sin_scart_no_rompe(monkeypatch):
    def _falla(*a, **k):
        raise OSError("no existe")

    monkeypatch.setattr(disponibilidad.subprocess, "run", _falla)
    assert disponibilidad._correr(
        "/no/existe", ["-d", "/x"], ["A.B..HHZ"],
        datetime(2020, 1, 1), datetime(2020, 1, 1, 0, 10), 5) == ({}, [])


# --------------------------------------------------------------------------
# Filas
# --------------------------------------------------------------------------
def test_specs_de_fila_usa_la_lista_completa():
    fila = {"red": "C", "estacion": "CCSP", "loc_ref": "18", "cha_ref": "HNE",
            "streams_vigentes_ids": "C.CCSP.18.HNE;C.CCSP.18.HHZ"}
    assert disponibilidad.specs_de_fila(fila) == \
        ["C.CCSP.18.HNE", "C.CCSP.18.HHZ"]


def test_specs_de_fila_cae_a_la_referencia():
    fila = {"red": "C", "estacion": "CCSP", "loc_ref": "", "cha_ref": "HNZ"}
    assert disponibilidad.specs_de_fila(fila) == ["C.CCSP..HNZ"]


def test_aplicar_resultado_prefiere_la_referencia(monkeypatch):
    fila = {"streams_vigentes_ids": "A.B..HHZ;A.B..HHE"}
    resultado = {
        "A.B..HHZ": {"status": disponibilidad.ESTADO_SIN_DATOS,
                     "source": "", "desde": "", "hasta": ""},
        "A.B..HHE": {"status": disponibilidad.ESTADO_CON_DATOS,
                     "source": disponibilidad.FUENTE_SDS,
                     "desde": "d", "hasta": "h"},
    }
    assert disponibilidad.aplicar_resultado(fila, resultado) == \
        disponibilidad.ESTADO_CON_DATOS
    # Como la referencia no tenía datos, se usa el otro stream vigente.
    assert fila["availability_source"] == disponibilidad.FUENTE_SDS
    assert fila["cobertura_desde"] == "d"


def test_texto_formas_onda():
    assert disponibilidad.texto_formas_onda(
        {"waveform_status": "CON_DATOS", "availability_source": "SDS"}) == "SDS"
    assert disponibilidad.texto_formas_onda(
        {"waveform_status": "CON_DATOS",
         "availability_source": "RECORDSTREAM"}) == "Tiempo real"
    assert disponibilidad.texto_formas_onda(
        {"waveform_status": "SIN_DATOS"}) == "Sin datos"
    assert disponibilidad.texto_formas_onda({}) == ""


# --------------------------------------------------------------------------
# Evidencia: certeza (ondas) vs deducción (actividad)
# --------------------------------------------------------------------------
def test_estado_evidencia_verificado_manda():
    fila = {"waveform_status": "CON_DATOS", "actividad_ventana": "0"}
    assert disponibilidad.estado_evidencia(fila) == \
        disponibilidad.EVIDENCIA_VERIFICADO


def test_estado_evidencia_indicio_por_actividad():
    fila = {"waveform_status": "NO_CONSULTADO", "actividad_ventana": "2"}
    assert disponibilidad.estado_evidencia(fila) == \
        disponibilidad.EVIDENCIA_INDICIO


def test_estado_evidencia_sin_evidencia_y_sin_consultar():
    assert disponibilidad.estado_evidencia(
        {"waveform_status": "SIN_DATOS", "actividad_ventana": "0"}) == \
        disponibilidad.EVIDENCIA_SIN_EVIDENCIA
    assert disponibilidad.estado_evidencia({}) == \
        disponibilidad.EVIDENCIA_NO_CONSULTADO


def test_texto_evidencia():
    assert disponibilidad.texto_evidencia(
        {"waveform_status": "CON_DATOS",
         "availability_source": "SDS"}) == "Verificado (SDS)"
    assert disponibilidad.texto_evidencia(
        {"waveform_status": "CON_DATOS",
         "availability_source": "RECORDSTREAM"}) == "Verificado (tiempo real)"
    assert disponibilidad.texto_evidencia(
        {"actividad_ventana": "1"}) == "Indicio (actividad)"
    assert disponibilidad.texto_evidencia(
        {"waveform_status": "SIN_DATOS", "actividad_ventana": "0"}) == \
        "Sin evidencia"
    assert disponibilidad.texto_evidencia({}) == "Sin consultar"


def test_aplicar_resultado_actualiza_evidencia():
    fila = {"streams_vigentes_ids": "A.B..HHZ", "actividad_ventana": "0"}
    disponibilidad.aplicar_resultado(
        fila, {"A.B..HHZ": {"status": "CON_DATOS", "source": "SDS",
                            "desde": "d", "hasta": "h"}})
    assert fila["evidencia"] == disponibilidad.EVIDENCIA_VERIFICADO
